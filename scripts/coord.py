#!/usr/bin/env python3
"""coord.py -- shared cross-window coordination ledger for concurrent Claude windows.

Problem: several Claude Code windows can run on the same repo at once (different
worktrees / branches / sessions). They must not commit or merge the same files,
and must be able to see "who is doing what" so work doesn't collide. A running
Claude window cannot be pushed messages from outside (see window_watchdog.py /
load_retry_runner.py for that hard limit), so coordination is PULL-based: every
window reads + writes a SHARED journal at its own turn boundaries.

This CLI is the safe, deterministic writer for that journal. The model never
edits the journal directly (two windows Edit-ing one markdown file clobber each
other); instead each window calls this CLI, which mutates a JSON state file
under a cross-process file LOCK and then renders a human-readable work.md view.

Where the journal lives: a single shared, UNTRACKED location that every worktree
of the same repo resolves to identically, via `git rev-parse --git-common-dir`
(the common .git dir shared across all worktrees). Hash that -> a stable repo
key -> ~/.claude/.coord/<key>/{state.json, work.md, .lock}. Nothing is written
into the repo, so there are no merge conflicts and no tracked churn.

state.json shape:
{
  "repo":       "<abs path of main worktree>",
  "updated_at": iso8601,
  "windows": {
    "<session6>": {
      "session": "<session6>", "pid": int, "host": str,
      "start": iso8601|null,            # process start time (PID-reuse defense; best-effort)
      "branch": str|null, "worktree": str|null,
      "first_seen": iso8601, "hb": iso8601,   # hb = last heartbeat
      "note": str,                       # what this window is doing right now
      "claims": ["<repo-relative path>", ...]   # files/tasks this window owns
    }, ...
  }
}

Subcommands (every mutating one takes --session; falls back to $CLAUDE_SESSION_ID):
  register  --session S [--note T] [--branch B] [--worktree W]   upsert this window
  beat      --session S [--note T]                               refresh heartbeat (+note)
  claim     --session S PATH [PATH ...]                          claim files if free
  release   --session S [PATH ...]                               drop some/all claims
  claim-task   --session S ID [--title T]                       atomically check out a task
  release-task --session S [ID]                                 give a task back (none = all mine)
  finish-task  --session S ID                                   mark a task done (not redone)
  tasks                                                         list tasks (held/free/done)
  done      --session S                                          remove this window
  status                                                         render + print work.md
  context   --session S                                          compact machine block (for a hook)
  gc                                                             drop dead windows
  path                                                           print journal dir

Liveness: a window is LIVE if its heartbeat is within --stale seconds
(default 1800). A hook refreshes hb every turn, so a live window never goes
stale; a crashed/closed window ages out and its claims free up. On the same
host a best-effort PID check (psutil if present) can mark a window dead early.
Cross-host windows are judged by heartbeat only and never force-killed.

claim is first-come-first-served and atomic (whole op under the lock): if a
LIVE other window already holds a path, the claim is refused for that path and
reported as a conflict (exit 3), so the caller picks different work.

claim-task is the same guarantee one level up: it leases a TASK id (state
"tasks": {id: {holder, status claimed|done, title, t}}), so two windows never
start the same work even before either touches a file. A task held by a dead
window is free for takeover; a finished one is refused so it is not redone.

Exit codes: 0 ok; 2 bad usage; 3 claim conflict (file or task). Never throws on a corrupt
state file -- it is rebuilt. Kill switch: COORD_DISABLE=1 makes every command a
no-op success; or delete ~/.claude/.coord/<key>/ to reset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
COORD_ROOT = CLAUDE_DIR / ".coord"
DEFAULT_STALE = int(os.environ.get("COORD_STALE_SECONDS", "1800"))  # 30 min
LOCK_TIMEOUT = 10.0   # seconds to wait for the cross-process lock (CLI ops)
LOCK_STALE = 60.0     # break a lock dir older than this (a crashed holder)
# Per-turn hook budget: a board refresh can wait a turn, a user prompt cannot.
# If the lock is busy longer than this, hook_tick skips silently instead of
# stalling the UserPromptSubmit dispatcher toward its 20s timeout.
HOOK_LOCK_TIMEOUT = float(os.environ.get("COORD_HOOK_LOCK_TIMEOUT", "2.0"))
# A dead recorded pid does NOT kill a window whose heartbeat is younger than
# this: registrations made through a transient wrapper (see _window_pid) must
# survive until their next beat re-stamps a live pid. Crashed windows still
# get GC'd once their heartbeat passes this grace instead of instantly.
PID_DEAD_GRACE = int(os.environ.get("COORD_PID_DEAD_GRACE", "300"))
EVENTS_KEEP = 25      # recent activity lines retained in work.md
TASKS_DONE_KEEP = 50  # finished tasks remembered (so a done task is not redone)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _age_seconds(iso: str | None) -> float:
    dt = _parse_iso(iso)
    if dt is None:
        return float("inf")
    return (datetime.now(timezone.utc) - dt).total_seconds()


# --------------------------------------------------------------------------- repo key

def _git(args: list[str], cwd: str | None = None) -> str | None:
    cmd = ["git"] + (["-C", cwd] if cwd else []) + list(args)
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def _fs_git_identity(cwd: str | None = None) -> tuple[str | None, str | None]:
    """(git-common-dir abs, branch) read straight off the filesystem, NO subprocess.

    `git rev-parse --git-common-dir --abbrev-ref HEAD` needs a git.exe spawn,
    measured at 2-3s on this Windows box (three resident AV engines inspect
    every process launch), and hook_tick runs it on EVERY prompt -- it was 97%
    of the UserPromptSubmit hook's wall time and the reason the dispatcher kept
    hitting its timeout. Both facts are plain files, so read them directly:

      - <worktree>/.git is either the git dir itself (normal clone) or a file
        "gitdir: <path>" (linked worktree / submodule);
      - a linked worktree's git dir contains `commondir`, whose contents are
        exactly what --git-common-dir prints;
      - <gitdir>/HEAD holds "ref: refs/heads/<branch>", or a raw sha when
        detached -- which --abbrev-ref reports as the literal "HEAD".

    Returns (None, None) for anything unusual (bare repo, unreadable files, not
    a worktree) so the caller falls back to the git CLI and behaviour is
    unchanged. Kill switch: COORD_FS_IDENTITY=0 forces the CLI path.
    """
    if os.environ.get("COORD_FS_IDENTITY", "1").strip() in ("0", "false", "False"):
        return None, None
    try:
        start = Path(cwd).resolve() if cwd else Path.cwd().resolve()
        dot = None
        for d in [start, *start.parents]:
            cand = d / ".git"
            if cand.exists():
                dot = cand
                break
        if dot is None:
            return None, None

        if dot.is_dir():
            gitdir = dot
        else:  # linked worktree / submodule: a file pointing at the real gitdir
            txt = dot.read_text(encoding="utf-8", errors="replace").strip()
            if not txt.startswith("gitdir:"):
                return None, None
            gp = Path(txt.split(":", 1)[1].strip())
            gitdir = (gp if gp.is_absolute() else dot.parent / gp).resolve()

        common = gitdir
        cf = gitdir / "commondir"
        if cf.is_file():
            rel = cf.read_text(encoding="utf-8", errors="replace").strip()
            if rel:
                cp = Path(rel)
                common = (cp if cp.is_absolute() else gitdir / cp).resolve()

        branch = None
        head = gitdir / "HEAD"
        if head.is_file():
            h = head.read_text(encoding="utf-8", errors="replace").strip()
            if h.startswith("ref:"):
                ref = h.split(":", 1)[1].strip()
                # Keep the full branch path after refs/heads/ -- "feature/x"
                # must not be truncated to "x" the way a naive rsplit would.
                branch = ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref or None
            elif h:
                branch = "HEAD"  # detached; matches `git rev-parse --abbrev-ref`
        return str(common.resolve()), branch
    except Exception:
        return None, None


def repo_identity(cwd: str | None = None) -> tuple[str, str | None, str | None]:
    """Return (key, main_worktree_abs, branch). key is stable across all worktrees
    of one repo. Falls back to cwd when not in a git repo. cwd lets a caller
    (e.g. the prompt hook) resolve a repo other than the process cwd WITHOUT an
    in-process chdir (which would corrupt sibling hooks in the dispatcher)."""
    # Filesystem first (no process spawn); the git CLI stays as the fallback for
    # layouts the file reader declines. Both produce the SAME resolved common
    # dir, so the derived repo key is identical either way -- existing boards
    # keep working (asserted in coord_smoketest.py).
    common, branch = _fs_git_identity(cwd)
    if common is None:
        # One git spawn instead of two: rev-parse prints the common dir and the
        # abbreviated HEAD ref on separate lines. A cold git.exe start costs
        # ~1-2.5s on Windows, and this runs on every prompt via the hook.
        combined = _git(["rev-parse", "--git-common-dir", "--abbrev-ref", "HEAD"], cwd=cwd)
        if combined is not None:
            parts = combined.splitlines()
            common = (parts[0].strip() or None) if parts else None
            branch = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
        else:
            # Rare split fallback (e.g. unborn HEAD makes --abbrev-ref fail while
            # the common dir is still resolvable) -- keeps the repo key stable.
            common = _git(["rev-parse", "--git-common-dir"], cwd=cwd)
            branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if common:
        # git -C resolves relative to cwd, so make absolute against it
        cp = Path(common)
        if not cp.is_absolute() and cwd:
            cp = Path(cwd) / cp
        common_abs = str(cp.resolve())
        # main worktree root is the parent of the common .git dir
        main_root = str(Path(common_abs).parent) if Path(common_abs).name == ".git" else common_abs
        seed = common_abs
    else:
        main_root = str(Path(cwd).resolve()) if cwd else str(Path.cwd().resolve())
        seed = main_root
    # Non-cryptographic: a short, stable directory key derived from the repo path.
    # nosemgrep: insecure-hash-algorithm-sha1 -- usedforsecurity=False, not a security hash
    key = hashlib.sha1(seed.lower().encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
    return key, main_root, branch


def journal_dir(cwd: str | None = None) -> Path:
    key, _, _ = repo_identity(cwd)
    return COORD_ROOT / key


# --------------------------------------------------------------------------- locking

def _acquire_lock(lock: Path, timeout: float = LOCK_TIMEOUT) -> bool:
    """Atomic cross-process lock via mkdir (works identically on Windows/POSIX).

    EVERY path is bounded by `timeout`, including the stale-break path. An
    earlier version did `continue` immediately after a failed rmdir -- skipping
    both the deadline check and the sleep -- so a stale lock that could NOT be
    removed (a non-empty dir left by a holder that died mid-write, or a handle
    held by AV/indexer on Windows) spun this loop forever at full CPU. Reached
    through the UserPromptSubmit hook that hung EVERY prompt in EVERY window on
    the repo until Claude Code killed the hook at 20s and discarded all the
    injected context ("UserPromptSubmit hook timed out after 20s").
    """
    deadline = time.time() + timeout
    while True:
        try:
            lock.mkdir(parents=False, exist_ok=False)
            return True
        except FileExistsError:
            _break_if_stale(lock)
        except OSError:
            return False
        if time.time() >= deadline:
            return False
        time.sleep(0.05)


def _break_if_stale(lock: Path) -> None:
    """Best-effort removal of a lock left behind by a crashed holder.

    Never raises and never blocks: on failure the caller simply retries until
    its own deadline. Also handles the non-empty case (debris from a holder
    that died mid-write), which a plain rmdir cannot remove.
    """
    try:
        if (time.time() - lock.stat().st_mtime) <= LOCK_STALE:
            return
    except OSError:
        return
    try:
        lock.rmdir()
        return
    except OSError:
        pass
    try:
        for leftover in lock.iterdir():
            try:
                leftover.unlink()
            except OSError:
                pass
        lock.rmdir()
    except OSError:
        pass


def _release_lock(lock: Path) -> None:
    try:
        lock.rmdir()
    except OSError:
        pass


# --------------------------------------------------------------------------- state io

def _load_state(d: Path) -> dict:
    f = d / "state.json"
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("windows"), dict):
            return data
    except (OSError, ValueError):
        pass
    _, main_root, _ = repo_identity()
    return {"repo": main_root, "updated_at": now_iso(), "windows": {},
            "events": [], "requests": []}


def _save_state(d: Path, state: dict) -> None:
    state["updated_at"] = now_iso()
    f = d / "state.json"
    tmp = d / "state.json.tmp"
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=True), encoding="utf-8")
    os.replace(tmp, f)


def _pid_alive(pid: int | None, host: str, start: str | None = None) -> bool | None:
    """True/False if determinable on this host, else None (unknown -> use heartbeat).

    When the recorded process start time is available, a pid that exists but
    was created at a different time is a REUSED pid -- the original process is
    gone, so report False rather than a false alive.
    """
    if not pid or host != socket.gethostname():
        return None
    try:
        import psutil  # type: ignore
        if not psutil.pid_exists(int(pid)):
            return False
        if start:
            try:
                created = datetime.fromtimestamp(
                    psutil.Process(int(pid)).create_time(), tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
                # compare to the minute: sub-second precision is dropped in ISO
                if created[:16] != start[:16]:
                    return False
            except Exception:
                return None
        return True
    except Exception:
        return None


def _is_live(win: dict, stale: int) -> bool:
    alive = _pid_alive(win.get("pid"), win.get("host", ""), win.get("start"))
    if alive is False and _age_seconds(win.get("hb")) > PID_DEAD_GRACE:
        return False
    return _age_seconds(win.get("hb")) <= stale


def _gc(state: dict, stale: int) -> list[str]:
    dropped = []
    for sid, win in list(state["windows"].items()):
        if not _is_live(win, stale):
            dropped.append(sid)
            del state["windows"][sid]
    return dropped


def _add_event(state: dict, line: str) -> None:
    events = state.setdefault("events", [])
    events.append({"t": now_iso(), "line": line})
    if len(events) > EVENTS_KEEP:
        del events[: len(events) - EVENTS_KEEP]


# --------------------------------------------------------------------------- render

def _render_work_md(state: dict, stale: int) -> str:
    lines = []
    lines.append("# work.md -- live cross-window coordination board")
    lines.append("")
    lines.append("Auto-generated by coord.py. Do NOT hand-edit (it is overwritten).")
    lines.append("All Claude windows on this repo register here; each owns the files")
    lines.append("it has claimed -- do not commit/merge another live window's claims.")
    lines.append("")
    lines.append(f"- repo: {state.get('repo')}")
    lines.append(f"- updated: {state.get('updated_at')}")
    wins = state.get("windows", {})
    live = {s: w for s, w in wins.items() if _is_live(w, stale)}
    lines.append(f"- live windows: {len(live)}")
    lines.append("")
    lines.append("## Active windows")
    if not live:
        lines.append("")
        lines.append("(none registered)")
    for sid, w in sorted(live.items()):
        age = int(_age_seconds(w.get("hb")))
        lines.append("")
        lines.append(f"### [{sid}] {w.get('branch') or '?'} (pid {w.get('pid')}, {w.get('host')})")
        lines.append(f"- worktree: {w.get('worktree') or '?'}")
        lines.append(f"- heartbeat: {w.get('hb')} ({age}s ago)")
        lines.append(f"- doing: {w.get('note') or '-'}")
        claims = w.get("claims") or []
        lines.append(f"- holds ({len(claims)}): {', '.join(claims) if claims else '-'}")
        tasks = _tasks_held_by(state, sid)
        lines.append(f"- tasks ({len(tasks)}): {', '.join(tasks) if tasks else '-'}")
    lines.append("")
    lines.append("## Tasks")
    all_tasks = state.get("tasks", {})
    if not all_tasks:
        lines.append("")
        lines.append("(none)")
    for tid, t in sorted(all_tasks.items()):
        if t.get("status") == "done":
            state_txt = f"done by {t.get('done_by')} at {t.get('done_at')}"
        elif t.get("holder") in live:
            state_txt = f"held by {t.get('holder')} since {t.get('t')}"
        else:
            state_txt = f"FREE (holder {t.get('holder')} gone)"
        title = f" -- {t['title']}" if t.get("title") else ""
        lines.append(f"- {tid}{title}: {state_txt}")
    lines.append("")
    lines.append("## Pending requests / handoffs")
    reqs = [r for r in state.get("requests", []) if r.get("status") in ("open", "answered")]
    if not reqs:
        lines.append("")
        lines.append("(none)")
    for r in reqs:
        lines.append("")
        lines.append(f"### [{r.get('id')}] {r.get('frm')} -> {r.get('to')}  ({r.get('status')})")
        lines.append(f"- posted: {r.get('t')}")
        lines.append(f"- ask: {r.get('note')}")
        if r.get("answer"):
            lines.append(f"- answer ({r.get('answered_by')}): {r.get('answer')}")
    lines.append("")
    lines.append("## Recent activity")
    events = state.get("events", [])
    if not events:
        lines.append("")
        lines.append("(none)")
    for ev in events[-EVENTS_KEEP:]:
        lines.append(f"- {ev.get('t')}  {ev.get('line')}")
    lines.append("")
    return "\n".join(lines)


def _write_work_md(d: Path, state: dict, stale: int) -> None:
    (d / "work.md").write_text(_render_work_md(state, stale), encoding="utf-8")


# --------------------------------------------------------------------------- helpers

SESSION_TRANSCRIPT_MAX_AGE = int(os.environ.get("COORD_SESSION_TRANSCRIPT_MAX_AGE", "900"))
# Two different sessions' transcripts written within this many seconds of
# each other = concurrent windows -> a transcript-derived identity guess is
# ambiguous and mutating commands refuse it (see _session_from_transcripts).
SESSION_AMBIGUITY_SEC = float(os.environ.get("COORD_SESSION_AMBIGUITY_SEC", "5"))


_TRANSCRIPT_GUESS_AMBIGUOUS = False


def _session_from_transcripts(start: str | None = None) -> str | None:
    """Owning window's session id, recovered from the newest transcript on disk.

    Claude Code does NOT export CLAUDE_SESSION_ID into a tool call's shell, so
    every documented CLI mutation ("claim before editing") died on
    "coord <cmd>: no session" -- the hook worked (its stdin payload carries the
    id) but the model's own claims never registered. Claude Code appends the
    tool_use record to ~/.claude/projects/<slug>/<session>.jsonl BEFORE the
    command runs, so the GLOBALLY newest transcript across ALL project dirs
    belongs to the window running this command.

    GUEST-WINDOW BUG (r026fed / f2ddf2 lelet, fixed 2026-08-28): the previous
    version searched only the cwd-slug project dir, so a window VISITING
    another project's tree found the OTHER window's transcript and mutated the
    board under a foreign identity (the r9c5a81 mis-post). The scan is now
    cwd-INDEPENDENT: newest transcript account-wide wins, because the caller
    wrote its own tool_use milliseconds ago regardless of where cwd points.
    `start` is accepted for signature compatibility and ignored.

    AMBIGUITY GUARD: when a transcript of a DIFFERENT session was written
    within SESSION_AMBIGUITY_SEC of the newest one, two windows were writing
    concurrently and the guess is unsafe -- _TRANSCRIPT_GUESS_AMBIGUOUS is
    set, and _session() refuses MUTATING commands under such a guess (the
    caller must pass --session explicitly).

    Returns None (never a guess) when no transcript is fresher than
    SESSION_TRANSCRIPT_MAX_AGE. Kill switch: COORD_SESSION_FROM_TRANSCRIPT=0.
    """
    global _TRANSCRIPT_GUESS_AMBIGUOUS
    _TRANSCRIPT_GUESS_AMBIGUOUS = False
    if os.environ.get("COORD_SESSION_FROM_TRANSCRIPT", "1").strip() in ("0", "false", "False"):
        return None
    del start  # cwd-independent by design; kept for signature compatibility
    try:
        root = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "projects"
        if not root.is_dir():
            return None
        now = time.time()
        best: tuple[float, str] | None = None      # (mtime, session id)
        runner_up: tuple[float, str] | None = None  # newest with a DIFFERENT id
        for f in root.glob("*/*.jsonl"):
            try:
                m = f.stat().st_mtime
            except OSError:
                continue
            if now - m > SESSION_TRANSCRIPT_MAX_AGE:
                continue
            stem = f.stem
            if best is None or m > best[0]:
                if best is not None and best[1] != stem:
                    runner_up = best
                best = (m, stem)
            elif stem != best[1] and (runner_up is None or m > runner_up[0]):
                runner_up = (m, stem)
        if best is None:
            return None
        if runner_up is not None and (best[0] - runner_up[0]) <= SESSION_AMBIGUITY_SEC:
            _TRANSCRIPT_GUESS_AMBIGUOUS = True
        return best[1]
    except Exception:
        return None


def _session(args, mutating: bool = False) -> str | None:
    """Resolve the calling window's session id.

    Explicit sources (--session, CLAUDE_SESSION_ID) are always trusted. A
    transcript-derived GUESS is trusted for read-only commands; for MUTATING
    commands it is refused when two windows wrote transcripts within the
    ambiguity window (a wrong guess would act on the board under a foreign
    identity), and otherwise allowed with a one-line stderr note so any
    misattribution stays visible in the command output."""
    explicit = getattr(args, "session", None) or os.environ.get("CLAUDE_SESSION_ID")
    if explicit:
        return explicit
    guess = _session_from_transcripts()
    if guess is None:
        return None
    if mutating:
        if _TRANSCRIPT_GUESS_AMBIGUOUS:
            sys.stderr.write(
                "coord: session identity would be GUESSED from transcripts, "
                "but two windows wrote within the ambiguity window -- refusing "
                "a mutating command under a guessed identity. Re-run with "
                "--session <your-session-id>.\n")
            return None
        sys.stderr.write(
            f"[coord] session guessed from newest transcript: {guess[:6]}\n")
    return guess


def _proc_start(pid: int) -> str | None:
    try:
        import psutil  # type: ignore
        return datetime.fromtimestamp(
            psutil.Process(pid).create_time(), tz=timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


# Per-event wrappers Claude Code (or the Bash tool) puts between the window
# process and this script. Recording one of these as the window's pid
# self-destructs the board: the wrapper exits the moment the call returns, and
# the next tick's pid-liveness GC drops the window even though the Claude
# window itself is alive.
_TRANSIENT_PARENTS = {
    "cmd.exe", "conhost.exe", "powershell.exe", "pwsh.exe",
    "bash.exe", "sh.exe", "bash", "sh", "zsh", "dash",
    "python.exe", "python3.exe", "python", "python3", "py.exe",
}


def _window_pid() -> int:
    """Nearest long-lived ancestor to represent this Claude window.

    Walks up from getppid() past known per-event wrappers to the first stable
    ancestor (normally the claude/node process). Falls back to plain
    getppid() when psutil or the walk is unavailable.
    """
    ppid = os.getppid()
    try:
        import psutil  # type: ignore
        p = psutil.Process(ppid)
        for _ in range(8):
            if p.name().lower() not in _TRANSIENT_PARENTS:
                return p.pid
            parent = p.parent()
            if parent is None:
                break
            p = parent
        return p.pid
    except Exception:
        return ppid


def _norm_claims(state: dict, sid: str, paths: list[str]) -> list[str]:
    return [p.replace("\\", "/").strip() for p in paths if p.strip()]


def _holder_of(state: dict, path: str, stale: int, exclude: str) -> str | None:
    for s, w in state["windows"].items():
        if s == exclude:
            continue
        if not _is_live(w, stale):
            continue
        if path in (w.get("claims") or []):
            return s
    return None


def _requests_for(state: dict, sid: str, branch: str | None) -> list[dict]:
    """Open requests addressed to this window (by session6, by branch, or '*')."""
    out = []
    for r in state.get("requests", []):
        if r.get("status") != "open":
            continue
        to = r.get("to")
        if to in (sid, "*") or (branch and to == branch):
            out.append(r)
    return out


def _answers_for(state: dict, sid: str) -> list[dict]:
    """Requests THIS window posted that have now been answered (awaiting ack)."""
    return [r for r in state.get("requests", [])
            if r.get("frm") == sid and r.get("status") == "answered"]


def _norm_task(tid: str) -> str:
    """Task ids compare case/whitespace-insensitively: 'Fix Login' == 'fix-login'."""
    return re.sub(r"\s+", "-", (tid or "").strip().lower())


def _task_holder(state: dict, tid: str, stale: int, exclude: str) -> str | None:
    """Live window (other than exclude) currently holding task tid, else None.
    A task whose holder died / left is free: the next claimant takes it over."""
    t = state.get("tasks", {}).get(tid)
    if not t or t.get("status") != "claimed":
        return None
    h = t.get("holder")
    if not h or h == exclude:
        return None
    w = state["windows"].get(h)
    return h if (w and _is_live(w, stale)) else None


def _tasks_held_by(state: dict, sid: str) -> list[str]:
    return sorted(k for k, t in state.get("tasks", {}).items()
                  if t.get("status") == "claimed" and t.get("holder") == sid)


def _trim_done_tasks(state: dict) -> None:
    tasks = state.get("tasks", {})
    done = sorted((t.get("done_at") or "", k) for k, t in tasks.items()
                  if t.get("status") == "done")
    for _, k in done[: max(0, len(done) - TASKS_DONE_KEEP)]:
        del tasks[k]


def hook_tick(session: str | None, cwd: str | None = None,
              note: str | None = None, stale: int = DEFAULT_STALE) -> dict:
    """One-call entry point for the UserPromptSubmit hook: refresh THIS window's
    heartbeat (auto-registering on first sight), GC dead windows, re-render
    work.md, and return the coordination context (other live windows, the paths
    they hold, and any open requests addressed here). Returns {} on any problem
    so the hook can no-op silently. cwd resolves the repo without chdir."""
    if not session:
        return {}
    sid = session[:6]
    # Resolve identity ONCE (journal_dir would run repo_identity a second
    # time -- that used to double the git-spawn cost on every prompt).
    key, main_root, branch = repo_identity(cwd)
    d = COORD_ROOT / key

    def op():
        state = _load_state(d)
        state["repo"] = main_root
        win = state["windows"].get(sid)
        if win is None:
            pid = _window_pid()
            win = {
                "session": sid, "pid": pid, "host": socket.gethostname(),
                "start": _proc_start(pid), "branch": branch,
                "worktree": cwd or str(Path.cwd().resolve()),
                "first_seen": now_iso(), "hb": now_iso(),
                "note": note or "", "claims": [],
            }
            _add_event(state, f"[{sid}] joined on {branch}")
        else:
            win["hb"] = now_iso()
            win["branch"] = branch or win.get("branch")
            if note is not None:
                win["note"] = note
            # A recorded pid that died while the window lives (transient
            # wrapper, harness restart) is re-stamped from the live tree, so
            # the PID_DEAD_GRACE window never has to carry it for long.
            if _pid_alive(win.get("pid"), win.get("host", ""), win.get("start")) is False:
                pid = _window_pid()
                win["pid"] = pid
                win["start"] = _proc_start(pid)
                win["host"] = socket.gethostname()
        state["windows"][sid] = win
        _gc(state, stale)
        _save_state(d, state)
        _write_work_md(d, state, stale)
        others = []
        for s, w in sorted(state["windows"].items()):
            if s == sid or not _is_live(w, stale):
                continue
            others.append({"session": s, "branch": w.get("branch"),
                           "note": w.get("note"), "claims": w.get("claims", []),
                           "tasks": _tasks_held_by(state, s)})
        blocked = sorted({c for o in others for c in o["claims"]})
        return {"self": sid, "branch": branch, "others": others,
                "blocked_paths": blocked,
                "requests_for_me": _requests_for(state, sid, branch),
                "answers_for_me": _answers_for(state, sid)}

    r = _with_lock(d, op, timeout=HOOK_LOCK_TIMEOUT)
    return r if isinstance(r, dict) else {}


# --------------------------------------------------------------------------- commands

def _with_lock(d: Path, fn, timeout: float = LOCK_TIMEOUT):
    d.mkdir(parents=True, exist_ok=True)
    lock = d / ".lock"
    if not _acquire_lock(lock, timeout):
        sys.stderr.write("coord: could not acquire lock\n")
        return 2
    try:
        return fn()
    finally:
        _release_lock(lock)


def _register_into(state: dict, args, sid: str, branch: str | None) -> None:
    """Insert/refresh THIS window in an ALREADY-LOADED state dict.

    Deliberately lock-free: every caller runs inside _with_lock. cmd_beat used
    to call cmd_register() from inside its own lock, which re-entered
    _with_lock on the same directory -- the inner acquire could never win, so
    beat burned the whole LOCK_TIMEOUT and failed with "could not acquire
    lock" for any window not yet on the board (its first beat could never
    register it).
    """
    win = state["windows"].get(sid, {})
    pid = int(args.pid) if getattr(args, "pid", None) else _window_pid()
    win.update({
        "session": sid,
        "pid": pid,
        "host": socket.gethostname(),
        "start": win.get("start") or _proc_start(pid),
        "branch": getattr(args, "branch", None) or branch,
        "worktree": getattr(args, "worktree", None) or str(Path.cwd().resolve()),
        "first_seen": win.get("first_seen") or now_iso(),
        "hb": now_iso(),
        "note": args.note if getattr(args, "note", None) is not None else win.get("note", ""),
        "claims": win.get("claims", []),
    })
    state["windows"][sid] = win
    _add_event(state, f"[{sid}] registered on {win['branch']}")


def cmd_register(args) -> int:
    sid = _session(args, mutating=True)
    if not sid:
        sys.stderr.write("coord register: no --session and no $CLAUDE_SESSION_ID\n")
        return 2
    sid = sid[:6]
    d = journal_dir()
    _, main_root, branch = repo_identity()

    def op():
        state = _load_state(d)
        _register_into(state, args, sid, branch)
        _gc(state, args.stale)
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        return 0

    return _with_lock(d, op)


def cmd_beat(args) -> int:
    sid = _session(args, mutating=True)
    if not sid:
        sys.stderr.write("coord beat: no session\n")
        return 2
    sid = sid[:6]
    # One repo_identity() call gives both the board key and the branch, so the
    # first-beat register path below needs no extra git spawn.
    key, _, branch = repo_identity()
    d = COORD_ROOT / key

    def op():
        state = _load_state(d)
        win = state["windows"].get(sid)
        if win is None:
            # First beat = join. Inline, NOT via cmd_register(), which would
            # re-enter _with_lock on this same dir and deadlock against us.
            _register_into(state, args, sid, branch)
        else:
            win["hb"] = now_iso()
            if args.note is not None:
                if args.note != win.get("note"):
                    _add_event(state, f"[{sid}] {args.note}")
                win["note"] = args.note
        _gc(state, args.stale)
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        return 0

    return _with_lock(d, op)


def cmd_claim(args) -> int:
    sid = _session(args, mutating=True)
    if not sid:
        sys.stderr.write("coord claim: no session\n")
        return 2
    sid = sid[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        _gc(state, args.stale)
        pid = _window_pid()
        win = state["windows"].setdefault(sid, {
            "session": sid, "pid": pid, "host": socket.gethostname(),
            "start": _proc_start(pid), "branch": None,
            "worktree": str(Path.cwd().resolve()),
            "first_seen": now_iso(), "hb": now_iso(), "note": "", "claims": [],
        })
        win["hb"] = now_iso()
        wanted = _norm_claims(state, sid, args.paths)
        conflicts = {}
        granted = []
        for p in wanted:
            holder = _holder_of(state, p, args.stale, exclude=sid)
            if holder:
                conflicts[p] = holder
            elif p not in win["claims"]:
                win["claims"].append(p)
                granted.append(p)
            else:
                granted.append(p)  # already ours (idempotent)
        if granted:
            _add_event(state, f"[{sid}] claimed {', '.join(granted)}")
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        result = {"granted": granted, "conflicts": conflicts}
        sys.stdout.write(json.dumps(result) + "\n")
        return 3 if conflicts else 0

    return _with_lock(d, op)


def cmd_claim_task(args) -> int:
    """Atomically check out a TASK (not a file): only one live window may hold
    a given task id, so two windows never start the same work. First-come wins;
    a task whose holder died is taken over; a finished task is refused (exit 3)
    so it is not redone. Exit 0 granted, 3 held/done elsewhere."""
    sid = _session(args, mutating=True)
    if not sid:
        sys.stderr.write("coord claim-task: no session\n")
        return 2
    sid = sid[:6]
    tid = _norm_task(args.id)
    if not tid:
        sys.stderr.write("coord claim-task: empty task id\n")
        return 2
    key, _, branch = repo_identity()
    d = COORD_ROOT / key

    def op():
        state = _load_state(d)
        _gc(state, args.stale)
        if sid not in state["windows"]:
            _register_into(state, args, sid, branch)
        state["windows"][sid]["hb"] = now_iso()
        tasks = state.setdefault("tasks", {})
        t = tasks.get(tid)
        out = {"task": tid, "granted": False}
        if t and t.get("status") == "done":
            out.update(reason="done", by=t.get("done_by"), at=t.get("done_at"))
            rc = 3
        elif (holder := _task_holder(state, tid, args.stale, exclude=sid)):
            out.update(reason="held", holder=holder)
            rc = 3
        else:
            prev = (t or {}).get("holder")
            if prev and prev != sid:
                _add_event(state, f"[{sid}] took over task {tid} from {prev} (gone)")
            elif prev != sid:
                _add_event(state, f"[{sid}] claimed task {tid}")
            tasks[tid] = {"id": tid, "title": args.title or (t or {}).get("title") or "",
                          "holder": sid, "status": "claimed",
                          "t": (t or {}).get("t") if prev == sid else now_iso()}
            out["granted"] = True
            rc = 0
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        sys.stdout.write(json.dumps(out) + "\n")
        return rc

    return _with_lock(d, op)


def cmd_release_task(args) -> int:
    """Give a task back unfinished (it becomes free). No id = all my tasks."""
    sid = _session(args, mutating=True)
    if not sid:
        sys.stderr.write("coord release-task: no session\n")
        return 2
    sid = sid[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        tasks = state.get("tasks", {})
        targets = [_norm_task(args.id)] if args.id else _tasks_held_by(state, sid)
        released = [k for k in targets
                    if tasks.get(k, {}).get("holder") == sid
                    and tasks[k].get("status") == "claimed"]
        for k in released:
            del tasks[k]
        if released:
            _add_event(state, f"[{sid}] released task {', '.join(released)}")
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        sys.stdout.write(json.dumps({"released": released}) + "\n")
        return 0

    return _with_lock(d, op)


def cmd_finish_task(args) -> int:
    """Mark a task done so no window picks it up again. Allowed for the holder,
    or for anyone when the task is unheld / its holder is gone. Exit 3 if a
    different live window holds it."""
    sid = _session(args, mutating=True)
    if not sid:
        sys.stderr.write("coord finish-task: no session\n")
        return 2
    sid = sid[:6]
    tid = _norm_task(args.id)
    d = journal_dir()

    def op():
        state = _load_state(d)
        holder = _task_holder(state, tid, args.stale, exclude=sid)
        if holder:
            sys.stdout.write(json.dumps({"task": tid, "done": False,
                                         "reason": "held", "holder": holder}) + "\n")
            return 3
        tasks = state.setdefault("tasks", {})
        t = tasks.get(tid) or {"id": tid, "title": "", "t": now_iso()}
        t.update(status="done", holder=sid, done_by=sid, done_at=now_iso())
        tasks[tid] = t
        _trim_done_tasks(state)
        _add_event(state, f"[{sid}] finished task {tid}")
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        sys.stdout.write(json.dumps({"task": tid, "done": True}) + "\n")
        return 0

    return _with_lock(d, op)


def cmd_tasks(args) -> int:
    """List every known task with its state (held / free / done)."""
    d = journal_dir()
    state = _load_state(d)
    out = []
    for tid, t in sorted(state.get("tasks", {}).items()):
        st = t.get("status")
        if st == "claimed":
            w = state["windows"].get(t.get("holder"))
            st = "held" if (w and _is_live(w, args.stale)) else "free"
        out.append({"task": tid, "title": t.get("title", ""), "state": st,
                    "holder": t.get("holder")})
    sys.stdout.write(json.dumps(out) + "\n")
    return 0


def cmd_release(args) -> int:
    sid = _session(args, mutating=True)
    if not sid:
        sys.stderr.write("coord release: no session\n")
        return 2
    sid = sid[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        win = state["windows"].get(sid)
        if win is None:
            return 0
        targets = _norm_claims(state, sid, args.paths) if args.paths else list(win.get("claims", []))
        win["claims"] = [c for c in win.get("claims", []) if c not in targets]
        win["hb"] = now_iso()
        if targets:
            _add_event(state, f"[{sid}] released {', '.join(targets)}")
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        return 0

    return _with_lock(d, op)


def cmd_done(args) -> int:
    sid = _session(args, mutating=True)
    if not sid:
        sys.stderr.write("coord done: no session\n")
        return 2
    sid = sid[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        if sid in state["windows"]:
            del state["windows"][sid]
            _add_event(state, f"[{sid}] left")
        _gc(state, args.stale)
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        return 0

    return _with_lock(d, op)


def cmd_gc(args) -> int:
    d = journal_dir()

    def op():
        state = _load_state(d)
        dropped = _gc(state, args.stale)
        if dropped:
            _add_event(state, f"gc dropped {', '.join(dropped)}")
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        sys.stdout.write(json.dumps({"dropped": dropped}) + "\n")
        return 0

    return _with_lock(d, op)


def cmd_request(args) -> int:
    """Post a handoff/request to another window (by session6, branch, or '*').
    Use for cross-window asks coord can't do for you -- e.g. 'engine-owner:
    cherry-pick commit 60a8123 (Q1.6 safety fix) into main'. The target window
    sees it in its next-turn context and acts or declines."""
    sid = _session(args, mutating=True)
    if not sid:
        sys.stderr.write("coord request: no session\n")
        return 2
    sid = sid[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        reqs = state.setdefault("requests", [])
        # nosemgrep: insecure-hash-algorithm-sha1 -- non-crypto short request id, usedforsecurity=False
        rid = "r" + hashlib.sha1(f"{now_iso()}{sid}{args.note}".encode(), usedforsecurity=False).hexdigest()[:6]
        reqs.append({"id": rid, "t": now_iso(), "frm": sid, "to": args.to,
                     "note": args.note, "status": "open"})
        _add_event(state, f"[{sid}] -> {args.to}: {args.note}")
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        sys.stdout.write(json.dumps({"id": rid}) + "\n")
        return 0

    return _with_lock(d, op)


def cmd_reply(args) -> int:
    """Answer a request addressed to you. The answer travels BACK to the asker
    (it shows in their `answers_for_me` next turn). Use for the auto-relay
    round-trip: engine asks 'who rebases?' -> you reply -> engine reads it.
    DECISION-GATE: if the ask needs an irreversible op (merge to main, push,
    rebase of live files), do NOT execute it autonomously -- reply with the
    PROPOSED command and 'needs user approval', and surface it to the user."""
    sid = (_session(args, mutating=True) or "")[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        found = False
        for r in state.get("requests", []):
            if r.get("id") == args.id and r.get("status") in ("open", "answered"):
                r["status"] = "answered"
                r["answer"] = args.note
                r["answered_by"] = sid
                r["answered_at"] = now_iso()
                found = True
                _add_event(state, f"[{sid}] answered {args.id}: {args.note}")
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        sys.stdout.write(json.dumps({"answered": found}) + "\n")
        return 0

    return _with_lock(d, op)


def cmd_ack(args) -> int:
    """Close out an answered request you posted (you've read the answer)."""
    sid = (_session(args) or "")[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        for r in state.get("requests", []):
            if r.get("id") == args.id:
                r["status"] = "closed"
                r["acked_by"] = sid
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        sys.stdout.write(json.dumps({"acked": args.id}) + "\n")
        return 0

    return _with_lock(d, op)


def cmd_resolve(args) -> int:
    """Close a request by id (the actor or poster marks it handled/declined)."""
    sid = (_session(args) or "")[:6]
    d = journal_dir()

    def op():
        state = _load_state(d)
        found = False
        for r in state.get("requests", []):
            if r.get("id") == args.id and r.get("status") == "open":
                r["status"] = args.status
                r["resolved_by"] = sid
                r["resolved_at"] = now_iso()
                found = True
                _add_event(state, f"[{sid}] {args.status} {args.id}")
        _save_state(d, state)
        _write_work_md(d, state, args.stale)
        sys.stdout.write(json.dumps({"resolved": found}) + "\n")
        return 0

    return _with_lock(d, op)


def cmd_status(args) -> int:
    d = journal_dir()
    state = _load_state(d)
    sys.stdout.write(_render_work_md(state, args.stale))
    return 0


def cmd_context(args) -> int:
    """Compact machine-readable block for a UserPromptSubmit hook to inject."""
    sid = (_session(args) or "")[:6]
    d = journal_dir()
    state = _load_state(d)
    wins = state.get("windows", {})
    others = []
    for s, w in sorted(wins.items()):
        if s == sid or not _is_live(w, args.stale):
            continue
        others.append({
            "session": s, "branch": w.get("branch"), "note": w.get("note"),
            "claims": w.get("claims", []),
            "tasks": _tasks_held_by(state, s),
        })
    blocked = sorted({c for o in others for c in o["claims"]})
    _, _, branch = repo_identity()
    out = {"self": sid, "others": others, "blocked_paths": blocked,
           "requests_for_me": _requests_for(state, sid, branch),
           "answers_for_me": _answers_for(state, sid)}
    sys.stdout.write(json.dumps(out) + "\n")
    return 0


def cmd_inbox(args) -> int:
    """Compact actionable view for the auto-relay loop: requests addressed to
    me + answers to my own questions. Same-project only (the board is per-repo)."""
    sid = (_session(args) or "")[:6]
    d = journal_dir()
    state = _load_state(d)
    _, _, branch = repo_identity()
    out = {"self": sid,
           "requests_for_me": _requests_for(state, sid, branch),
           "answers_for_me": _answers_for(state, sid)}
    sys.stdout.write(json.dumps(out) + "\n")
    return 0


def cmd_path(args) -> int:
    sys.stdout.write(str(journal_dir()) + "\n")
    return 0


# --------------------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="coord", description="cross-window coordination ledger")
    p.add_argument("--stale", type=int, default=DEFAULT_STALE,
                   help="seconds before a silent window is considered dead")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_session(sp):
        sp.add_argument("--session", default=None)

    sp = sub.add_parser("register"); add_session(sp)
    sp.add_argument("--note", default=None); sp.add_argument("--branch", default=None)
    sp.add_argument("--worktree", default=None); sp.add_argument("--pid", default=None)
    sp.set_defaults(func=cmd_register)

    sp = sub.add_parser("beat"); add_session(sp)
    sp.add_argument("--note", default=None); sp.add_argument("--branch", default=None)
    sp.add_argument("--worktree", default=None); sp.add_argument("--pid", default=None)
    sp.set_defaults(func=cmd_beat)

    sp = sub.add_parser("claim"); add_session(sp)
    sp.add_argument("paths", nargs="+"); sp.set_defaults(func=cmd_claim)

    sp = sub.add_parser("release"); add_session(sp)
    sp.add_argument("paths", nargs="*"); sp.set_defaults(func=cmd_release)

    sp = sub.add_parser("claim-task"); add_session(sp)
    sp.add_argument("id", help="short task id, e.g. fix-login")
    sp.add_argument("--title", default=None, help="one-line description")
    sp.set_defaults(func=cmd_claim_task)

    sp = sub.add_parser("release-task"); add_session(sp)
    sp.add_argument("id", nargs="?", default=None); sp.set_defaults(func=cmd_release_task)

    sp = sub.add_parser("finish-task"); add_session(sp)
    sp.add_argument("id"); sp.set_defaults(func=cmd_finish_task)

    sp = sub.add_parser("tasks"); sp.set_defaults(func=cmd_tasks)

    sp = sub.add_parser("request"); add_session(sp)
    sp.add_argument("--to", required=True, help="target session6, branch name, or '*'")
    sp.add_argument("--note", required=True, help="what you are asking for")
    sp.set_defaults(func=cmd_request)

    sp = sub.add_parser("resolve"); add_session(sp)
    sp.add_argument("id"); sp.add_argument("--status", default="done",
                                           choices=["done", "declined"])
    sp.set_defaults(func=cmd_resolve)

    sp = sub.add_parser("reply"); add_session(sp)
    sp.add_argument("id"); sp.add_argument("--note", required=True)
    sp.set_defaults(func=cmd_reply)

    sp = sub.add_parser("ack"); add_session(sp)
    sp.add_argument("id"); sp.set_defaults(func=cmd_ack)

    sp = sub.add_parser("inbox"); add_session(sp); sp.set_defaults(func=cmd_inbox)

    sp = sub.add_parser("done"); add_session(sp); sp.set_defaults(func=cmd_done)
    sp = sub.add_parser("gc"); sp.set_defaults(func=cmd_gc)
    sp = sub.add_parser("status"); sp.set_defaults(func=cmd_status)
    sp = sub.add_parser("context"); add_session(sp); sp.set_defaults(func=cmd_context)
    sp = sub.add_parser("path"); sp.set_defaults(func=cmd_path)
    return p


def main(argv: list[str] | None = None) -> int:
    if os.environ.get("COORD_DISABLE") == "1":
        return 0  # kill switch: no-op success
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:  # never hard-crash a caller
        sys.stderr.write(f"coord: {e}\n")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
