#!/usr/bin/env python3
"""Single-process dispatcher for the hot-path Claude Code hooks.

WHY THIS EXISTS
---------------
settings.json used to register N separate Python hooks per event. Claude Code
runs them serially, each as its OWN `python.exe` process. On Windows a cold
interpreter spawn costs ~1.2-1.6s (cold file cache / AV first-touch), so the
UserPromptSubmit chain (4 hooks) added several seconds of latency BEFORE every
prompt, and PostToolUse (2 hooks) added ~2-3s after every edit. The hooks'
actual work is tiny (~0-30 ms each); the cost is purely interpreter startup,
paid once per hook.

This dispatcher collapses that to ONE interpreter start per event: it imports
each underlying hook module once (the imports are the real work) and calls its
`main()` in-process, feeding each a fresh copy of the stdin payload and
capturing its stdout/stderr/exit code. The individual hook files are NOT
modified -- they still run standalone and their *_smoketest.py still pass.

OUTPUT CONTRACTS PRESERVED
--------------------------
- UserPromptSubmit: each hook emits a JSON object
  {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                          "additionalContext": "..."}}
  (or nothing). Claude Code, running them separately, would concatenate every
  hook's additionalContext. We reproduce that: extract each hook's
  additionalContext (or plain text), join with blank lines, and emit ONE merged
  JSON object. Exit 0 always.
- PostToolUse: a hook exits 2 (with a stderr message) to surface a blocker back
  to Claude; otherwise exit 0. We run all hooks, and if ANY asked to block we
  re-emit its stderr and exit 2; else exit 0.

LOAD-BEARING INVARIANT (matches every hook here): never block the user on an
internal failure. A hook that raises, fails to import, or misbehaves is treated
as a silent no-op -- the dispatcher still exits 0 for UserPromptSubmit, and for
PostToolUse only a clean exit-2 from a hook propagates.

KILL SWITCH
-----------
Revert settings.json to the per-hook command arrays (git history has the prior
form). This file becoming a no-op or being deleted only matters once settings
points at it. Set CC_HOOK_DISPATCH_DISABLE=1 to make the dispatcher pass through
as a no-op (exit 0, no output) without touching settings.json.

USAGE
-----
    python hook_dispatch.py UserPromptSubmit   < payload.json
    python hook_dispatch.py PostToolUse        < payload.json
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Absolute hook paths, mirroring what settings.json registered before
# consolidation. Two homes, unchanged from the original setup:
#   - ~/.claude/scripts/         (copied from this repo's scripts/)
#   - <repo>/hermes-agent/claude_code_integration/  (run from the repo directly)
# Resolve the scripts dir from this file's own location so a moved/copied
# dispatcher still finds its neighbours; the claude_code_integration dir is the
# repo path settings.json already hardcodes.
_SCRIPTS_DIR = Path(__file__).resolve().parent
_CCI_DIR = Path(
    os.environ.get(
        "CC_HOOK_CCI_DIR",
        r"D:\Projects\super_code\hermes-agent\claude_code_integration",
    )
)

# event name -> ordered list of (label, hook_file_path). Order matches the
# original settings.json arrays so injected-context ordering is unchanged.
REGISTRY: dict[str, list[tuple[str, Path]]] = {
    "UserPromptSubmit": [
        ("curator_prompt_hook", _CCI_DIR / "curator_prompt_hook.py"),
        ("smart_router_prompt_hook", _CCI_DIR / "smart_router_prompt_hook.py"),
        ("context_budget_gate", _SCRIPTS_DIR / "context_budget_gate.py"),
        ("qrev_auto_inject", _SCRIPTS_DIR / "qrev_auto_inject.py"),
        ("coord_prompt_hook", _SCRIPTS_DIR / "coord_prompt_hook.py"),
        ("memgraph_prompt_hook", _SCRIPTS_DIR / "memgraph_prompt_hook.py"),
    ],
    "PostToolUse": [
        ("semgrep_postedit_hook", _SCRIPTS_DIR / "semgrep_postedit_hook.py"),
        ("qrev_edit_counter", _SCRIPTS_DIR / "qrev_edit_counter.py"),
    ],
}


class HookResult:
    __slots__ = ("label", "code", "stdout", "stderr")

    def __init__(self, label: str, code: int, stdout: str, stderr: str) -> None:
        self.label = label
        self.code = code
        self.stdout = stdout
        self.stderr = stderr


def _load_main(label: str, path: Path):
    """Import a hook module from its file path and return its main() callable.

    Returns None on any failure (missing file, import error, no main()) so the
    caller can treat it as a no-op. The import runs the module's top-level code
    once -- that's where the real (cached) work lives.
    """
    try:
        if not path.is_file():
            return None
        spec = importlib.util.spec_from_file_location(f"_hookmod_{label}", str(path))
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        # Register before exec so a hook that introspects sys.modules behaves.
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        fn = getattr(mod, "main", None)
        return fn if callable(fn) else None
    except Exception:
        return None


def _run_hook(label: str, path: Path, payload_raw: str) -> HookResult:
    """Call one hook's main() with stdin/stdout/stderr swapped; capture all."""
    main_fn = _load_main(label, path)
    if main_fn is None:
        return HookResult(label, 0, "", "")

    real_stdin, real_stdout, real_stderr = sys.stdin, sys.stdout, sys.stderr
    out_buf, err_buf = io.StringIO(), io.StringIO()
    code = 0
    try:
        sys.stdin = io.StringIO(payload_raw)  # fresh, unread copy per hook
        sys.stdout = out_buf
        sys.stderr = err_buf
        try:
            ret = main_fn()
            code = int(ret) if isinstance(ret, int) else 0
        except SystemExit as e:  # a hook may sys.exit() from inside main()
            code = int(e.code) if isinstance(e.code, int) else 0
        except Exception:
            code = 0  # never block on an internal hook failure
    finally:
        sys.stdin, sys.stdout, sys.stderr = real_stdin, real_stdout, real_stderr
    return HookResult(label, code, out_buf.getvalue(), err_buf.getvalue())


def _extract_context(stdout: str) -> str:
    """Pull the additionalContext out of one UserPromptSubmit hook's stdout.

    Accepts the JSON hookSpecificOutput form (what every hook here emits) and
    falls back to treating non-JSON stdout as plain context text.
    """
    s = stdout.strip()
    if not s:
        return ""
    try:
        obj = json.loads(s)
    except Exception:
        return s  # plain-text context
    if isinstance(obj, dict):
        hso = obj.get("hookSpecificOutput")
        if isinstance(hso, dict):
            ctx = hso.get("additionalContext")
            if isinstance(ctx, str) and ctx.strip():
                return ctx
        # Some other JSON shape: don't guess -- emit nothing rather than garble.
        return ""
    return ""


def _log_injection_size(merged: str, piece_count: int) -> None:
    """Append the merged additionalContext size to a per-turn JSONL log.

    ISC #3 (AI_OS_STRATEGY.md sect. 12, "token floor held"): the per-turn
    injected-context budget is verified by diffing THIS log before/after any
    OS change -- the statusline can't isolate the injection delta. One row per
    UserPromptSubmit dispatch, zero rows lost to errors (silent no-op).
    Kill switch: CC_INJECTION_LOG_DISABLE=1, or delete the log file.
    """
    if os.environ.get("CC_INJECTION_LOG_DISABLE") == "1":
        return
    try:
        base = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
        row = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": "UserPromptSubmit",
            "bytes": len(merged.encode("utf-8")),
            "approx_tokens": len(merged) // 4,
            "pieces": piece_count,
        }
        with (base / ".hook_injection_log.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception:
        pass  # never block the user on logging


def _dispatch_user_prompt_submit(hooks, payload_raw: str) -> int:
    pieces: list[str] = []
    for label, path in hooks:
        res = _run_hook(label, path, payload_raw)
        ctx = _extract_context(res.stdout)
        if ctx:
            pieces.append(ctx)
    _log_injection_size("\n\n".join(pieces), len(pieces))
    if pieces:
        merged = "\n\n".join(pieces)
        decision = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": merged,
            }
        }
        sys.stdout.write(json.dumps(decision))
    return 0


def _dispatch_post_tool_use(hooks, payload_raw: str) -> int:
    block_msgs: list[str] = []
    for label, path in hooks:
        res = _run_hook(label, path, payload_raw)
        if res.code == 2:
            msg = res.stderr.strip()
            block_msgs.append(msg if msg else f"{label}: blocked")
    if block_msgs:
        sys.stderr.write("\n".join(block_msgs) + "\n")
        return 2
    return 0


def main(argv: list[str]) -> int:
    if os.environ.get("CC_HOOK_DISPATCH_DISABLE") == "1":
        return 0
    event = argv[1] if len(argv) > 1 else ""
    hooks = REGISTRY.get(event)
    if not hooks:
        return 0  # unknown event -> no-op

    try:
        payload_raw = sys.stdin.read()
    except Exception:
        payload_raw = ""

    if event == "UserPromptSubmit":
        return _dispatch_user_prompt_submit(hooks, payload_raw)
    if event == "PostToolUse":
        return _dispatch_post_tool_use(hooks, payload_raw)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:
        # A dispatcher crash must never block the user.
        sys.exit(0)
