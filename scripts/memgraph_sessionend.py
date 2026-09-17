#!/usr/bin/env python3
"""memgraph_sessionend.py -- SessionEnd hook: queue this session for memory ingestion.

Level-5 ("always-on") memory layer, part 1 of 2. At session end this hook
appends {session_id, transcript_path, cwd, ts} to ~/.claude/.memgraph_queue.json.
Only sessions from the super_code project root are queued -- cross-project
ingestion is explicitly blocked (P1 security finding from qRev).
The queue is drained by the memgraph-ingest skill, which the companion
UserPromptSubmit hook (memgraph_prompt_hook.py) triggers when the threshold
is reached. This hook itself does NO extraction and NO network/LLM work --
it only records that a session happened.

Mirrors the curator queue pattern (curator_stop_hook.py): append-only queue,
dedupe by session_id, silent no-op on ANY error so a broken hook can never
block session close.

Kill switch: MEMGRAPH_DISABLE=1, or remove this command from settings.json
SessionEnd (backup noted in CLAUDE.md "Hooks"). Deleting
~/.claude/.memgraph_queue.json resets the queue with no other effect.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

QUEUE_PATH = Path(
    os.environ.get("MEMGRAPH_QUEUE", "")
    or Path(os.environ.get("CLAUDE_CONFIG_DIR", "") or (Path.home() / ".claude"))
    / ".memgraph_queue.json"
)

# Sessions with transcripts smaller than this are trivial (a quick question,
# an aborted window) -- nothing evergreen to ingest.
MIN_TRANSCRIPT_BYTES = int(os.environ.get("MEMGRAPH_MIN_TRANSCRIPT_BYTES", "20000"))

# Only queue sessions from this project root. Cross-project ingestion writes
# another project's session content into this project's memory -- blocked as
# a P1 security finding. Override with MEMGRAPH_PROJECT_ROOT for testing.
_PROJECT_ROOT = Path(
    os.environ.get("MEMGRAPH_PROJECT_ROOT", "") or r"D:\Projects\super_code"
).resolve()


def _is_project_session(cwd: str) -> bool:
    """Return True only when cwd resolves under the project root."""
    if not cwd:
        return False
    try:
        return Path(cwd).resolve().is_relative_to(_PROJECT_ROOT)
    except Exception:
        return False


def main() -> int:
    if os.environ.get("MEMGRAPH_DISABLE") == "1":
        return 0
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # silent no-op on missing/malformed stdin
    try:
        session_id = str(payload.get("session_id") or "").strip()
        transcript = str(payload.get("transcript_path") or "").strip()
        cwd = str(payload.get("cwd") or "").strip()
        if not session_id or not transcript:
            return 0
        # Project scope filter: only queue sessions from this project.
        if not _is_project_session(cwd):
            return 0
        tpath = Path(transcript)
        if not tpath.is_file() or tpath.stat().st_size < MIN_TRANSCRIPT_BYTES:
            return 0
        # Read existing queue -- FileNotFoundError is expected on first run.
        # Any other read error: bail out rather than overwriting with empty state
        # (would drop all pending sessions -- data loss).
        try:
            queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
            if not isinstance(queue, list):
                queue = []
        except FileNotFoundError:
            queue = []
        except Exception:
            return 0  # read error -- do not clobber the existing queue
        if any(e.get("session_id") == session_id for e in queue if isinstance(e, dict)):
            return 0
        queue.append(
            {
                "session_id": session_id,
                "transcript_path": str(tpath),
                "cwd": cwd,
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )
        # Atomic write: temp file in same dir + os.replace to avoid partial writes.
        queue_json = json.dumps(queue, indent=1, ensure_ascii=False)
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=QUEUE_PATH.parent, prefix=".memgraph_queue_tmp_", suffix=".json"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
                fh.write(queue_json)
            os.replace(tmp_path, QUEUE_PATH)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            return 0
    except BaseException:
        return 0  # never block session close, including KeyboardInterrupt
    return 0


if __name__ == "__main__":
    sys.exit(main())
