#!/usr/bin/env python3
"""Smoketest for proc_registry.py against an isolated temp CLAUDE_CONFIG_DIR.

Exercises: run --detach registers, list shows it alive, kill --label tree-kills
it and unregisters, a pid-reuse entry (wrong start time) is never killed,
foreground run unregisters on exit and passes the exit code through, gc drops
dead entries, reap-hooks is a dry-run by default, and the kill switch.
Prints [ok]/[fail] lines (ASCII only); exits non-zero on any failure.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
REG = HERE / "proc_registry.py"
PY = sys.executable
results = []


def check(name: str, ok: bool) -> None:
    results.append((name, ok))
    print(f"[{'ok' if ok else 'fail'}] {name}")


def main() -> int:
    cfg = Path(tempfile.mkdtemp(prefix="procreg_smoke_"))
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(cfg), CLAUDE_SESSION_ID="aaaaaa11")
    env.pop("PROC_REGISTRY_DISABLE", None)

    def call(*a, extra=None):
        e = dict(env, **(extra or {}))
        return subprocess.run([PY, str(REG), *a], capture_output=True, text=True, env=e)

    sleeper = [PY, "-c", "import time; time.sleep(120)"]

    r = call("run", "--label", "sleeper", "--detach", "--", *sleeper)
    pid = json.loads(r.stdout)["pid"]
    time.sleep(0.5)
    check("detached run registers", r.returncode == 0 and psutil.pid_exists(pid))

    lst = json.loads(call("list").stdout)
    check("list shows it alive", any(e["pid"] == pid and e["alive"] for e in lst))

    r = call("kill", "--label", "sleeper")
    out = json.loads(r.stdout)
    time.sleep(0.5)
    check("kill --label kills it", pid in out["killed"] and not psutil.pid_exists(pid))
    check("kill unregisters", json.loads(call("list").stdout) == [])

    # pid-reuse defense: register a LIVE pid with a fake start time -> must not be killed
    victim = subprocess.Popen(sleeper)
    time.sleep(0.3)
    f = cfg / ".proc_registry" / "aaaaaa.json"
    f.write_text(json.dumps({"session": "aaaaaa", "procs": [
        {"pid": victim.pid, "start": "2000-01-01T00:00:00Z", "label": "stale", "cmd": "", "t": ""}]}))
    out = json.loads(call("kill", "--mine").stdout)
    check("reused pid is never killed", victim.pid in out["not_alive_or_reused"]
          and victim.poll() is None)
    victim.kill()

    # foreground run: exit code passes through and the entry is removed afterwards
    r = call("run", "--label", "fg", "--", PY, "-c", "import sys; sys.exit(7)")
    check("foreground run passes exit code", r.returncode == 7)
    check("foreground run unregisters", json.loads(call("list").stdout) == [])

    # gc drops a dead entry
    f.write_text(json.dumps({"session": "aaaaaa", "procs": [
        {"pid": 999999, "start": None, "label": "dead", "cmd": "", "t": ""}]}))
    check("gc drops dead entries", json.loads(call("gc").stdout)["dropped"] == 1)

    r = json.loads(call("reap-hooks").stdout)
    check("reap-hooks defaults to dry-run", r["dry_run"] is True and r["killed"] == 0)

    r = call("list", extra={"PROC_REGISTRY_DISABLE": "1"})
    check("kill switch no-ops", r.returncode == 0 and r.stdout == "")

    npass = sum(ok for _, ok in results)
    print(f"\n{npass}/{len(results)} checks passed")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
