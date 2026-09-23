#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook — smart-router model-tier hint.

Reads the JSON payload Claude Code passes on stdin, recommends a subagent
model tier (plus mode/effort) via smart_router_rules, and emits a
hookSpecificOutput.additionalContext JSON carrying that hint alongside the
standing token/fleet discipline.

SCOPE NOTE (2026-09-23) — the skill-suggestion branch was REMOVED, along with
its SMART_ROUTER_SUGGEST_INJECT switch and the always-on eval logging that fed
it. Measured: of the joinable eval rows where the router predicted a skill, the
user invoked the predicted skill 0 times, and the prompt text carries no
learnable tier signal (naive Bayes 48.1% vs a 56.8% always-"sonnet" baseline,
n=81) because 85% of turns delegate to no subagent at all. The injection had
already been off since 2026-08-29; this removed the dead code behind it. Full
evidence: docs/decisions/log.md.

Designed to run side-by-side with curator_prompt_hook.py — Claude Code
concatenates the additionalContext from every registered UserPromptSubmit
hook.

Failures are silent: any exception → exit 0 with no output. A broken router
must never block the user's prompt.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from smart_router_rules import (  # noqa: E402
    format_model_tier,
    format_mode_effort,
    recommend_model_tier,
    recommend_mode_effort,
)

MAX_INJECTED_CHARS = 1400

# Injected every turn - no exceptions. Keep short so it never crowds the skill hint.
STANDING_DISCIPLINE = (
    "[MANDATORY STANDING DISCIPLINE - every turn, no exceptions]\n"
    "TOKENJUICE: pipe ALL Bash/PowerShell cmds -> "
    "python ~/.claude/scripts/tokenjuice.py -- <cmd>; "
    "big blobs -> tokenjuice_condense.py --file <path>. "
    "No exceptions except interactive cmds and exact-byte-required cmds.\n"
    "QREV FLEET: /qRev = exactly 15 parallel agents per pass x 3 passes. "
    "Dispatching fewer is a VIOLATION. No sparing, no shortcuts, no exceptions."
)

EVAL_LOG_PATH = (
    Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
    / ".smart_router_eval.jsonl"
)

def _eval_log_enabled() -> bool:
    """Eval-log writing is OPT-IN and OFF by default (2026-09-23).

    3.5 months of always-on logging produced 6577 rows (~2 MB) and only 81
    usable labels, on which a learned router scored WORSE than always
    guessing "sonnet" -- the stream was not earning its cost. The writer and
    its privacy contract are kept intact behind this switch so it can be
    re-armed cheaply if a real labelling need appears.
    """
    return os.environ.get("SMART_ROUTER_EVAL_LOG", "0").strip() in ("1", "true", "True")


_MODE_EFFORT_GATE: bool | None = None


def _mode_effort_enabled() -> bool:
    """True only if the fixture passes AND the kill switch is not set.
    Fail-closed: any error importing/running the fixture -> False (no new hint,
    old hints untouched). Cached per process."""
    global _MODE_EFFORT_GATE
    if os.environ.get("SR_MODE_EFFORT_DISABLE") == "1":
        return False
    if _MODE_EFFORT_GATE is None:
        try:
            from smart_router_mode_effort_fixture_runner import run_fixture
            _MODE_EFFORT_GATE = bool(run_fixture()[0])
        except Exception:
            _MODE_EFFORT_GATE = False
    return _MODE_EFFORT_GATE


def _slugify_project(cwd: str) -> str:
    """Turn a working directory into the slug Claude Code uses for ~/.claude/projects/<slug>/.

    Matches the observed naming pattern: ``:``, ``\\``, ``/``, ``_``, and
    spaces all become ``-``. Case is preserved.
    """
    if not cwd:
        return ""
    out = cwd
    for ch in (":", "\\", "/", "_", " "):
        out = out.replace(ch, "-")
    return out


def _log_eval_row(prompt_text: str, payload: dict, tier=None, me=None) -> None:
    """Append one hashed eval row to ~/.claude/.smart_router_eval.jsonl.

    Privacy: stores sha256(prompt)[:16] and a word count; never the body.
    Caller MUST wrap this in try/except — a logger failure must never
    block the user's prompt (the hook's load-bearing invariant).
    """
    sid = payload.get("session_id") or ""
    cwd = payload.get("cwd") or ""
    row = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session_id": sid,
        "project": _slugify_project(cwd),
        "prompt_hash": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:16],
        "prompt_len_words": len(prompt_text.split()),
        "suggested_model_or_null": tier.model if tier is not None else None,
        "suggested_mode_or_null": me.mode if me is not None else None,
        "suggested_effort_or_null": me.effort if me is not None else None,
        "invoked_skill_or_null": None,
    }
    EVAL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVAL_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _extract_prompt(raw: str) -> str:
    """Pull the user prompt out of the stdin payload.

    Claude Code passes a JSON object with the prompt field. Be defensive:
    accept multiple shapes, fall back to raw stdin when JSON parsing fails.
    """
    if not raw:
        return ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw  # treat raw stdin as prompt text
    if not isinstance(payload, dict):
        return ""
    for key in ("prompt", "user_prompt", "userPrompt", "text"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""


def main() -> int:
    try:
        raw = sys.stdin.read()
    except Exception:
        return 0

    prompt_text = _extract_prompt(raw)
    if not prompt_text.strip():
        return 0

    try:
        payload_obj = json.loads(raw) if raw else {}
        if not isinstance(payload_obj, dict):
            payload_obj = {}
    except json.JSONDecodeError:
        payload_obj = {}

    try:
        tier = recommend_model_tier(prompt_text)
    except Exception:
        tier = None

    try:
        me = recommend_mode_effort(prompt_text)
    except Exception:
        me = None

    if _eval_log_enabled():
        try:
            _log_eval_row(prompt_text, payload_obj, tier, me)
        except Exception:
            pass  # logger must never block the prompt

    hints: list[str] = []
    if tier is not None:
        tier_hint = format_model_tier(tier)
        if me is not None and _mode_effort_enabled():
            tier_hint = tier_hint + format_mode_effort(me)
        hints.append(tier_hint)
    hints.append(STANDING_DISCIPLINE)

    text = "\n".join(hints)
    if len(text) > MAX_INJECTED_CHARS:
        text = text[: MAX_INJECTED_CHARS - 3] + "..."

    decision = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": text,
        }
    }
    print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
