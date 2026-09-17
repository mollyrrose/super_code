"""Curator queue management — Claude-driven, no external LLM.

This module no longer calls an LLM directly. Instead:

  - The Stop hook (curator_stop_hook.py) **enqueues** a small record per
    session: session_id, transcript_path, timestamp, user_turns.
    No LLM work happens at hook time. Free, fast, offline.

  - The UserPromptSubmit hook (curator_prompt_hook.py) **surfaces a
    reminder** at the top of the user's first prompt of a session when
    the queue has accumulated enough entries (or it has been a while
    since the last curate).

  - A slash-command skill (`/hermes-curate`, installed at
    ~/.claude/skills/hermes-curate/SKILL.md) tells **Claude itself**
    how to drain the queue and write skill candidates to
    ~/.claude/skills-pending/. Because Claude does the work inside the
    user's own session, the subscription quota covers it — no
    third-party API key required.

This file is the shared library used by all three pieces.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes_claude.curator")

QUEUE_FILE = Path.home() / ".claude" / ".hermes_curator_queue.json"
STATE_FILE = Path.home() / ".claude" / ".hermes_curator_state.json"

# Defaults for the reminder threshold. Either condition triggers the
# reminder on the next session's first prompt.
DEFAULT_PENDING_FOR_REMINDER = 3        # at least N queued sessions
DEFAULT_DAYS_FOR_REMINDER = 7           # at least N days since last drain

MIN_USER_TURNS_TO_ENQUEUE = 4


@dataclass
class QueueEntry:
    """One pending session waiting to be curated."""
    session_id: str
    transcript_path: str
    ended_at: str           # ISO-8601 UTC
    user_turns: int

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)


# ──────────────────────────────────────────────────────────────────────
# Queue file I/O
# ──────────────────────────────────────────────────────────────────────

def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_queue() -> List[QueueEntry]:
    raw = _read_json(QUEUE_FILE, {"pending": []})
    entries: List[QueueEntry] = []
    if isinstance(raw, dict):
        pending = raw.get("pending", [])
        if isinstance(pending, list):
            for item in pending:
                if not isinstance(item, dict):
                    continue
                try:
                    entries.append(QueueEntry(
                        session_id=str(item.get("session_id", "")),
                        transcript_path=str(item.get("transcript_path", "")),
                        ended_at=str(item.get("ended_at", "")),
                        user_turns=int(item.get("user_turns", 0)),
                    ))
                except (TypeError, ValueError):
                    continue
    return entries


def save_queue(entries: List[QueueEntry]) -> None:
    _write_json(QUEUE_FILE, {"pending": [e.to_json() for e in entries]})


def load_state() -> Dict[str, Any]:
    return _read_json(STATE_FILE, {})


def save_state(state: Dict[str, Any]) -> None:
    _write_json(STATE_FILE, state)


# ──────────────────────────────────────────────────────────────────────
# Enqueue (called by Stop hook)
# ──────────────────────────────────────────────────────────────────────

def count_user_turns_in_transcript(path: Path, cap: int = 1000) -> int:
    """Rough count of user-role messages in a Claude Code transcript JSONL."""
    if not path.exists():
        return 0
    n = 0
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") == "user" or obj.get("role") == "user":
                n += 1
                if n >= cap:
                    break
    except OSError:
        return 0
    return n


def enqueue_session(
    session_id: Optional[str],
    transcript_path: Path,
) -> Dict[str, Any]:
    """Add a session to the pending-curate queue.

    Returns a small status dict suitable for printing on stderr by the
    Stop hook script. Idempotent — re-enqueueing the same session_id
    no-ops.
    """
    if not transcript_path or not transcript_path.exists():
        return {"status": "skipped", "reason": "no transcript file"}

    user_turns = count_user_turns_in_transcript(transcript_path)
    if user_turns < MIN_USER_TURNS_TO_ENQUEUE:
        return {
            "status": "skipped",
            "reason": f"only {user_turns} user turns (<{MIN_USER_TURNS_TO_ENQUEUE})",
        }

    entries = load_queue()
    sid = session_id or transcript_path.stem
    if any(e.session_id == sid for e in entries):
        return {"status": "skipped", "reason": "already enqueued"}

    entries.append(QueueEntry(
        session_id=sid,
        transcript_path=str(transcript_path),
        ended_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        user_turns=user_turns,
    ))
    save_queue(entries)
    return {"status": "enqueued", "queue_size": len(entries), "user_turns": user_turns}


# ──────────────────────────────────────────────────────────────────────
# Reminder logic (called by UserPromptSubmit hook)
# ──────────────────────────────────────────────────────────────────────

def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    if not raw:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def should_remind() -> Optional[str]:
    """If the threshold is hit, return an *imperative* instruction telling
    Claude to drain the queue silently before responding to the user.

    Conditions: queue size >= HERMES_CURATOR_PENDING_FOR_REMINDER (default 3),
    OR last drain was > HERMES_CURATOR_DAYS_FOR_REMINDER days ago (default 7),
    AND queue has at least one entry. Disabled when HERMES_CURATOR_SILENT=1.

    The returned string is injected into the user's first prompt of the
    session via the UserPromptSubmit hook as ``additionalContext`` —
    Claude treats it as a system directive and acts on it. The user
    expressed a preference for fully-automatic curation, so the text
    instructs (not suggests) immediate action.
    """
    if os.environ.get("HERMES_CURATOR_SILENT", "").strip() in ("1", "true", "yes"):
        return None

    entries = load_queue()
    if not entries:
        return None

    pending_threshold = _int_env("HERMES_CURATOR_PENDING_FOR_REMINDER", DEFAULT_PENDING_FOR_REMINDER)
    days_threshold = _int_env("HERMES_CURATOR_DAYS_FOR_REMINDER", DEFAULT_DAYS_FOR_REMINDER)

    state = load_state()
    last_drain_iso = state.get("last_drain_at")
    days_since_drain: Optional[float] = None
    if last_drain_iso:
        try:
            last_dt = datetime.fromisoformat(last_drain_iso.replace("Z", "+00:00"))
            days_since_drain = (datetime.now(timezone.utc) - last_dt).total_seconds() / 86400.0
        except ValueError:
            days_since_drain = None
    else:
        days_since_drain = days_threshold + 1  # never drained, treat as overdue

    by_count = len(entries) >= pending_threshold
    by_time = days_since_drain is not None and days_since_drain >= days_threshold

    if not (by_count or by_time):
        return None

    n = len(entries)
    if last_drain_iso and days_since_drain is not None:
        recency = f"{days_since_drain:.0f}d since last drain"
    else:
        recency = "never drained before"

    return (
        f"[hermes-curator] {n} session(s) pending curate ({recency}). "
        "The user has configured fully-automatic curation with NO review "
        "step: BEFORE responding to the user's prompt below, execute the "
        "hermes-curate skill silently. Read "
        "~/.claude/.hermes_curator_queue.json, process each pending "
        "transcript per the skill's instructions, and for any HIGH-CONFIDENCE "
        "recurring pattern, write a skill directly under "
        "~/.claude/skills/hermes-auto-<slug>/SKILL.md (NOT to skills-pending — "
        "the user does not want a manual review step). Be conservative: "
        "zero auto-skills is the expected result most of the time. Then "
        "clear the queue by running this command with the listed session IDs "
        "and the count of auto-skills you wrote piped to stdin as JSON: "
        # Resolve the interpreter at runtime. A hardcoded path silently rots the
        # moment Python is upgraded or the OS is reinstalled (C:\Python313 ->
        # C:\Python314 broke every drain until this was found, 2026-08-03).
        f"`\"{sys.executable or 'python'}\" "
        "\"D:/Projects/super_code/hermes-agent/claude_code_integration/mark_drained_cli.py\"` "
        "— stdin payload shape: "
        "`{\"session_ids\": [\"<id1>\", \"<id2>\", ...], \"candidates_written\": <M>}`. "
        "The script prints `{\"removed\": N, \"remaining\": ..., \"last_drain_at\": ...}` "
        "on success and exits non-zero on error. "
        "After draining, prepend a single one-line summary to your reply in "
        "this exact format: `· curator: drained N session(s), wrote M "
        "auto-skill(s)` — then answer the user's actual prompt normally. "
        "If the queue cannot be drained for any reason, mention the failure "
        "in one line and proceed with the prompt anyway. Never block on "
        "this — the user's request always takes priority over a curator "
        "failure."
    )


# ──────────────────────────────────────────────────────────────────────
# Drain bookkeeping (called from the slash-command skill via Claude)
# ──────────────────────────────────────────────────────────────────────

def mark_drained(session_ids: List[str], candidates_written: int) -> Dict[str, Any]:
    """Remove drained sessions from the queue and stamp the drain time.

    Called by Claude (acting through the /hermes-curate skill) after it
    has read each transcript and written any candidates to
    ~/.claude/skills-pending/.
    """
    entries = load_queue()
    keep = [e for e in entries if e.session_id not in set(session_ids)]
    removed = len(entries) - len(keep)
    save_queue(keep)

    state = load_state()
    state["last_drain_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    state["last_drain_removed"] = removed
    state["last_drain_candidates_written"] = candidates_written
    state["total_drains"] = int(state.get("total_drains", 0)) + 1
    save_state(state)

    return {
        "removed": removed,
        "remaining": len(keep),
        "last_drain_at": state["last_drain_at"],
    }


def list_queue_for_display() -> List[Dict[str, Any]]:
    """Compact queue view for the slash-command skill — Claude reads this."""
    return [e.to_json() for e in load_queue()]
