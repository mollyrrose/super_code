#!/usr/bin/env python3
"""worktree_lifecycle.py -- classify every git worktree of a repo and predict
merge conflicts WITHOUT touching any working tree.

Problem: coord.py knows which window holds which FILE, but nothing tells you
which of the `.worktrees/<branch>/` trees are already merged (safe to remove),
which have gone stale with unmerged work (salvage first), and which branch
would conflict if merged into main right now. This CLI answers that from plain
git facts, deterministically.

Ported (simplified, stdlib-only) from ECC's
`scripts/lib/worktree-lifecycle/{lifecycle,git}.js`
(https://github.com/affaan-m/ECC, MIT License, Copyright (c) 2026 Affaan
Mustafa). Same state machine and the same cleanup safety rule.

States (first match wins):
  main         the primary worktree / the base branch
  detached     no branch checked out
  dirty        uncommitted changes -- never proposed for cleanup
  merged       clean, 0 commits ahead of base -- safe to remove
  conflict     clean, ahead, `git merge-tree` predicts conflicts
  stale        clean, ahead, last commit older than --stale-days -- salvage first
  merge-ready  clean, ahead, no predicted conflict, recent
  idle         anything else

Usage:
  python worktree_lifecycle.py                 # table for the current repo
  python worktree_lifecycle.py --json          # machine-readable report
  python worktree_lifecycle.py --gc            # cleanup PLAN (dry-run, prints commands)
  python worktree_lifecycle.py --base main --stale-days 7 --repo PATH

--gc never deletes anything: it prints the `git worktree remove` / `git branch
-d` commands for merged trees so the user (or a window, after approval) runs
them. Removal is an irreversible op and stays behind the decision-gate.

Conflict prediction needs Git 2.38+ (`merge-tree --write-tree`); older Git
falls back to the legacy three-way form and reports conflict yes/no only.

Kill switch: none needed -- read-only, no hook, nothing persists. Delete the
file to remove it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

DEFAULT_STALE_DAYS = 7
# Inherited git env (e.g. running inside a git hook) would override -C/cwd.
_INHERITED_GIT_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX")
_OID_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)


def _git(args: list[str], cwd: str) -> tuple[int, str]:
    env = {k: v for k, v in os.environ.items() if k not in _INHERITED_GIT_ENV}
    try:
        p = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return p.returncode, p.stdout or ""


def _norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(path))


def list_worktrees(repo: str) -> list[dict]:
    rc, out = _git(["worktree", "list", "--porcelain"], repo)
    if rc != 0:
        return []
    trees: list[dict] = []
    cur: dict | None = None
    for raw in out.splitlines():
        line = raw.strip()
        if line.startswith("worktree "):
            if cur:
                trees.append(cur)
            cur = {"path": line[len("worktree "):].strip(), "branch": None,
                   "head": None, "detached": False, "bare": False}
        elif cur is None:
            continue
        elif line.startswith("branch "):
            cur["branch"] = re.sub(r"^refs/heads/", "", line[len("branch "):].strip())
        elif line.startswith("HEAD "):
            cur["head"] = line[len("HEAD "):].strip()
        elif line == "detached":
            cur["detached"] = True
        elif line == "bare":
            cur["bare"] = True
    if cur:
        trees.append(cur)
    return trees


def is_dirty(path: str) -> bool:
    rc, out = _git(["status", "--porcelain"], path)
    return rc == 0 and bool(out.strip())


def ahead_behind(repo: str, branch: str, base: str) -> dict | None:
    rc, out = _git(["rev-list", "--left-right", "--count", f"{base}...{branch}"], repo)
    m = re.match(r"^(\d+)\s+(\d+)$", out.strip()) if rc == 0 else None
    return {"behind": int(m.group(1)), "ahead": int(m.group(2))} if m else None


def last_commit_ts(repo: str, branch: str) -> int | None:
    rc, out = _git(["log", "-1", "--format=%ct", branch], repo)
    try:
        ts = int(out.strip()) if rc == 0 else 0
    except ValueError:
        return None
    return ts if ts > 0 else None


def predict_conflicts(repo: str, branch: str, base: str) -> dict:
    rc, out = _git(["merge-tree", "--write-tree", "--name-only", base, branch], repo)
    if rc == 0:
        return {"conflicted": False, "files": [], "method": "merge-tree"}
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    if lines:
        # First line is the tree oid; the conflicted paths follow, then a blank
        # line and informational messages (which we stop at).
        files = []
        for l in out.splitlines()[1:]:
            if not l.strip():
                break
            if not _OID_RE.match(l.strip()):
                files.append(l.strip())
        return {"conflicted": True, "files": files, "method": "merge-tree"}
    _, legacy = _git(["merge-tree", base, base, branch], repo)
    marked = bool(re.search(r"^[<=>]{7}|\+<{7}|changed in both", legacy, re.MULTILINE))
    return {"conflicted": marked, "files": [], "method": "merge-tree-legacy"}


def classify(f: dict, stale_s: int, now: int) -> str:
    if f["is_main"]:
        return "main"
    if f["detached"] or not f["branch"]:
        return "detached"
    if f["dirty"]:
        return "dirty"
    ab = f["ahead_behind"]
    ahead = ab["ahead"] if ab else 0
    if ab is not None and ahead == 0:
        return "merged"
    if f["conflict"]:
        return "conflict"
    if ahead > 0 or ab is None:
        old = f["last_ts"] is not None and (now - f["last_ts"]) > stale_s
        return "stale" if old else "merge-ready"
    return "idle"


def build_report(repo: str, base: str = "main", stale_days: float = DEFAULT_STALE_DAYS,
                 now: int | None = None) -> dict:
    now = int(time.time()) if now is None else now
    stale_s = int(stale_days * 86400)
    rc, top = _git(["rev-parse", "--show-toplevel"], repo)
    root = top.strip() if rc == 0 and top.strip() else repo
    trees = []
    for wt in list_worktrees(root):
        if wt["bare"]:
            continue
        branch = wt["branch"]
        is_main = _norm(wt["path"]) == _norm(root) or branch == base
        dirty = is_dirty(wt["path"])
        ab = ahead_behind(root, branch, base) if (not is_main and branch) else None
        last_ts = last_commit_ts(root, branch) if branch else None
        ahead = ab["ahead"] if ab else 0
        conflict = {"conflicted": False, "files": [], "method": None}
        if not is_main and not dirty and branch and ahead > 0:
            conflict = predict_conflicts(root, branch, base)
        facts = {"is_main": is_main, "branch": branch, "detached": wt["detached"],
                 "dirty": dirty, "ahead_behind": ab, "last_ts": last_ts,
                 "conflict": conflict["conflicted"]}
        trees.append({
            "path": wt["path"], "branch": branch, "state": classify(facts, stale_s, now),
            "dirty": dirty, "ahead": ab["ahead"] if ab else None,
            "behind": ab["behind"] if ab else None,
            "age_days": round((now - last_ts) / 86400, 1) if last_ts else None,
            "conflict_files": conflict["files"], "conflict_method": conflict["method"],
        })
    states: dict[str, int] = {}
    for t in trees:
        states[t["state"]] = states.get(t["state"], 0) + 1
    return {"schema": "super_code.worktree-lifecycle.v1", "repo": root, "base": base,
            "stale_days": stale_days, "worktrees": trees, "states": states}


def plan_cleanup(report: dict) -> dict:
    """Safety rule (from ECC): only fully merged trees are proposed for removal.
    Dirty / unmerged trees are kept; stale unmerged trees are salvage-first."""
    remove, salvage, keep = [], [], []
    for t in report["worktrees"]:
        if t["state"] == "main":
            continue
        item = {"path": t["path"], "branch": t["branch"]}
        if t["state"] == "merged":
            remove.append({**item, "reason": "fully merged into base"})
        elif t["dirty"]:
            keep.append({**item, "reason": "has uncommitted changes"})
        elif t["state"] == "stale":
            salvage.append({**item, "reason": f"unmerged + stale ({t['age_days']}d, "
                                              f"{t['ahead']} ahead) - push/bundle before removing"})
        elif (t["ahead"] or 0) > 0:
            keep.append({**item, "reason": f"unmerged work ({t['ahead']} commits ahead)"})
        else:
            keep.append({**item, "reason": f"state {t['state']}"})
    return {"remove": remove, "salvage": salvage, "keep": keep}


def _print_table(report: dict) -> None:
    print(f"repo: {report['repo']}  base: {report['base']}  stale: >{report['stale_days']}d")
    for t in report["worktrees"]:
        ab = "" if t["ahead"] is None else f" +{t['ahead']}/-{t['behind']}"
        age = "" if t["age_days"] is None else f" {t['age_days']}d"
        print(f"  {t['state']:<12} {t['branch'] or '(detached)':<28}{ab}{age}  {t['path']}")
        for f in t["conflict_files"][:10]:
            print(f"      conflict: {f}")
    print("states: " + ", ".join(f"{k}={v}" for k, v in sorted(report["states"].items())))


def _print_plan(plan: dict) -> None:
    print("cleanup plan (dry-run, nothing was deleted):")
    for r in plan["remove"]:
        print(f"  remove   {r['branch']}: {r['reason']}")
        print(f"           git worktree remove \"{r['path']}\" && git branch -d {r['branch']}")
    for s in plan["salvage"]:
        print(f"  salvage  {s['branch']}: {s['reason']}")
    for k in plan["keep"]:
        print(f"  keep     {k['branch']}: {k['reason']}")
    if not (plan["remove"] or plan["salvage"] or plan["keep"]):
        print("  (no secondary worktrees)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Classify git worktrees + predict merge conflicts (read-only).")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--base", default="main")
    ap.add_argument("--stale-days", type=float, default=DEFAULT_STALE_DAYS)
    ap.add_argument("--gc", action="store_true", help="print a cleanup plan (dry-run)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    report = build_report(args.repo, args.base, args.stale_days)
    if not report["worktrees"]:
        print("not a git repo (or git unavailable)", file=sys.stderr)
        return 1
    plan = plan_cleanup(report) if args.gc else None
    if args.json:
        out = dict(report)
        if plan is not None:
            out["plan"] = plan
        print(json.dumps(out, indent=2))
    else:
        _print_table(report)
        if plan is not None:
            _print_plan(plan)
    return 0


if __name__ == "__main__":
    sys.exit(main())
