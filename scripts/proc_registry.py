#!/usr/bin/env python3
"""proc_registry.py -- per-window registry of processes a Claude window started,
so the window (or a later one) can find and kill exactly those processes.

Problem: long-running / background commands (dev servers, watchers, test
suites, detached jobs) outlive the turn -- or the whole window -- that started
them, and later nobody knows which of 400 node.exe processes are "ours". This
CLI records every process a window launches through it (pid + process START
time + label + command) and can later kill them by label / pid / all-mine,
tree-wide. The start time defends against PID reuse: a pid whose current
process was created at a different time is NOT the one we started, and is
never killed.

Storage: ~/.claude/.proc_registry/<session6>.json, one file per window, so
concurrent windows never contend for one file (no lock needed). Writes are
atomic (tmp + os.replace).

Subcommands (session = --session, else $CLAUDE_SESSION_ID, else coord.py's
transcript-based guess):
  run   --label L [--detach] -- CMD ...   start CMD, register it; without
                                          --detach wait and unregister on exit
  add   --pid N --label L                 register an already-running process
  list  [--all]                           my entries (+alive), --all = every window
  kill  (--label L | --pid N | --mine)    tree-kill matching live entries, unregister
  gc                                      drop entries whose process is gone (all windows)
  reap-hooks [--older MIN] [--yes]        find hung HOOK processes (harness-spawned,
                                          so never registered) older than MIN minutes
                                          (default 30); dry-run unless --yes

HARD LIMIT (honest): the registry only knows processes launched THROUGH it
(`run`) or registered explicitly (`add`). Processes the harness spawns on its
own -- hook subprocesses, MCP servers -- never pass through here; `reap-hooks`
is the separate, pattern-based sweep for the known leaking hook shapes.

Exit codes: 0 ok; 2 bad usage / no session; `run` without --detach returns the
child's exit code. Kill switch: PROC_REGISTRY_DISABLE=1 makes every command a
no-op (run still executes the command, just unregistered); delete
~/.claude/.proc_registry/ to reset.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
REG_DIR = CLAUDE_DIR / ".proc_registry"
DISABLED = os.environ.get("PROC_REGISTRY_DISABLE") == "1"

# Command-line shapes of harness-spawned hook processes seen leaking on this
# setup (2026-09-30: 358 hung, up to 5 days old). Override with
# PROC_REAP_PATTERNS (a single regex).
DEFAULT_REAP = (r"plugins[\\/]cache[\\/]ecc[\\/].*[\\/]hooks[\\/]"
                r"|run-with-flags|mcp-health-check|const p=require\('path'\)"
                r"|ruflo@latest hooks")

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _start_of(pid: int) -> str | None:
    try:
        return datetime.fromtimestamp(psutil.Process(pid).create_time(),
                                      tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def _alive(entry: dict) -> bool:
    """Alive AND the same process we registered (start time to the minute)."""
    pid = entry.get("pid")
    if not pid or psutil is None or not psutil.pid_exists(int(pid)):
        return False
    st = _start_of(int(pid))
    want = entry.get("start")
    return bool(st) and (not want or st[:16] == want[:16])


def _session(explicit: str | None) -> str | None:
    sid = explicit or os.environ.get("CLAUDE_SESSION_ID")
    if not sid:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import coord  # type: ignore
            sid = coord._session(argparse.Namespace(session=None), mutating=True)
        except Exception:
            sid = None
    return sid[:6] if sid else None


def _file(sid: str) -> Path:
    return REG_DIR / f"{sid}.json"


def _load(sid: str) -> dict:
    try:
        data = json.loads(_file(sid).read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("procs"), list):
            return data
    except Exception:
        pass
    return {"session": sid, "procs": []}


def _save(sid: str, data: dict) -> None:
    REG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _file(sid).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")
    os.replace(tmp, _file(sid))


def _register(sid: str, pid: int, label: str, cmd: str) -> dict:
    data = _load(sid)
    entry = {"pid": pid, "start": _start_of(pid), "label": label,
             "cmd": cmd[:300], "t": now_iso()}
    data["procs"] = [e for e in data["procs"] if e.get("pid") != pid] + [entry]
    _save(sid, data)
    return entry


def _unregister(sid: str, pids: set[int]) -> None:
    data = _load(sid)
    data["procs"] = [e for e in data["procs"] if e.get("pid") not in pids]
    _save(sid, data)


def _kill_tree(pid: int) -> bool:
    try:
        root = psutil.Process(pid)
        procs = root.children(recursive=True) + [root]
        for p in procs:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass
        psutil.wait_procs(procs, timeout=5)
        return True
    except psutil.NoSuchProcess:
        return True
    except Exception:
        return False


def _need_sid(args) -> str | None:
    sid = _session(args.session)
    if not sid:
        sys.stderr.write("proc_registry: no session (--session or $CLAUDE_SESSION_ID)\n")
    return sid


# --------------------------------------------------------------------------- commands

def cmd_run(args) -> int:
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    if not cmd:
        sys.stderr.write("proc_registry run: no command after --\n")
        return 2
    sid = None if DISABLED else _need_sid(args)
    flags = 0
    if args.detach and os.name == "nt":
        # CREATE_NO_WINDOW, not DETACHED_PROCESS: a console-less (detached)
        # parent makes Windows open a NEW visible console for every console
        # child it spawns (python.exe, node.exe) -- a hidden console is
        # inherited by the children instead, so nothing pops up.
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    proc = subprocess.Popen(cmd, creationflags=flags,
                            stdin=subprocess.DEVNULL if args.detach else None,
                            stdout=subprocess.DEVNULL if args.detach else None,
                            stderr=subprocess.DEVNULL if args.detach else None,
                            start_new_session=bool(args.detach and os.name != "nt"))
    if sid:
        _register(sid, proc.pid, args.label, " ".join(cmd))
    if args.detach:
        sys.stdout.write(json.dumps({"pid": proc.pid, "label": args.label}) + "\n")
        return 0
    try:
        return proc.wait()
    finally:
        if sid:
            _unregister(sid, {proc.pid})


def cmd_add(args) -> int:
    if DISABLED:
        return 0
    sid = _need_sid(args)
    if not sid:
        return 2
    if psutil is None or not psutil.pid_exists(args.pid):
        sys.stderr.write(f"proc_registry add: pid {args.pid} not running\n")
        return 2
    try:
        cmd = " ".join(psutil.Process(args.pid).cmdline())
    except Exception:
        cmd = ""
    sys.stdout.write(json.dumps(_register(sid, args.pid, args.label, cmd)) + "\n")
    return 0


def _all_sessions() -> list[str]:
    return sorted(p.stem for p in REG_DIR.glob("*.json")) if REG_DIR.is_dir() else []


def cmd_list(args) -> int:
    if DISABLED:
        return 0
    sids = _all_sessions() if args.all else [s for s in [_need_sid(args)] if s]
    out = []
    for sid in sids:
        for e in _load(sid)["procs"]:
            out.append({**e, "session": sid, "alive": _alive(e)})
    sys.stdout.write(json.dumps(out, indent=1) + "\n")
    return 0


def cmd_kill(args) -> int:
    if DISABLED:
        return 0
    sid = _need_sid(args)
    if not sid:
        return 2
    data = _load(sid)
    targets = [e for e in data["procs"]
               if args.mine
               or (args.label and e.get("label") == args.label)
               or (args.pid and e.get("pid") == args.pid)]
    killed, skipped = [], []
    for e in targets:
        if _alive(e):
            (killed if _kill_tree(int(e["pid"])) else skipped).append(e["pid"])
        else:
            skipped.append(e["pid"])  # gone or pid reused -> never kill a stranger
    _unregister(sid, {e["pid"] for e in targets})  # killed or already gone: drop both
    sys.stdout.write(json.dumps({"killed": killed, "not_alive_or_reused": skipped}) + "\n")
    return 0


def cmd_gc(args) -> int:
    if DISABLED:
        return 0
    dropped = 0
    for sid in _all_sessions():
        data = _load(sid)
        keep = [e for e in data["procs"] if _alive(e)]
        dropped += len(data["procs"]) - len(keep)
        if keep:
            data["procs"] = keep
            _save(sid, data)
        else:
            _file(sid).unlink(missing_ok=True)
    sys.stdout.write(json.dumps({"dropped": dropped}) + "\n")
    return 0


def cmd_reap_hooks(args) -> int:
    if DISABLED:
        return 0
    if psutil is None:
        sys.stderr.write("proc_registry reap-hooks: needs psutil\n")
        return 2
    pat = re.compile(os.environ.get("PROC_REAP_PATTERNS") or DEFAULT_REAP)
    cutoff = datetime.now(timezone.utc).timestamp() - args.older * 60
    hits = []
    for p in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            if (p.info["name"] or "").lower() not in ("node.exe", "node"):
                continue
            if (p.info["create_time"] or 0) > cutoff:
                continue  # young: may be a hook legitimately running right now
            cl = " ".join(p.info["cmdline"] or [])
            if pat.search(cl):
                hits.append((p.info["pid"], cl[:120]))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    killed = 0
    if args.yes:
        for pid, _ in hits:
            try:
                psutil.Process(pid).kill()
                killed += 1
            except Exception:
                pass
    sys.stdout.write(json.dumps({"matched": len(hits), "killed": killed,
                                 "dry_run": not args.yes,
                                 "sample": [c for _, c in hits[:5]]}, indent=1) + "\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="proc_registry",
                                description="per-window registry of started processes")
    sub = p.add_subparsers(dest="cmd_name", required=True)

    def s(sp):
        sp.add_argument("--session", default=None)

    sp = sub.add_parser("run"); s(sp)
    sp.add_argument("--label", required=True); sp.add_argument("--detach", action="store_true")
    sp.add_argument("cmd", nargs=argparse.REMAINDER); sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("add"); s(sp)
    sp.add_argument("--pid", type=int, required=True); sp.add_argument("--label", required=True)
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("list"); s(sp)
    sp.add_argument("--all", action="store_true"); sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("kill"); s(sp)
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--label"); g.add_argument("--pid", type=int)
    g.add_argument("--mine", action="store_true")
    sp.set_defaults(func=cmd_kill)

    sp = sub.add_parser("gc"); sp.set_defaults(func=cmd_gc)

    sp = sub.add_parser("reap-hooks")
    sp.add_argument("--older", type=int, default=30, help="minutes")
    sp.add_argument("--yes", action="store_true", help="actually kill (default: dry-run)")
    sp.set_defaults(func=cmd_reap_hooks)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:  # never hard-crash a caller
        sys.stderr.write(f"proc_registry: {e}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
