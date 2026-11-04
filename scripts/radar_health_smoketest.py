#!/usr/bin/env python3
"""Smoketest for radar_health.py (no network, no real repo)."""
import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import radar_health as rh  # noqa: E402


def run(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = rh.main(list(args))
    return code, buf.getvalue().strip()


def main():
    tmp = Path(tempfile.mkdtemp())
    log = tmp / "log.md"
    log.write_text("# Ingest log\n\n- 2026-11-04 — sweep\n- 2026-09-08 — older\n", encoding="utf-8")
    base = ["--repo", str(tmp / "no-repo"), "--log", str(log), "--no-fetch"]

    code, out = run(*base, "--today", "2026-11-10")
    assert code == 0 and out == "", f"healthy must be silent: {out!r}"

    code, out = run(*base, "--today", "2026-11-20")
    assert code == 0 and "has not landed for 16 days" in out, out

    code, out = run(*base, "--today", "2026-11-10", "--json")
    r = json.loads(out)
    assert r["status"] == "ok" and r["source"] == "live log.md" and r["age_days"] == 6, r

    code, out = run("--repo", str(tmp / "x"), "--log", str(tmp / "missing.md"), "--no-fetch", "--json")
    assert code == 0 and json.loads(out)["status"] == "unknown", out

    code, out = run(*base, "--today", "not-a-date")
    assert code == 0 and out == "", "bad input must be a silent no-op"

    os.environ["RADAR_HEALTH_DISABLE"] = "1"
    code, out = run(*base, "--today", "2026-12-31")
    assert code == 0 and out == "", "kill switch must silence"
    del os.environ["RADAR_HEALTH_DISABLE"]

    print("radar_health smoketest: pass 6")


if __name__ == "__main__":
    main()
