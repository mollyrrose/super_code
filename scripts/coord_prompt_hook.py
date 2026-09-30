#!/usr/bin/env python3
"""UserPromptSubmit hook: keep this window live on the shared coordination board
and inject what the other live windows are doing -- so cross-window collisions
are avoided with ZERO user questions.

Every turn it calls coord.hook_tick(), which:
  - refreshes this window's heartbeat (auto-registering on first sight) so the
    window shows as LIVE and its claims stay valid;
  - GCs windows that went silent (their file claims free up);
  - re-renders work.md;
  - returns the other live windows, the paths they hold, and any open requests
    addressed to this window/branch.

It emits an [coordination] additionalContext block ONLY when there is something
to say (another live window exists, or a request is pending). A solo window adds
no noise. The behavioural rules Claude follows (claim before editing, post a
handoff request for cross-branch work, act on requests addressed to you) live in
the project / global CLAUDE.md "Cross-window coordination" section.

Contract: read JSON payload from stdin ({session_id, cwd, ...}); on anything
missing/malformed, silent no-op (exit 0, no output). Never blocks the user.
Kill switch: COORD_DISABLE=1 (coord.hook_tick returns {} -> no output), or
remove this hook from hook_dispatch.py REGISTRY.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load_coord():
    """Import the sibling coord.py by path (robust under the dispatcher, which
    does not put this dir on sys.path)."""
    try:
        path = _HERE / "coord.py"
        spec = importlib.util.spec_from_file_location("_coord_mod", str(path))
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _build_context(tick: dict) -> str:
    others = tick.get("others") or []
    reqs = tick.get("requests_for_me") or []
    answers = tick.get("answers_for_me") or []
    blocked = tick.get("blocked_paths") or []
    if not others and not reqs and not answers:
        return ""  # solo window, nothing pending -> no noise

    lines = []
    if others:
        lines.append(f"[coordination] {len(others)} other live Claude window(s) on this repo:")
        for o in others:
            held = ", ".join(o.get("claims") or []) or "-"
            note = o.get("note") or "-"
            tasks = ", ".join(o.get("tasks") or []) or "-"
            lines.append(f"- [{o.get('session')}] {o.get('branch') or '?'}: \"{note}\" | holds: {held}"
                         f" | tasks: {tasks}")
        if blocked:
            lines.append("Do NOT edit/commit/merge these files (another live window owns them): "
                         + ", ".join(blocked))
        lines.append("Before editing a file no one holds, claim it: "
                     "`python ~/.claude/scripts/coord.py claim <path>` (on conflict, pick other work).")
        lines.append("Before STARTING a task, check it out: `coord.py claim-task <id> --title \"...\"` "
                     "(exit 3 = another window has it or it is done -> pick other work); "
                     "`coord.py finish-task <id>` when done.")
    if reqs:
        lines.append("Requests addressed to YOU -- answer with `coord.py reply <id> --note \"...\"` "
                     "(or decline). DECISION-GATE: if it needs an irreversible op (merge to main, "
                     "push, rebase of live files), do NOT execute it autonomously -- reply with the "
                     "proposed command + 'needs user approval' and surface it to the user.")
        for r in reqs:
            lines.append(f"- [{r.get('id')}] from {r.get('frm')}: {r.get('note')}")
    if answers:
        lines.append("Answers to YOUR questions arrived (read, then `coord.py ack <id>`):")
        for r in answers:
            lines.append(f"- [{r.get('id')}] {r.get('answered_by')}: {r.get('answer')}")
    return "\n".join(lines)


def main() -> int:
    if os.environ.get("COORD_DISABLE") == "1":
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0
    session = payload.get("session_id") or os.environ.get("CLAUDE_SESSION_ID")
    cwd = payload.get("cwd") or None
    if not session:
        return 0

    coord = _load_coord()
    if coord is None:
        return 0
    try:
        tick = coord.hook_tick(session, cwd=cwd)
    except Exception:
        return 0
    ctx = _build_context(tick if isinstance(tick, dict) else {})
    if ctx:
        sys.stdout.write(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": ctx,
            }
        }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
