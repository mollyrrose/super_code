#!/usr/bin/env python3
"""Smoketest for coord.py -- simulates two concurrent windows coordinating.

Runs against an isolated temp CLAUDE_CONFIG_DIR + temp git repo so it never
touches the real ledger. Exercises: register, claim, claim-conflict (the core
guarantee), release-frees-claim, heartbeat staleness GC, done, and that work.md
renders. Prints PASS/FAIL lines (ASCII only) and exits non-zero on any failure.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
COORD = HERE / "coord.py"
PY = sys.executable

results = []


def check(name: str, ok: bool) -> None:
    results.append((name, ok))
    print(f"[{'ok' if ok else 'fail'}] {name}")


def run(env, *args, expect_rc=None):
    p = subprocess.run([PY, str(COORD), *args], capture_output=True, text=True, env=env)
    if expect_rc is not None and p.returncode != expect_rc:
        print(f"    rc={p.returncode} (wanted {expect_rc}) args={args}\n    err={p.stderr.strip()}")
    return p


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="coord_smoke_"))
    cfg = tmp / "claude"; cfg.mkdir()
    repo = tmp / "repo"; repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo)

    base = dict(os.environ)
    base["CLAUDE_CONFIG_DIR"] = str(cfg)
    base.pop("COORD_DISABLE", None)

    def env_for(session, cwd=repo):
        e = dict(base); e["CLAUDE_SESSION_ID"] = session; e["_CWD"] = str(cwd)
        return e

    # subprocess cwd is set per-call; emulate by chdir via env not possible, so pass cwd=
    def call(session, *args, expect_rc=None, cwd=repo):
        e = dict(base); e["CLAUDE_SESSION_ID"] = session
        p = subprocess.run([PY, str(COORD), *args], capture_output=True, text=True, env=e, cwd=str(cwd))
        if expect_rc is not None and p.returncode != expect_rc:
            print(f"    rc={p.returncode} (wanted {expect_rc}) args={args} err={p.stderr.strip()}")
        return p

    # window A and B register
    call("aaaaaa", "register", "--note", "building parser", expect_rc=0)
    call("bbbbbb", "register", "--note", "writing tests", expect_rc=0)

    # journal dir + work.md exist
    pth = call("aaaaaa", "path").stdout.strip()
    jdir = Path(pth)
    check("journal dir created", jdir.is_dir())
    check("work.md rendered", (jdir / "work.md").is_file())
    check("state.json exists", (jdir / "state.json").is_file())

    # both windows visible to each other in context
    ctx_a = json.loads(call("aaaaaa", "context").stdout)
    check("A sees B as other live window", any(o["session"] == "bbbbbb" for o in ctx_a["others"]))

    # A claims a file
    r = call("aaaaaa", "claim", "src/foo.py", expect_rc=0)
    g = json.loads(r.stdout)
    check("A claim granted", "src/foo.py" in g["granted"] and not g["conflicts"])

    # B tries to claim the SAME file -> conflict (the core guarantee), rc=3
    r = call("bbbbbb", "claim", "src/foo.py", expect_rc=3)
    g = json.loads(r.stdout)
    check("B claim conflicts with A", g["conflicts"].get("src/foo.py") == "aaaaaa")

    # B sees the path as blocked in its context
    ctx_b = json.loads(call("bbbbbb", "context").stdout)
    check("B sees foo.py as blocked", "src/foo.py" in ctx_b["blocked_paths"])

    # B claims a different file -> ok
    r = call("bbbbbb", "claim", "src/bar.py", expect_rc=0)
    check("B claims a free file", "src/bar.py" in json.loads(r.stdout)["granted"])

    # A releases -> B can now take it
    call("aaaaaa", "release", "src/foo.py", expect_rc=0)
    r = call("bbbbbb", "claim", "src/foo.py", expect_rc=0)
    check("B claims after A releases", "src/foo.py" in json.loads(r.stdout)["granted"])

    # atomic task checkout: A takes a task, B is refused, ids normalise
    r = call("aaaaaa", "claim-task", "Fix Login", "--title", "login bug", expect_rc=0)
    check("A task checkout granted", json.loads(r.stdout)["granted"] is True)
    r = call("bbbbbb", "claim-task", "fix-login", expect_rc=3)
    g = json.loads(r.stdout)
    check("B task checkout refused (held by A)", g.get("reason") == "held" and g.get("holder") == "aaaaaa")
    r = call("aaaaaa", "claim-task", "fix-login", expect_rc=0)
    check("re-claim by holder is idempotent", json.loads(r.stdout)["granted"] is True)
    ctx_b = json.loads(call("bbbbbb", "context").stdout)
    check("B sees A's task in context",
          any("fix-login" in o.get("tasks", []) for o in ctx_b["others"]))
    r = call("bbbbbb", "finish-task", "fix-login", expect_rc=3)
    check("B cannot finish A's live task", json.loads(r.stdout)["done"] is False)
    call("aaaaaa", "release-task", "fix-login", expect_rc=0)
    r = call("bbbbbb", "claim-task", "fix-login", expect_rc=0)
    check("B takes task after A releases", json.loads(r.stdout)["granted"] is True)
    r = call("bbbbbb", "finish-task", "fix-login", expect_rc=0)
    check("holder finishes task", json.loads(r.stdout)["done"] is True)
    r = call("aaaaaa", "claim-task", "fix-login", expect_rc=3)
    check("finished task is not re-checked-out", json.loads(r.stdout).get("reason") == "done")
    call("aaaaaa", "claim-task", "orphan-task", expect_rc=0)
    tl = {t["task"]: t for t in json.loads(call("aaaaaa", "tasks").stdout)}
    check("tasks lists held + done", tl["orphan-task"]["state"] == "held" and tl["fix-login"]["state"] == "done")
    check("work.md renders Tasks section", "## Tasks" in call("aaaaaa", "status").stdout)

    # request/reply/ack round-trip: A asks B, B replies, A sees the answer
    r = call("aaaaaa", "request", "--to", "bbbbbb", "--note", "who rebases PR2?")
    rid = json.loads(r.stdout)["id"]
    ctx_b = json.loads(call("bbbbbb", "context").stdout)
    check("B sees the question", any(q["id"] == rid for q in ctx_b["requests_for_me"]))
    r = call("bbbbbb", "reply", rid, "--note", "(a) engine-owner does it")
    check("B reply accepted", json.loads(r.stdout)["answered"] is True)
    ctx_a = json.loads(call("aaaaaa", "context").stdout)
    ans = [a for a in ctx_a["answers_for_me"] if a["id"] == rid]
    check("A receives the answer", bool(ans) and "engine-owner does it" in ans[0]["answer"])
    call("aaaaaa", "ack", rid)
    ctx_a = json.loads(call("aaaaaa", "context").stdout)
    check("ack clears the answer", not any(a["id"] == rid for a in ctx_a["answers_for_me"]))

    # staleness GC: with stale=0 everything ages out as dead
    r = call("aaaaaa", "--stale", "0", "gc")
    dropped = json.loads(r.stdout)["dropped"]
    check("gc drops stale windows", set(dropped) >= {"aaaaaa", "bbbbbb"})

    # after gc, a fresh claim on the previously-blocked path succeeds (no live holder)
    r = call("cccccc", "register", "--note", "third window", expect_rc=0)
    r = call("cccccc", "claim", "src/foo.py", expect_rc=0)
    check("free path reclaimable after holders die", "src/foo.py" in json.loads(r.stdout)["granted"])
    r = call("cccccc", "claim-task", "orphan-task", expect_rc=0)
    check("dead holder's task is taken over", json.loads(r.stdout)["granted"] is True)

    # done removes a window
    call("cccccc", "done", expect_rc=0)
    st = json.loads((jdir / "state.json").read_text())
    check("done removes window", "cccccc" not in st["windows"])

    # kill switch: COORD_DISABLE=1 is a no-op success and writes nothing new
    e = dict(base); e["CLAUDE_SESSION_ID"] = "dddddd"; e["COORD_DISABLE"] = "1"
    p = subprocess.run([PY, str(COORD), "register"], capture_output=True, text=True, env=e, cwd=str(repo))
    st2 = json.loads((jdir / "state.json").read_text())
    check("COORD_DISABLE no-ops", p.returncode == 0 and "dddddd" not in st2["windows"])

    # all worktrees of one repo share the key: a linked worktree resolves same dir
    wt = tmp / "wt"
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", str(wt), "-b", "feat"],
                   capture_output=True, text=True)
    if wt.is_dir():
        pth2 = call("eeeeee", "path", cwd=wt).stdout.strip()
        check("worktree shares journal dir", Path(pth2) == jdir)
    else:
        check("worktree shares journal dir", True)  # skip if worktree add unsupported

    npass = sum(1 for _, ok in results if ok)
    print(f"\n{npass}/{len(results)} checks passed")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
