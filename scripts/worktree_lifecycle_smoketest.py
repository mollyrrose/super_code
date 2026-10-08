#!/usr/bin/env python3
"""Smoketest for worktree_lifecycle.py against a throwaway temp git repo.

Builds main + five worktrees (merged, merge-ready, conflict, dirty, stale),
then checks each gets the right state, the conflict file is named, --gc only
proposes the merged tree for removal (stale = salvage, dirty/ahead = keep),
and nothing was deleted. Prints [ok]/[fail] lines (ASCII only); exits non-zero
on any failure.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / "worktree_lifecycle.py"
PY = sys.executable
results = []


def check(name: str, cond: bool, detail: str = "") -> None:
    results.append(cond)
    print(f"[{'ok' if cond else 'fail'}] {name}" + (f" -- {detail}" if detail and not cond else ""))


def git(cwd: Path, *args: str, env: dict | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={**os.environ, **(env or {})})


def commit(cwd: Path, name: str, text: str, env: dict | None = None) -> None:
    (cwd / name).write_text(text, encoding="utf-8")
    git(cwd, "add", name)
    git(cwd, "commit", "-q", "-m", f"edit {name}", env=env)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="wtlife_smoke_"))
    try:
        repo = tmp / "repo"
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main")
        git(repo, "config", "user.email", "smoke@example.invalid")
        git(repo, "config", "user.name", "smoke")
        commit(repo, "shared.txt", "base\n")

        wts = tmp / "wt"
        for b in ("merged", "ready", "conflict", "dirty", "stale"):
            git(repo, "worktree", "add", "-q", str(wts / b), "-b", b)
            git(wts / b, "config", "user.email", "smoke@example.invalid")
            git(wts / b, "config", "user.name", "smoke")

        commit(wts / "ready", "ready.txt", "new\n")
        commit(wts / "conflict", "shared.txt", "branch side\n")
        commit(repo, "shared.txt", "main side\n")          # main diverges -> conflict
        commit(wts / "dirty", "d.txt", "x\n")
        (wts / "dirty" / "d.txt").write_text("uncommitted\n", encoding="utf-8")
        old = "2020-01-01T00:00:00"
        commit(wts / "stale", "s.txt", "old\n",
               env={"GIT_AUTHOR_DATE": old, "GIT_COMMITTER_DATE": old})

        p = subprocess.run([PY, str(TOOL), "--repo", str(repo), "--gc", "--json"],
                           capture_output=True, text=True)
        check("exit 0", p.returncode == 0, p.stderr)
        rep = json.loads(p.stdout)
        st = {t["branch"]: t["state"] for t in rep["worktrees"]}
        expect = {"main": "main", "merged": "merged", "ready": "merge-ready",
                  "conflict": "conflict", "dirty": "dirty", "stale": "stale"}
        for b, s in expect.items():
            check(f"{b} -> {s}", st.get(b) == s, f"got {st.get(b)}")

        cf = next(t for t in rep["worktrees"] if t["branch"] == "conflict")
        if cf["conflict_method"] == "merge-tree":
            check("conflict file named", "shared.txt" in cf["conflict_files"], str(cf["conflict_files"]))

        plan = rep["plan"]
        check("only merged proposed for removal", [r["branch"] for r in plan["remove"]] == ["merged"],
              str(plan["remove"]))
        check("stale is salvage", [s["branch"] for s in plan["salvage"]] == ["stale"], str(plan["salvage"]))
        kept = {k["branch"] for k in plan["keep"]}
        check("dirty/ready/conflict kept", {"dirty", "ready", "conflict"} <= kept, str(kept))
        check("nothing deleted", all((wts / b).is_dir() for b in expect if b != "main"))

        p2 = subprocess.run([PY, str(TOOL), "--repo", str(repo)], capture_output=True, text=True)
        check("table output", p2.returncode == 0 and "merge-ready" in p2.stdout, p2.stderr)
        p3 = subprocess.run([PY, str(TOOL), "--repo", str(tmp)], capture_output=True, text=True)
        check("non-repo exits 1", p3.returncode == 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"{sum(results)}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
