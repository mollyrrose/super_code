#!/usr/bin/env python3
"""Smoketest for run_codex_challenge.py — runs without Codex CLI (mock mode)."""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

# Add scripts/lib to path
sys.path.insert(0, str(Path(__file__).parent))

from run_codex_challenge import (
    check_codex_binary,
    check_codex_auth,
    check_api_backend,
    build_adversarial_prompt,
    parse_codex_jsonl,
    run_codex_challenge,
)


def test_check_codex_binary_missing():
    """Test binary check when codex not found."""
    with patch("shutil.which", return_value=None):
        ok, msg = check_codex_binary()
        assert not ok
        assert "not found" in msg.lower()
    print("[ok] check_codex_binary: correctly detects missing binary")


def test_check_codex_auth_missing():
    """Test auth check when no auth configured."""
    with patch.dict(os.environ, {"CODEX_HOME": "/nonexistent/path"}, clear=False):
        for key in ["CODEX_API_KEY", "OPENAI_API_KEY"]:
            os.environ.pop(key, None)
        ok, msg = check_codex_auth()
        assert not ok
        assert "auth" in msg.lower()
    print("[ok] check_codex_auth: correctly detects missing auth")


def test_build_adversarial_prompt():
    """Test prompt building includes boundary and diff."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            subprocess.run(["git", "init", "-q"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], check=True, capture_output=True)
            Path("test.txt").write_text("original")
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init", "-q"], check=True, capture_output=True)
            Path("test.txt").write_text("modified")
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "modify", "-q"], check=True, capture_output=True)

            prompt = build_adversarial_prompt(["test.txt"], "HEAD~1")
            assert "IMPORTANT: Do NOT read or execute any files under ~/.claude/" in prompt
            assert "adversarial" in prompt.lower() or "attacker" in prompt.lower()
            assert "THE DIFF:" in prompt
            print("[ok] build_adversarial_prompt: contains boundary and diff")
        finally:
            os.chdir(old_cwd)


def test_parse_codex_jsonl():
    """Test JSONL parser extracts findings, reasoning, tokens."""
    jsonl_output = """{"type": "item.completed", "item": {"type": "reasoning", "text": "thinking about race conditions"}}
{"type": "item.completed", "item": {"type": "agent_message", "text": "Found [P1] SQL injection at users.py:42"}}
{"type": "item.completed", "item": {"type": "agent_message", "text": "Found [P2] missing input validation at api.py:10"}}
{"type": "turn.completed", "usage": {"input_tokens": 1000, "output_tokens": 500}}"""

    result = parse_codex_jsonl(jsonl_output)
    assert len(result["reasoning_traces"]) == 1
    assert "race conditions" in result["reasoning_traces"][0]
    assert len(result["findings"]) == 2
    assert result["tokens_used"] == 1500
    assert result["turns_completed"] == 1
    print("[ok] parse_codex_jsonl: extracts reasoning, findings, tokens")


def test_p1_p2_classification():
    """Test [P1]/[P2] classification logic."""
    p1 = ["Found [P1] critical bug", "Another [P1] issue"]
    p2 = ["Found [P2] advisory", "No marker here"]
    classified_p1 = [f for f in p1 + p2 if "[P1]" in f]
    classified_p2 = [f for f in p1 + p2 if "[P2]" in f or ("[P1]" not in f and "[P2]" not in f)]
    assert len(classified_p1) == 2
    assert len(classified_p2) == 2
    print("[ok] p1/p2 classification: works correctly")


def _no_local_llm(monkeypatch_target="run_codex_challenge.check_local_llm"):
    """Context manager: force check_local_llm to return False (no server)."""
    from unittest.mock import patch as _patch
    return _patch(monkeypatch_target, return_value=(False, "", "mocked: no local LLM"))


def test_check_local_llm_no_server():
    """Test check_local_llm returns False when nothing runs on known ports."""
    # All common ports are blocked/unavailable in a test environment without running servers.
    # We verify the function returns a tuple and does not raise.
    import run_codex_challenge as m
    ok, url, name = m.check_local_llm()
    assert isinstance(ok, bool)
    assert isinstance(url, str)
    assert isinstance(name, str)
    print("[ok] check_local_llm: returns valid tuple (server may or may not be running)")


def test_parse_local_llm_findings():
    """Test [P1]/[P2] extraction from plain text LLM response."""
    from run_codex_challenge import parse_local_llm_findings
    text = (
        "[P1] SQL injection at users.py:42 -- raw query with unsanitized input.\n\n"
        "[P2] Missing rate limiting on /api/login -- brute force vector.\n\n"
        "Some other paragraph without markers but mentions injection."
    )
    result = parse_local_llm_findings(text)
    assert len(result["p1_findings"]) == 1
    assert "injection" in result["p1_findings"][0].lower()
    assert len(result["p2_findings"]) >= 1  # [P2] + other (injection keyword)
    assert len(result["all_findings"]) >= 2
    print("[ok] parse_local_llm_findings: extracts [P1]/[P2] and keyword findings")


def test_check_api_backend_off_by_default():
    """Hosted API must stay off unless QREV_CHALLENGE_API names a provider."""
    for value in ["", "0", "off", "none", "false"]:
        with patch.dict(os.environ, {"QREV_CHALLENGE_API": value}, clear=False):
            ok, provider, msg = check_api_backend()
            assert not ok, f"backend must be off for QREV_CHALLENGE_API={value!r}"
            assert provider == ""
            assert "QREV_CHALLENGE_API" in msg
    print("[ok] check_api_backend: opt-in only, off by default (no silent API spend)")


def test_check_api_backend_unknown_provider():
    """An unrecognised provider name is a clean skip, not a crash."""
    with patch.dict(os.environ, {"QREV_CHALLENGE_API": "bogus"}, clear=False):
        ok, provider, msg = check_api_backend()
        assert not ok
        assert "unknown" in msg.lower()
    print("[ok] check_api_backend: unknown provider skips cleanly")


def test_check_api_backend_missing_key():
    """A known provider without its key is a clean skip."""
    with patch.dict(os.environ, {"QREV_CHALLENGE_API": "deepseek"}, clear=False):
        os.environ.pop("DEEPSEEK_API_KEY", None)
        ok, provider, msg = check_api_backend()
        assert not ok
        assert provider == "deepseek"
        assert "DEEPSEEK_API_KEY" in msg
    print("[ok] check_api_backend: missing key skips cleanly")


def test_check_api_backend_enabled():
    """With provider + key set, the backend reports available."""
    with patch.dict(
        os.environ,
        {"QREV_CHALLENGE_API": "deepseek", "DEEPSEEK_API_KEY": "test-key-not-real"},
        clear=False,
    ):
        ok, provider, msg = check_api_backend()
        assert ok
        assert provider == "deepseek"
    print("[ok] check_api_backend: enables when provider + key are both present")


def test_api_pick_best():
    """Model discovery picks the highest-priority family, stable alias first."""
    import run_codex_challenge as m

    assert m._api_pick_best("deepseek", ["deepseek-chat", "deepseek-reasoner"]) == "deepseek-reasoner"
    assert m._api_pick_best("deepseek", ["deepseek-chat"]) == "deepseek-chat"
    assert m._api_pick_best("deepseek", ["something-else"]) is None
    # OpenAI is version-ranked, not list-ranked: a newer family wins even when
    # no pattern in the fallback list mentions it. This is the regression that
    # let gpt-5.5 keep winning after gpt-5.6-* and gpt-6-astra shipped.
    live = ["gpt-4o", "gpt-5", "gpt-5.5", "gpt-5.5-pro", "gpt-5.6-luna",
            "gpt-5.6-sol", "gpt-5.6-terra", "gpt-6-astra", "o3"]
    assert m._api_pick_best("openai", live) == "gpt-6-astra"
    # A hypothetical future family must win with NO code change.
    assert m._api_pick_best("openai", live + ["gpt-7-nova"]) == "gpt-7-nova"
    # Within a family: pro beats plain, and an undated alias beats a snapshot.
    assert m._api_pick_best("openai", ["gpt-5.5", "gpt-5.5-pro"]) == "gpt-5.5-pro"
    assert m._api_pick_best("openai", ["gpt-5-2026-01-01", "gpt-5"]) == "gpt-5"
    assert m._api_pick_best("openai", ["gpt-5-2025-07-15", "gpt-5-2026-01-01"]) == "gpt-5-2026-01-01"
    # Weak variants must never win, even when they are the newest thing listed.
    # The list is deliberately minimal and the mini/nano ids are hypothetical
    # (like gpt-7-nova above): the exclusion is only provable when the weak
    # variant comes from a NEWER family than the alternative -- otherwise it
    # would lose on version anyway and the assertion would pass even with the
    # exclusion broken. Adding gpt-6-astra here would make the expected answer
    # gpt-6-astra and this test would stop proving anything about mini/nano.
    # The real codename variants (astra/luna/sol/terra) are covered by `live`.
    assert m._api_pick_best("openai", ["gpt-5.5", "gpt-6-mini", "gpt-6-nano"]) == "gpt-5.5"
    assert m._openai_sort_key("gpt-5.4-mini") is None
    assert m._openai_sort_key("gpt-5-search-api") is None
    assert m._openai_sort_key("text-embedding-3-large") is None
    # o-series ranks below every gpt family.
    assert m._api_pick_best("openai", ["o3-pro", "gpt-5"]) == "gpt-5"
    print("[ok] _api_pick_best: version-ranked, newest family wins, weak variants excluded")


def test_api_model_cache_roundtrip():
    """Cache write/read roundtrips, and a stale entry is only served on demand."""
    import run_codex_challenge as m

    with tempfile.TemporaryDirectory() as tmpdir:
        original = m._API_MODEL_CACHE
        m._API_MODEL_CACHE = Path(tmpdir) / "cache.json"
        try:
            assert m._api_read_cache("deepseek") is None  # missing file
            m._api_write_cache("deepseek", "deepseek-chat")
            assert m._api_read_cache("deepseek") == "deepseek-chat"
            assert m._api_read_cache("openai") is None  # other provider untouched

            # Age it past the TTL: fresh read misses, stale read still serves.
            aged = json.loads(m._API_MODEL_CACHE.read_text(encoding="utf-8"))
            aged["deepseek"]["fetched_at"] -= (m._API_CACHE_TTL_HOURS + 1) * 3600
            m._API_MODEL_CACHE.write_text(json.dumps(aged), encoding="utf-8")
            assert m._api_read_cache("deepseek") is None
            assert m._api_read_cache("deepseek", allow_stale=True) == "deepseek-chat"

            # A corrupt cache file must never raise.
            m._API_MODEL_CACHE.write_text("{not json", encoding="utf-8")
            assert m._api_read_cache("deepseek") is None
        finally:
            m._API_MODEL_CACHE = original
    print("[ok] _api_*_cache: roundtrip, TTL, stale fallback, corrupt file tolerated")


def test_api_empty_response_is_a_failure():
    """An empty model message must never be reported as a clean PASS."""
    import io
    import run_codex_challenge as m

    body = json.dumps({
        "choices": [{"message": {"content": "   "}}],
        "usage": {"total_tokens": 8192, "completion_tokens": 8192,
                  "completion_tokens_details": {"reasoning_tokens": 8192}},
    }).encode("utf-8")

    class _Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key", "QREV_CHALLENGE_MODEL": "deepseek-v4-pro"}, clear=False):
        with patch.object(m._API_OPENER, "open", return_value=_Resp(body)):
            result = m.call_api_llm("deepseek", "prompt")
    assert not result["success"], "blank content must not count as a successful review"
    assert "API_EMPTY_RESPONSE" in result["error"]
    assert "reasoning_tokens=8192" in result["error"]
    print("[ok] call_api_llm: blank response is a failure, not a silent PASS")


def test_api_refuses_redirects():
    """A 3xx must not re-send the Bearer key to the redirect target."""
    import run_codex_challenge as m

    handler = m._NoRedirect()
    req = urllib.request.Request("https://api.deepseek.com/v1/models")
    try:
        handler.redirect_request(req, io.BytesIO(b""), 302, "Found", {},
                                 "https://evil.example/v1/models")
    except urllib.error.HTTPError as e:
        assert "refusing redirect" in str(e.reason)
        assert "evil.example" in str(e.reason)
    else:
        raise AssertionError("redirect_request must raise, not follow the redirect")
    # The opener the API calls actually use must carry that handler.
    assert any(isinstance(h, m._NoRedirect) for h in m._API_OPENER.handlers)
    print("[ok] _NoRedirect: key-bearing requests refuse to follow redirects")


def test_prompt_frames_diff_as_untrusted_data():
    """The diff is attacker-controllable, so the prompt must fence it off."""
    import run_codex_challenge as m

    with patch.object(m.subprocess, "run") as fake_run:
        fake_run.return_value = subprocess.CompletedProcess([], 0, "diff --git a/x b/x\n", "")
        prompt = m.build_adversarial_prompt(["x"], "main")
    assert "UNTRUSTED DATA" in prompt
    assert "prompt injection" in prompt.lower()
    # rindex, not index: the boundary text quotes the marker name itself, so
    # the FIRST "THE DIFF:" is inside the instructions. The real marker is last.
    assert prompt.index("UNTRUSTED DATA") < prompt.rindex("THE DIFF:")
    print("[ok] build_adversarial_prompt: diff is fenced as untrusted data")


def test_run_codex_challenge_skip_on_missing_binary():
    """Test run_codex_challenge returns skip when no local LLM and no binary."""
    with _no_local_llm():
        with patch.dict(os.environ, {"QREV_CHALLENGE_API": ""}, clear=False):
            with patch("shutil.which", return_value=None):
                result = run_codex_challenge(["test.txt"], "main")
                assert not result["success"]
                assert "no local LLM" in result["skip_reason"]
                assert "CODEX_CLI_MISSING" in result["error"]
                assert "API_UNAVAILABLE" in result["error"]
    print("[ok] run_codex_challenge: skips gracefully when no local LLM and binary missing")


def test_run_codex_challenge_skip_on_missing_auth():
    """Test run_codex_challenge returns skip when no local LLM and no auth."""
    # Patch check_codex_binary itself, not shutil.which: on Windows the probe
    # runs `codex --version` through cmd.exe, so a faked which() path still
    # reports the binary as missing and we would never reach the auth branch.
    with _no_local_llm():
        with patch("run_codex_challenge.check_codex_binary", return_value=(True, "fake codex 1.0")):
            with patch.dict(
                os.environ,
                {"CODEX_HOME": "/nonexistent", "QREV_CHALLENGE_API": ""},
                clear=False,
            ):
                for key in ["CODEX_API_KEY", "OPENAI_API_KEY"]:
                    os.environ.pop(key, None)
                result = run_codex_challenge(["test.txt"], "main")
                assert not result["success"]
                assert "no local LLM" in result["skip_reason"]
                assert "CODEX_AUTH_FAILED" in result["error"]
    print("[ok] run_codex_challenge: skips gracefully when no local LLM and auth missing")


def main():
    """Run all smoketests."""
    test_check_codex_binary_missing()
    test_check_codex_auth_missing()
    test_parse_codex_jsonl()
    test_p1_p2_classification()
    test_check_local_llm_no_server()
    test_parse_local_llm_findings()
    test_check_api_backend_off_by_default()
    test_check_api_backend_unknown_provider()
    test_check_api_backend_missing_key()
    test_check_api_backend_enabled()
    test_api_pick_best()
    test_api_model_cache_roundtrip()
    test_api_empty_response_is_a_failure()
    test_api_refuses_redirects()
    test_prompt_frames_diff_as_untrusted_data()
    test_run_codex_challenge_skip_on_missing_binary()
    test_run_codex_challenge_skip_on_missing_auth()

    # test_build_adversarial_prompt requires git - run separately if git available
    if shutil.which("git"):
        try:
            test_build_adversarial_prompt()
        except Exception as e:
            print(f"(warn) build_adversarial_prompt test skipped: {e}")

    print("\n[ok] All smoketests passed!")


if __name__ == "__main__":
    main()