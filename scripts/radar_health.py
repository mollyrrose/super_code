#!/usr/bin/env python3
"""radar_health.py -- is the weekly AI Radar routine actually landing?

The cloud routine (trigger trig_01SfqhMbYrnRqQwbk4XSQKHp) can "finish" without
doing anything: 2026-09-15..2026-11-03 every scheduled run died in ~10s with a
403 and nobody noticed for 8 weeks. This script checks the effect instead of
the run status: when did a commit last touch okf/ai-radar/ on origin/main?

Read-only. Prints ONE line when the radar is stale (default > 10 days), prints
nothing when healthy, and always exits 0 (safe to call from qRem orientation).

    python ~/.claude/scripts/radar_health.py            # silent if healthy
    python ~/.claude/scripts/radar_health.py --verbose  # always print status
    python ~/.claude/scripts/radar_health.py --json

Env: RADAR_REPO (default D:/Projects/super_code), RADAR_HEALTH_DAYS (default 10),
RADAR_HEALTH_DISABLE=1 (no-op), RADAR_HEALTH_NO_FETCH=1 (skip git fetch).
Fallback when git is unavailable: newest "- YYYY-MM-DD" line in the live mirror
~/.claude/okf/ai-radar/log.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_REPO = "D:/Projects/super_code"
LOG_DATE_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2})\b", re.M)


def _git(repo: str, *args: str, timeout: int = 20) -> str | None:
    try:
        p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout,
                           stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def last_landed_from_git(repo: str, fetch: bool) -> dt.date | None:
    if not Path(repo, ".git").exists():
        return None
    if fetch:
        _git(repo, "fetch", "--quiet", "origin", "main", timeout=30)
    out = _git(repo, "log", "-1", "--format=%cI", "origin/main", "--", "okf/ai-radar")
    if not out:
        return None
    try:
        return dt.datetime.fromisoformat(out).date()
    except ValueError:
        return None


def last_landed_from_log(log_path: Path) -> dt.date | None:
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    dates = []
    for m in LOG_DATE_RE.finditer(text):
        try:
            dates.append(dt.date.fromisoformat(m.group(1)))
        except ValueError:
            pass
    return max(dates) if dates else None


def check(repo: str, log_path: Path, max_days: int, fetch: bool, today: dt.date) -> dict:
    landed, source = last_landed_from_git(repo, fetch), "git origin/main"
    if landed is None:
        landed, source = last_landed_from_log(log_path), "live log.md"
    if landed is None:
        return {"status": "unknown", "source": None, "last": None, "age_days": None}
    age = (today - landed).days
    return {"status": "stale" if age > max_days else "ok", "source": source,
            "last": landed.isoformat(), "age_days": age, "max_days": max_days}


def main(argv: list[str] | None = None) -> int:
    if os.environ.get("RADAR_HEALTH_DISABLE") == "1":
        return 0
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=os.environ.get("RADAR_REPO", DEFAULT_REPO))
    ap.add_argument("--log", default=str(Path.home() / ".claude/okf/ai-radar/log.md"))
    ap.add_argument("--days", type=int, default=int(os.environ.get("RADAR_HEALTH_DAYS", "10")))
    ap.add_argument("--today", help="YYYY-MM-DD (tests)")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    try:
        a = ap.parse_args(argv)
        today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
        fetch = not (a.no_fetch or os.environ.get("RADAR_HEALTH_NO_FETCH") == "1")
        r = check(a.repo, Path(a.log), a.days, fetch, today)
    except Exception:  # never break a caller's orientation
        return 0
    if a.json:
        print(json.dumps(r))
    elif r["status"] == "stale":
        print(f"[radar] the weekly AI Radar has not landed for {r['age_days']} days "
              f"(last {r['last']}, via {r['source']}) -- check the routine's runs "
              f"(RemoteTrigger list_runs trig_01SfqhMbYrnRqQwbk4XSQKHp).")
    elif a.verbose:
        print(f"[radar] {r['status']}: last landed {r['last']} ({r['age_days']}d, via {r['source']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
