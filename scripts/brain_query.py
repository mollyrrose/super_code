"""brain_query.py -- deterministic, no-LLM, read-only query layer over the
three learning JSONL streams and the memory dir.

Kill switch: delete this file. No side effects -- read-only.

Env overrides (all optional):
  CLAUDE_CONFIG_DIR          -- Claude config base dir (default: ~/.claude);
                                MUST match what the writing hooks use.
  BRAIN_QUERY_MEMORY_DIR     -- override the memory dir
                                (default: $CLAUDE_CONFIG_DIR/projects/D--Projects-super-code/memory)
  BRAIN_QUERY_ROUTER_FILE    -- override ~/.claude/.smart_router_eval.jsonl path
  BRAIN_QUERY_DECISIONS_FILE -- override ~/.claude/.decision_log.jsonl path
  BRAIN_QUERY_VERDICTS_FILE  -- override ~/.claude/.qrev_verdict_log.jsonl path

Usage:
  python brain_query.py health
  python brain_query.py router [--misses] [--project P] [--last N]
  python brain_query.py decisions [--open] [--reversed] [--since YYYY-MM-DD] [--project P]
  python brain_query.py verdicts [--trend]
  python brain_query.py facts <topic>
  python brain_query.py stale [--memory] [--telos]

Data-sufficiency gates (AI_OS_STRATEGY.md Section 2):
  router features require smart_router_eval.jsonl with >=20 rows.
  decision features require decision_log.jsonl with >=20 rows (currently 15 -- approaching).
  verdict features require qrev_verdict_log.jsonl (currently MISSING -- will warn).
  All gates print a warning but do not abort.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

# Respect CLAUDE_CONFIG_DIR so this reader and the hook writers point at the same files.
CLAUDE_DIR = pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR", str(pathlib.Path.home() / ".claude")))
_default_memory = CLAUDE_DIR / "projects" / "D--Projects-super-code" / "memory"
MEMORY_DIR = pathlib.Path(os.environ.get("BRAIN_QUERY_MEMORY_DIR", str(_default_memory)))
STREAMS: dict[str, pathlib.Path] = {
    "router": pathlib.Path(
        os.environ.get("BRAIN_QUERY_ROUTER_FILE", str(CLAUDE_DIR / ".smart_router_eval.jsonl"))
    ),
    "decisions": pathlib.Path(
        os.environ.get("BRAIN_QUERY_DECISIONS_FILE", str(CLAUDE_DIR / ".decision_log.jsonl"))
    ),
    "verdicts": pathlib.Path(
        os.environ.get("BRAIN_QUERY_VERDICTS_FILE", str(CLAUDE_DIR / ".qrev_verdict_log.jsonl"))
    ),
}
GATE = 20  # minimum rows for full feature availability -- per AI_OS_STRATEGY.md sect.2

_ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _strip_ansi(s: str, limit: int = 200) -> str:
    """Strip ANSI escape sequences from JSONL-derived strings before printing."""
    return _ANSI_RE.sub("", str(s))[:limit]


# ── helpers ──────────────────────────────────────────────────────────────────


def _read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    bad = 0
    # errors='replace': survive cp1252/BOM fragments without crashing the whole stream
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        bad += 1
    except OSError as e:
        # permission / lock / TOCTOU race after the exists() check -- degrade, don't crash
        print(f"  [warn] {path.name}: unreadable ({e.__class__.__name__}) -- returning partial data")
        return rows
    if bad:
        print(f"  [warn] {path.name}: {bad} malformed line(s) skipped")
    return rows


def _gate_warn(name: str, count: int) -> None:
    if count == 0:
        print(f"  [warn] {name}: stream MISSING or empty -- feature disabled")
    elif count < GATE:
        print(f"  [warn] {name}: {count} rows (gate={GATE}) -- partial data, results may be thin")


def _ts(row: dict[str, Any]) -> datetime | None:
    ts_str = row.get("ts") or row.get("timestamp")
    if not ts_str:
        return None
    # Try tz-aware formats first, then tz-naive with UTC assumption to avoid silent exclusion.
    # The literal-Z format belongs in the NAIVE group: strptime's "Z" is a plain
    # character (not %z), so it yields a naive datetime that must be UTC-tagged,
    # or later tz-aware comparisons raise TypeError.
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            pass
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(ts_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


# ── subcommands ──────────────────────────────────────────────────────────────


def cmd_health(_args: argparse.Namespace) -> None:
    print("=== brain_query health ===")
    # Read each stream once and reuse -- the router stream is ~800 KB and growing
    cache: dict[str, list[dict[str, Any]]] = {
        name: _read_jsonl(path) for name, path in STREAMS.items()
    }
    total = 0
    for name, rows in cache.items():
        n = len(rows)
        total += n
        gate_ok = "ok" if n >= GATE else ("warn" if n > 0 else "MISSING")
        print(f"  {name:20s}: {n:5d} rows  [{gate_ok}]")

    if not MEMORY_DIR.exists():
        print(f"  {'memory files':20s}:     0 files  [warn: dir not found: {MEMORY_DIR}]")
    else:
        mem_files = list(MEMORY_DIR.glob("*.md"))
        print(f"  {'memory files':20s}: {len(mem_files):5d} files")
    print(f"  {'TOTAL stream rows':20s}: {total:5d}")

    router_rows = cache["router"]
    if router_rows:
        now = datetime.now(tz=timezone.utc)
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)
        # Single pass over router rows for both trend buckets
        recent = prior = 0
        for r in router_rows:
            t = _ts(r)
            if t is None:
                continue
            if t >= week_ago:
                recent += 1
            elif t >= two_weeks_ago:
                prior += 1
        arrow = "^" if recent >= prior else "v"
        print(f"\n  router last 7d: {recent}  prior 7d: {prior}  trend: {arrow}")

    print("\n  Feature gates:")
    for name, rows in cache.items():
        n = len(rows)
        if n >= GATE:
            print(f"    {name}: OPEN ({n} rows)")
        elif n > 0:
            print(f"    {name}: PARTIAL ({n}/{GATE} rows)")
        else:
            print(f"    {name}: CLOSED (no data)")


def cmd_router(args: argparse.Namespace) -> None:
    rows = _read_jsonl(STREAMS["router"])
    _gate_warn("smart_router_eval", len(rows))
    if not rows:
        return

    if args.project:
        rows = [r for r in rows if r.get("project", "").lower() == args.project.lower()]

    if args.last is not None:
        if args.last < 1:
            print("  [error] --last must be >= 1")
            return
        rows = rows[-args.last:]

    if args.misses:
        # The forward log writes invoked_skill_or_null=None on every row; the backfill
        # script populates it in a SEPARATE file. Only rows with BOTH fields populated
        # are meaningful miss comparisons -- otherwise every suggestion looks like a miss.
        null_invoked = sum(1 for r in rows if r.get("invoked_skill_or_null") is None)
        if null_invoked >= len(rows) * 0.9:
            print(
                f"  [warn] invoked_skill_or_null is unpopulated in {null_invoked}/{len(rows)} rows"
                f" -- run hermes_backfill_router_log.py first; --misses output is not valid"
            )
            # Stop here: printing a 0/0 miss count under an "output is not valid"
            # warning reads as perfect router accuracy to anyone who missed the warning.
            return
        paired = [r for r in rows if r.get("suggested_skill_or_null") and r.get("invoked_skill_or_null")]
        misses = [r for r in paired if r["invoked_skill_or_null"] != r["suggested_skill_or_null"]]
        print(f"Router misses: {len(misses)} / {len(paired)} paired rows (of {len(rows)} total)")
        for r in misses[-20:]:
            print(
                f"  [{_strip_ansi(r.get('ts', '?'), 10)[:10]}] "
                f"suggested={_strip_ansi(r.get('suggested_skill_or_null', ''))}  "
                f"invoked={_strip_ansi(r.get('invoked_skill_or_null', ''))}"
            )
        return

    # Single pass over rows for Counter + null_count
    null_count = 0
    skill_list: list[str] = []
    model_list: list[str] = []
    for r in rows:
        s = r.get("suggested_skill_or_null")
        m = r.get("suggested_model_or_null")
        if s:
            skill_list.append(s)
        else:
            null_count += 1
        if m:
            model_list.append(m)
    suggestions = Counter(skill_list)
    models = Counter(model_list)

    print(f"Router eval rows: {len(rows)}")
    print(f"  No suggestion: {null_count} ({100*null_count//max(len(rows),1)}%)")
    print("\n  Top suggested skills:")
    for skill, n in suggestions.most_common(10):
        print(f"    {n:4d}x  {_strip_ansi(skill)}")
    print("\n  Model tier suggestions:")
    for model, n in models.most_common():
        print(f"    {n:4d}x  {_strip_ansi(model)}")


def cmd_decisions(args: argparse.Namespace) -> None:
    rows = _read_jsonl(STREAMS["decisions"])
    _gate_warn("decision_log", len(rows))
    if not rows:
        return

    if args.project:
        rows = [r for r in rows if r.get("project", "").lower() == args.project.lower()]

    if args.since:
        try:
            cutoff = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            rows = [r for r in rows if (t := _ts(r)) and t >= cutoff]
        except ValueError:
            print(f"  [error] --since must be YYYY-MM-DD, got: {args.since}")
            return

    if args.open and args.reversed:
        print("  [warn] --open and --reversed are mutually exclusive; ignoring --reversed")
    if args.open:
        rows = [r for r in rows if r.get("outcome", "open") == "open"]
    elif args.reversed:
        rows = [r for r in rows if r.get("outcome") == "reversed"]

    print(f"Decisions: {len(rows)} matching")
    for r in rows:
        ts = _strip_ansi(r.get("ts", "?"), 10)[:10]
        title = _strip_ansi(r.get("title", "?"), 160)
        outcome = _strip_ansi(r.get("outcome", "open"), 20)
        project = _strip_ansi(r.get("project", "?"), 60)
        print(f"\n  [{ts}] [{outcome}] [{project}]")
        print(f"  {title}")
        if r.get("why"):
            print(f"  Why: {_strip_ansi(r['why'], 120)}")
        if r.get("revisit_if"):
            print(f"  Revisit if: {_strip_ansi(r['revisit_if'], 80)}")


def cmd_verdicts(args: argparse.Namespace) -> None:
    rows = _read_jsonl(STREAMS["verdicts"])
    _gate_warn("qrev_verdict_log", len(rows))
    if not rows:
        print("  Verdict stream not yet populated. Run /qRev on a project to generate data.")
        return

    print(f"Verdict rows: {len(rows)}")
    if args.trend:
        # TODO: implement rolling approve/block ratio once qrev_verdict_log has data
        print("  (trend analysis not yet implemented)")


def cmd_facts(args: argparse.Namespace) -> None:
    topic = " ".join(args.topic).lower()
    if not MEMORY_DIR.exists():
        print(f"  [warn] memory dir not found: {MEMORY_DIR}")
        print(f"  Set BRAIN_QUERY_MEMORY_DIR to override.")
        return

    hits: list[tuple[pathlib.Path, str]] = []
    for md in sorted(MEMORY_DIR.glob("*.md")):
        if md.name == "MEMORY.md":
            continue
        try:
            # Lowercase once per file to avoid repeated string allocation per line
            text_lower = md.read_text(encoding="utf-8", errors="replace").lower()
        except OSError as e:
            print(f"  [warn] skip {md.name}: {e}")
            continue
        if topic in text_lower:
            for line in text_lower.splitlines():
                if topic in line:
                    hits.append((md, line.strip()[:120]))
                    break

    if not hits:
        print(f"  No memory files mention '{topic}'")
        return

    print(f"Facts matching '{topic}': {len(hits)} file(s)")
    for path, snippet in hits:
        print(f"\n  [{path.stem}]")
        print(f"  {snippet}")


def cmd_stale(args: argparse.Namespace) -> None:
    """Scan for staleness markers in memory/TELOS files."""
    if not MEMORY_DIR.exists():
        print(f"  [warn] memory dir not found: {MEMORY_DIR}")
        print(f"  Set BRAIN_QUERY_MEMORY_DIR to override.")
        return

    show_both = not args.memory and not args.telos
    paths_to_scan: list[pathlib.Path] = []

    if args.telos or show_both:
        telos = MEMORY_DIR / "TELOS.md"
        if telos.exists():
            paths_to_scan.append(telos)

    if args.memory or show_both:
        paths_to_scan.extend(sorted(MEMORY_DIR.glob("*.md")))

    stale_pat = re.compile(r"<!--\s*stale", re.IGNORECASE)
    updated_pat = re.compile(r"<!--\s*last-updated[:\s]+([0-9-]+)", re.IGNORECASE)
    found_any = False

    seen: set[pathlib.Path] = set()
    for path in paths_to_scan:
        if not path.is_file() or path in seen:
            continue
        seen.add(path)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"  [warn] skip {path.name}: {e}")
            continue
        has_stale = bool(stale_pat.search(text))
        updated_matches = updated_pat.findall(text)
        if has_stale or updated_matches:
            found_any = True
            print(f"  {path.name}:")
            for date_str in updated_matches:
                print(f"    last-updated: {date_str}")
            if has_stale:
                print(f"    [warn] stale marker present")

    if not found_any:
        print("  No staleness markers found (TELOS.md not yet created, or no markers set).")


# ── entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="brain_query -- deterministic query layer over the Claude learning streams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_health = sub.add_parser("health", help="Stream counts, gates, and trend summary")
    p_health.set_defaults(func=cmd_health)

    p_router = sub.add_parser("router", help="Query smart_router_eval.jsonl")
    p_router.add_argument("--misses", action="store_true")
    p_router.add_argument("--project")
    p_router.add_argument("--last", type=int, metavar="N")
    p_router.set_defaults(func=cmd_router)

    p_dec = sub.add_parser("decisions", help="Query decision_log.jsonl")
    p_dec.add_argument("--open", action="store_true")
    p_dec.add_argument("--reversed", action="store_true")
    p_dec.add_argument("--since", metavar="YYYY-MM-DD")
    p_dec.add_argument("--project")
    p_dec.set_defaults(func=cmd_decisions)

    p_ver = sub.add_parser("verdicts", help="Query qrev_verdict_log.jsonl")
    p_ver.add_argument("--trend", action="store_true")
    p_ver.set_defaults(func=cmd_verdicts)

    p_facts = sub.add_parser("facts", help="Search memory files for a topic")
    p_facts.add_argument("topic", nargs="+")
    p_facts.set_defaults(func=cmd_facts)

    p_stale = sub.add_parser("stale", help="Scan staleness markers")
    p_stale.add_argument("--memory", action="store_true")
    p_stale.add_argument("--telos", action="store_true")
    p_stale.set_defaults(func=cmd_stale)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
