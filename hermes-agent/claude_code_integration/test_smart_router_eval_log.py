"""Tests for the smart-router eval-log writer in smart_router_prompt_hook.

Run with: python -m unittest test_smart_router_eval_log
from the claude_code_integration directory.

Privacy contract (load-bearing):
- The prompt body never appears in the output JSONL row.
- A logger exception never changes the hook's exit code or stdout output.

Since 2026-09-23 the writer is OPT-IN (SMART_ROUTER_EVAL_LOG=1) and OFF by
default, so the helper below arms it explicitly; one test covers the default.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class _IsolatedLogPath:
    """Patches CLAUDE_CONFIG_DIR + reloads the hook so EVAL_LOG_PATH resolves to a tmpdir.

    Also sets SMART_ROUTER_EVAL_LOG, which gates the writer (default OFF in
    production). Pass enable_log=False to exercise that default.
    """

    def __init__(self, tmpdir: Path, enable_log: bool = True):
        self.tmpdir = tmpdir
        self.enable_log = enable_log
        self._old_env = None
        self._old_eval = None

    def __enter__(self):
        self._old_env = os.environ.get("CLAUDE_CONFIG_DIR")
        self._old_eval = os.environ.get("SMART_ROUTER_EVAL_LOG")
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.tmpdir)
        os.environ["SMART_ROUTER_EVAL_LOG"] = "1" if self.enable_log else "0"
        # Re-import the hook so module-level EVAL_LOG_PATH picks up the env var.
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        for mod_name in ("smart_router_prompt_hook",):
            sys.modules.pop(mod_name, None)
        import smart_router_prompt_hook  # noqa: F401

        return smart_router_prompt_hook

    def __exit__(self, *_):
        if self._old_env is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = self._old_env
        if self._old_eval is None:
            os.environ.pop("SMART_ROUTER_EVAL_LOG", None)
        else:
            os.environ["SMART_ROUTER_EVAL_LOG"] = self._old_eval


class TestEvalLogPrivacy(unittest.TestCase):
    def _run_hook_with_payload(
        self, payload: dict, tmpdir: Path, enable_log: bool = True
    ) -> tuple[int, str]:
        """Invoke smart_router_prompt_hook.main() with a JSON stdin payload."""
        raw = json.dumps(payload)
        with _IsolatedLogPath(tmpdir, enable_log=enable_log) as hook:
            with mock.patch.object(sys, "stdin", io.StringIO(raw)):
                stdout_buf = io.StringIO()
                with mock.patch.object(sys, "stdout", stdout_buf):
                    rc = hook.main()
                return rc, stdout_buf.getvalue()

    def test_prompt_body_never_appears_in_log(self):
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            distinctive = "DOLPHIN-MAGIC-FLAMINGO-12345"
            payload = {
                "prompt": f"the {distinctive} crashed at startup",
                "session_id": "test-sid",
                "cwd": "D:\\projects\\super_claude",
            }
            self._run_hook_with_payload(payload, tmpdir)

            log_file = tmpdir / ".smart_router_eval.jsonl"
            self.assertTrue(log_file.exists(), "logger must write the row")
            text = log_file.read_text(encoding="utf-8")
            self.assertNotIn(
                distinctive, text, "prompt body must NEVER appear in the log"
            )

    def test_hash_format_is_16_hex(self):
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            payload = {
                "prompt": "Traceback ValueError in foo.py",
                "session_id": "test-sid",
                "cwd": "D:\\projects\\super_claude",
            }
            self._run_hook_with_payload(payload, tmpdir)

            row = json.loads((tmpdir / ".smart_router_eval.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(len(row["prompt_hash"]), 16)
            expected = hashlib.sha256(payload["prompt"].encode()).hexdigest()[:16]
            self.assertEqual(row["prompt_hash"], expected)

    def test_logger_exception_does_not_break_hook(self):
        """A forced logger crash must not change exit code or stdout."""
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            payload = {
                "prompt": "Traceback ValueError in foo.py",
                "session_id": "test-sid",
                "cwd": "D:\\projects\\super_claude",
            }
            # First confirm baseline output without crashing logger.
            rc_ok, stdout_ok = self._run_hook_with_payload(payload, tmpdir)
            # Now force the logger to raise.
            with _IsolatedLogPath(tmpdir) as hook:
                with mock.patch.object(
                    hook, "_log_eval_row", side_effect=RuntimeError("boom")
                ):
                    raw = json.dumps(payload)
                    with mock.patch.object(sys, "stdin", io.StringIO(raw)):
                        stdout_buf = io.StringIO()
                        with mock.patch.object(sys, "stdout", stdout_buf):
                            rc_crash = hook.main()
                            stdout_crash = stdout_buf.getvalue()

            self.assertEqual(rc_crash, rc_ok)
            self.assertEqual(stdout_crash, stdout_ok)

    def test_no_row_written_when_switch_is_off(self):
        """Default (SMART_ROUTER_EVAL_LOG unset/0) writes nothing at all."""
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            payload = {
                "prompt": "Traceback (most recent call last): ValueError in foo.py",
                "session_id": "test-sid",
                "cwd": "D:\\projects\\super_code",
            }
            rc, stdout = self._run_hook_with_payload(payload, tmpdir, enable_log=False)
            self.assertEqual(rc, 0)
            self.assertFalse(
                (tmpdir / ".smart_router_eval.jsonl").exists(),
                "eval log must not be written while the opt-in switch is off",
            )
            # The tier hint itself is unaffected by the logging switch.
            self.assertIn("hookSpecificOutput", stdout)

    def test_dead_skill_field_is_gone_from_the_row(self):
        """The skill-suggestion branch was deleted; its column must not come back."""
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            payload = {
                "prompt": "Traceback (most recent call last): ValueError in foo.py",
                "session_id": "test-sid",
                "cwd": "D:\\projects\\super_code",
            }
            self._run_hook_with_payload(payload, tmpdir)
            row = json.loads((tmpdir / ".smart_router_eval.jsonl").read_text(encoding="utf-8"))
            self.assertNotIn("suggested_skill_or_null", row)
            self.assertIn("suggested_model_or_null", row)

    def test_project_slug_matches_claude_code_pattern(self):
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            payload = {
                "prompt": "Traceback ValueError in foo.py",
                "session_id": "test-sid",
                "cwd": "D:\\projects\\super_claude",
            }
            self._run_hook_with_payload(payload, tmpdir)
            row = json.loads((tmpdir / ".smart_router_eval.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(row["project"], "D--projects-super-claude")


if __name__ == "__main__":
    unittest.main()
