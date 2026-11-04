#!/usr/bin/env python3
"""tokenjuice.py -- deterministic token/context compression layer for tool output.

WHAT THIS IS FOR
----------------
Verbose tool/command output is where most context-window tokens go to die: a
`git status` in a busy repo, a `cargo build` log, a `docker ps -a` against a real
cluster, a 600-line `pip install` -- each balloons the context for almost no
information gain. This wrapper runs ONE command (or a piped stream) through a
RULE OVERLAY that strips the noise and keeps the signal BEFORE the text reaches
the model, cutting cost + latency with no information loss that matters.

The design is INSPIRED BY (not copied from) openhuman's "TokenJuice" feature:
a three-layer JSON rule overlay (builtin < user < project, later overrides
earlier), each rule naming a command pattern and a list of reduction strategies.
Here it is a standalone Python CLI -- because a Claude Code hook CANNOT rewrite a
tool result before the model sees it (the tool result is fixed by the time a
PostToolUse hook runs; same harness wall load_retry_runner.py / window_watchdog.py
document). So this is OPT-IN: you pipe the noisy command through it.

All strategies are DETERMINISTIC -- pure rules, no LLM call, free, private,
reproducible. (No "summarize with a model" path by design.)

USAGE
-----
    python tokenjuice.py [opts] -- <command...>     # run cmd, compress its output
    python tokenjuice.py [opts] --stdin             # compress piped text
    some-noisy-command | python tokenjuice.py --for "some-noisy-command"
    python tokenjuice.py --probe --for "git status" # show which rules would match
    python tokenjuice.py --list-rules               # dump the merged ruleset
    python tokenjuice.py --json -- git status       # machine-readable stat footer

In `-- <command>` mode the command runs via the shell; its combined stdout+stderr
is compressed and printed to THIS process's stdout, and tokenjuice's own savings
footer goes to stderr (so a downstream pipe stays clean). The exit code is the
command's own exit code, so the wrapper is transparent. In `--stdin` mode the
compressed text goes to stdout and the exit code is 0.

RULE OVERLAY (three layers, later overrides earlier by rule `name`)
------------------------------------------------------------------
    builtin   -- shipped in this file (BUILTIN_RULES below): git, npm, cargo,
                 docker, kubectl, ls, grep/rg, pip, pytest, + a universal rule.
    user      -- ~/.claude/tokenjuice/rules/*.json   (across all projects)
    project   -- ./.tokenjuice/rules/*.json          (repo-specific, committable)
Override TOKENJUICE_USER_DIR / point project dir with --project-dir.

A rule is JSON:
    {
      "name": "git-status",         # unique key; same name in a later layer REPLACES
      "match": "git status",        # matched against the command / --for subject
      "match_kind": "substring",    # substring (default) | regex | glob
      "enabled": true,
      "priority": 0,                # lower applies first; ties keep layer/file order
      "strategies": [               # applied in order, output of one feeds the next
        {"type": "strip_ansi"},
        {"type": "drop_regex", "patterns": ["^\\\\s*\\\\(use "]},
        {"type": "fold_whitespace", "blank_runs": 1},
        {"type": "truncate", "head": 60, "tail": 20, "min_lines": 120}
      ]
    }
The universal rule (match "*") always applies first; specific rules stack after it.

STRATEGIES (all deterministic)
------------------------------
  strip_ansi                         remove ANSI / VT escape sequences
  fold_whitespace {trailing,blank_runs,inner}
                                     rstrip lines; cap consecutive blank lines;
                                     optionally collapse inner space/tab runs
  dedup_lines {mode,keep_count}      drop duplicate lines (consecutive|global),
                                     optionally annotate "(xN)"
  drop_regex {patterns,ignorecase}   drop lines matching ANY pattern
  keep_regex {patterns,ignorecase}   keep ONLY lines matching ANY pattern
  truncate {head,tail,min_lines}     keep head N + tail M lines, fold the middle
  summarize_sections {head,tail,min_lines}
                                     like truncate, plus a one-line stat about the
                                     dropped block (count + most-frequent prefixes)
  html_to_markdown                   lightweight tag strip -> markdown-ish text
  shorten_urls {max_len}             collapse long URLs to scheme://host/...(len)
  condense {content_type,ratio}      structure-aware blob condense via the
                                     sibling tokenjuice_condense.py (ported from
                                     chopratejas/headroom, Apache-2.0): JSON keeps
                                     keys/schema, code keeps imports+signatures,
                                     logs keep errors/traces/summary, secrets and
                                     UUIDs always survive. content_type: auto
                                     (default) | json | code | log | text.
                                     Silent no-op if the module is missing.
                                     Also exposed as the --condense CLI flag.

KILL SWITCH
-----------
  TOKENJUICE_DISABLE=1  -> pass-through: run the command (or cat stdin) with NO
  compression, so a bad rule can never hide output. Or just call the command
  directly without this wrapper. It is a one-off helper -- no daemon, no hook,
  nothing persists when it exits.

Dependencies: none (standard library only). Output is written as UTF-8 with
errors replaced, so multi-byte text (CJK, emoji) survives and a cp1252 Windows
console never crashes on emit.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

# ----------------------------------------------------------------------------
# Builtin rules -- sensible defaults. User/project layers override by `name`.
# Keep every pattern ASCII (cp1252 consoles + grep-ability).
# ----------------------------------------------------------------------------

BUILTIN_RULES = [
    {
        "name": "universal",
        "match": "*",
        "match_kind": "glob",
        "priority": -100,
        "strategies": [
            {"type": "strip_ansi"},
            {"type": "fold_whitespace", "trailing": True, "blank_runs": 1},
        ],
    },
    {
        "name": "git-status",
        "match": "git status",
        "strategies": [
            # the "(use ...)" hint lines carry no signal for a model
            {"type": "drop_regex", "patterns": [r"^\s*\(use "]},
            {"type": "truncate", "head": 80, "tail": 20, "min_lines": 150},
        ],
    },
    {
        "name": "git-log",
        "match": "git log",
        "strategies": [
            {"type": "git_log_commits", "body_lines": 3, "stat_lines": 8},
            # safety net for huge histories / --oneline floods; per-commit
            # summaries are 1-12 lines, so this only trips on very long logs
            {"type": "truncate", "head": 300, "tail": 20, "min_lines": 400},
        ],
    },
    {
        "name": "git-diff",
        "match": "git diff",
        "strategies": [{"type": "truncate", "head": 200, "tail": 40, "min_lines": 300}],
    },
    {
        "name": "npm",
        "match": "npm ",
        "strategies": [
            {"type": "drop_regex", "patterns": [r"^npm WARN deprecated ", r"^\s*$"]},
            {"type": "dedup_lines", "mode": "consecutive"},
            {"type": "truncate", "head": 30, "tail": 50, "min_lines": 120},
        ],
    },
    {
        "name": "cargo",
        "match": "cargo ",
        "strategies": [
            # build/test noise: keep the lines that actually matter
            {"type": "keep_regex",
             "patterns": [r"error", r"warning", r"test result", r"running \d",
                          r"failures:", r"^\s*Compiling", r"Finished", r"FAILED",
                          r"passed", r"panicked"],
             "ignorecase": True},
            {"type": "dedup_lines", "mode": "consecutive"},
            {"type": "truncate", "head": 40, "tail": 60, "min_lines": 120},
        ],
    },
    {
        "name": "docker-ps",
        "match": "docker ps",
        "strategies": [{"type": "truncate", "head": 40, "tail": 0, "min_lines": 60}],
    },
    {
        "name": "kubectl-get",
        "match": "kubectl get",
        "strategies": [{"type": "truncate", "head": 50, "tail": 10, "min_lines": 80}],
    },
    {
        "name": "ls",
        "match": r"^\s*(ls|dir|Get-ChildItem)\b",
        "match_kind": "regex",
        "strategies": [{"type": "truncate", "head": 80, "tail": 20, "min_lines": 150}],
    },
    {
        "name": "grep",
        "match": r"\b(grep|rg|ripgrep|Select-String)\b",
        "match_kind": "regex",
        "strategies": [{"type": "truncate", "head": 120, "tail": 20, "min_lines": 200}],
    },
    {
        "name": "pip",
        "match": "pip install",
        "strategies": [
            {"type": "dedup_lines", "mode": "consecutive"},
            {"type": "drop_regex",
             "patterns": [r"already satisfied", r"^\s*\|", r"^\s*$"],
             "ignorecase": True},
            {"type": "truncate", "head": 20, "tail": 40, "min_lines": 80},
        ],
    },
    {
        "name": "pytest",
        "match": r"\bpytest\b",
        "match_kind": "regex",
        "strategies": [
            {"type": "keep_regex",
             "patterns": [r"PASSED", r"FAILED", r"ERROR", r"passed", r"failed",
                          r"error", r"=====", r"::", r"warnings summary", r"short test"],
             "ignorecase": False},
            {"type": "truncate", "head": 40, "tail": 60, "min_lines": 120},
        ],
    },
]

# ----------------------------------------------------------------------------
# Deterministic strategies. Each takes (text, params) -> text.
# ----------------------------------------------------------------------------

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[@-_]|\x07")
_URL_RE = re.compile(r"(https?://[^\s<>\")]+)")
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>",
                              re.IGNORECASE | re.DOTALL)


def _compile_patterns(patterns, ignorecase):
    flags = re.IGNORECASE if ignorecase else 0
    out = []
    for p in patterns or []:
        try:
            out.append(re.compile(p, flags))
        except re.error:
            # a malformed user pattern must never crash the pipeline -> skip it
            continue
    return out


def s_strip_ansi(text, params):
    return _ANSI_RE.sub("", text)


def s_fold_whitespace(text, params):
    trailing = params.get("trailing", True)
    blank_runs = params.get("blank_runs", 1)   # max consecutive blank lines kept
    inner = params.get("inner", False)         # collapse inner space/tab runs
    out = []
    blanks = 0
    for line in text.split("\n"):
        if trailing:
            line = line.rstrip()
        if inner:
            line = re.sub(r"[ \t]{2,}", " ", line)
        if line.strip() == "":
            blanks += 1
            if blank_runs >= 0 and blanks > blank_runs:
                continue
        else:
            blanks = 0
        out.append(line)
    return "\n".join(out)


def s_dedup_lines(text, params):
    mode = params.get("mode", "consecutive")   # consecutive | global
    keep_count = params.get("keep_count", False)
    lines = text.split("\n")
    out = []
    if mode == "global":
        seen = {}
        order = []
        for ln in lines:
            if ln not in seen:
                seen[ln] = 0
                order.append(ln)
            seen[ln] += 1
        for ln in order:
            out.append(_annotate(ln, seen[ln]) if keep_count else ln)
    else:
        prev = object()
        run = 0
        for ln in lines:
            if ln == prev:
                run += 1
                continue
            if out and keep_count and run > 1:
                out[-1] = _annotate(out[-1], run)
            out.append(ln)
            prev = ln
            run = 1
        if out and keep_count and run > 1:
            out[-1] = _annotate(out[-1], run)
    return "\n".join(out)


def _annotate(line, count):
    return line + ("  (x%d)" % count) if count > 1 else line


def s_drop_regex(text, params):
    pats = _compile_patterns(params.get("patterns"), params.get("ignorecase", False))
    if not pats:
        return text
    return "\n".join(ln for ln in text.split("\n")
                     if not any(p.search(ln) for p in pats))


def s_keep_regex(text, params):
    pats = _compile_patterns(params.get("patterns"), params.get("ignorecase", False))
    if not pats:
        return text
    return "\n".join(ln for ln in text.split("\n")
                     if any(p.search(ln) for p in pats))


def _fold_middle(lines, head, tail, marker):
    dropped = len(lines) - head - tail
    kept = lines[:head]
    kept.append(marker % dropped)
    if tail > 0:
        kept.extend(lines[-tail:])
    return kept, dropped


def s_truncate(text, params):
    head = max(0, int(params.get("head", 60)))
    tail = max(0, int(params.get("tail", 20)))
    min_lines = int(params.get("min_lines", head + tail + 1))
    lines = text.split("\n")
    if len(lines) <= max(min_lines, head + tail + 1):
        return text
    marker = "... [tokenjuice: dropped %d lines] ..."
    kept, _ = _fold_middle(lines, head, tail, marker)
    return "\n".join(kept)


def s_summarize_sections(text, params):
    head = max(0, int(params.get("head", 40)))
    tail = max(0, int(params.get("tail", 20)))
    min_lines = int(params.get("min_lines", head + tail + 1))
    lines = text.split("\n")
    if len(lines) <= max(min_lines, head + tail + 1):
        return text
    middle = lines[head: len(lines) - tail] if tail > 0 else lines[head:]
    stat = _summarize_block(middle)
    marker = "... [tokenjuice: folded %d lines; " + stat + "] ..."
    kept, _ = _fold_middle(lines, head, tail, marker)
    return "\n".join(kept)


def _summarize_block(lines):
    """Deterministic one-line description of a dropped block: line count plus the
    most frequent leading tokens, so the fold still carries some signal."""
    counts = {}
    for ln in lines:
        key = ln.strip().split(" ")[0][:24] if ln.strip() else ""
        if key:
            counts[key] = counts.get(key, 0) + 1
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    if not top:
        return "blank"
    return "top: " + ", ".join("%s x%d" % (k, c) for k, c in top)


_COMMIT_RE = re.compile(r"^commit ([0-9a-f]{7,40})\b(.*)$")
_STAT_RE = re.compile(r"^ \S.* \| +(\d+|Bin)")
_STAT_SUMMARY_RE = re.compile(r"^ \d+ files? changed")
_TRAILER_RE = re.compile(r"^(Co-Authored-By|Claude-Session|Signed-off-by|Reviewed-by|Change-Id):", re.I)


def s_git_log_commits(text, params):
    """Per-commit summary for full-format `git log` (optionally --stat).

    Every commit survives as `<short hash> <date> <subject>` plus at most
    `body_lines` body lines and `stat_lines` diffstat rows (the "N files
    changed" summary is always kept). A head-truncate used to drop whole
    commits (rtk benchmark 2026-11-04: `git log -20` lost 15 of 20).
    Output without `commit <hash>` headers (--oneline, --format) is returned
    unchanged."""
    body_cap = max(0, int(params.get("body_lines", 3)))
    stat_cap = max(0, int(params.get("stat_lines", 8)))
    lines = text.split("\n")
    if not any(_COMMIT_RE.match(ln) for ln in lines):
        return text
    out, commit = [], None

    def flush():
        if commit is None:
            return
        head = "%s %s%s" % (commit["hash"][:9], commit["date"], commit["refs"])
        body = [b for b in commit["body"] if b and not _TRAILER_RE.match(b)]
        out.append((head + " " + (body[0] if body else "")).rstrip())
        extra = body[1:]
        out.extend("    " + b for b in extra[:body_cap])
        if len(extra) > body_cap:
            out.append("    ... [+%d body lines]" % (len(extra) - body_cap))
        out.extend(commit["stat"][:stat_cap])
        if len(commit["stat"]) > stat_cap:
            out.append(" ... [+%d files]" % (len(commit["stat"]) - stat_cap))
        if commit["summary"]:
            out.append(commit["summary"])

    for ln in lines:
        m = _COMMIT_RE.match(ln)
        if m:
            flush()
            commit = {"hash": m.group(1), "refs": m.group(2).rstrip(), "date": "",
                      "body": [], "stat": [], "summary": ""}
            continue
        if commit is None:
            out.append(ln)
            continue
        if ln.startswith("Date:"):
            parts = ln[5:].split()
            # "Wed Nov 4 11:51:20 2026 +0000" -> "Nov 4 2026"
            commit["date"] = " ".join(parts[1:3] + parts[4:5]) if len(parts) >= 5 else ln[5:].strip()
        elif ln.startswith(("Author:", "Merge:", "Commit:", "AuthorDate:", "CommitDate:")):
            continue
        elif _STAT_SUMMARY_RE.match(ln):
            commit["summary"] = ln
        elif _STAT_RE.match(ln):
            commit["stat"].append(ln)
        elif ln.startswith("    "):
            body = ln[4:].rstrip()
            if body or commit["body"]:
                commit["body"].append(body)
    flush()
    # drop trailing blank body lines that survived inside the caps
    return "\n".join(l for l in out if l.strip() != "")


def s_html_to_markdown(text, params):
    text = _SCRIPT_STYLE_RE.sub("", text)
    text = re.sub(r"(?i)<\s*br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</\s*(p|div|tr|li|h[1-6])\s*>", "\n", text)
    text = re.sub(r"(?i)<\s*li[^>]*>", "- ", text)
    text = re.sub(r"(?i)<\s*h1[^>]*>", "# ", text)
    text = re.sub(r"(?i)<\s*h2[^>]*>", "## ", text)
    text = re.sub(r"(?i)<\s*h3[^>]*>", "### ", text)
    # <a href="X">label</a> -> label (X)
    text = re.sub(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                  lambda m: "%s (%s)" % (re.sub(r"\s+", " ", m.group(2)).strip(),
                                         m.group(1)),
                  text)
    text = _TAG_RE.sub("", text)
    # collapse the blank-line storm a tag strip leaves behind
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip("\n")


_condense_module = None


def _get_condense_module():
    """Lazy import of the sibling tokenjuice_condense.py. Returns the module
    or None -- a missing/broken module makes the strategy a silent no-op,
    never a crash (same invariant as every other strategy)."""
    global _condense_module
    if _condense_module is None:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            try:
                import tokenjuice_condense
                _condense_module = tokenjuice_condense
            finally:
                sys.path.pop(0)
        except Exception:
            _condense_module = False
    return _condense_module or None


def s_condense(text, params):
    mod = _get_condense_module()
    if mod is None:
        return text
    ctype = params.get("content_type", "auto")
    if ctype == "auto":
        ctype = None
    ratio = float(params.get("ratio", 0.3))
    out, _meta = mod.condense(text, content_type=ctype, ratio=ratio)
    return out


def s_shorten_urls(text, params):
    max_len = int(params.get("max_len", 60))

    def _short(m):
        url = m.group(1)
        if len(url) <= max_len:
            return url
        mm = re.match(r"(https?://[^/]+)(/.*)?", url)
        if not mm:
            return url
        host = mm.group(1)
        return "%s/...(%dc)" % (host, len(url))

    return _URL_RE.sub(_short, text)


STRATEGIES = {
    "strip_ansi": s_strip_ansi,
    "fold_whitespace": s_fold_whitespace,
    "dedup_lines": s_dedup_lines,
    "drop_regex": s_drop_regex,
    "keep_regex": s_keep_regex,
    "truncate": s_truncate,
    "summarize_sections": s_summarize_sections,
    "git_log_commits": s_git_log_commits,
    "html_to_markdown": s_html_to_markdown,
    "shorten_urls": s_shorten_urls,
    "condense": s_condense,
}


# ----------------------------------------------------------------------------
# Rule loading + overlay merge (builtin < user < project, override by name).
# ----------------------------------------------------------------------------

def _user_dir():
    env = os.environ.get("TOKENJUICE_USER_DIR")
    if env:
        return env
    return os.path.join(os.path.expanduser("~"), ".claude", "tokenjuice", "rules")


def _load_dir(path):
    """Load every *.json under path. Each file is one rule (object) or a list of
    rules. A broken file is skipped, never fatal."""
    rules = []
    if not path or not os.path.isdir(path):
        return rules
    for name in sorted(os.listdir(path)):
        if not name.lower().endswith(".json"):
            continue
        try:
            with open(os.path.join(path, name), "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            continue
        if isinstance(data, dict):
            rules.append(data)
        elif isinstance(data, list):
            rules.extend(r for r in data if isinstance(r, dict))
    return rules


def load_rules(project_dir=None, include_user=True):
    """Merge the three layers. Later layers override earlier ones by `name`."""
    merged = {}
    order = []

    def _absorb(layer_rules, layer):
        for r in layer_rules:
            name = r.get("name")
            if not name:
                continue
            r = dict(r)
            r["_layer"] = layer
            if name not in merged:
                order.append(name)
            merged[name] = r

    _absorb(BUILTIN_RULES, "builtin")
    if include_user:
        _absorb(_load_dir(_user_dir()), "user")
    proj = project_dir if project_dir else os.path.join(os.getcwd(), ".tokenjuice", "rules")
    _absorb(_load_dir(proj), "project")

    rules = [merged[n] for n in order if merged[n].get("enabled", True)]
    # universal / lower priority first; stable on insertion order for ties
    rules.sort(key=lambda r: r.get("priority", 0))
    return rules


def _rule_matches(rule, subject):
    pat = rule.get("match", "*")
    kind = rule.get("match_kind", "substring")
    if pat == "*":
        return True
    if subject is None:
        return False
    try:
        if kind == "regex":
            return re.search(pat, subject) is not None
        if kind == "glob":
            return fnmatch.fnmatch(subject, pat)
        return pat in subject
    except re.error:
        return False


def matching_rules(rules, subject):
    return [r for r in rules if _rule_matches(r, subject)]


# ----------------------------------------------------------------------------
# Compression pipeline
# ----------------------------------------------------------------------------

def compress(text, rules, subject):
    """Apply every matching rule's strategies in order. Returns (text, trace)."""
    trace = []
    for rule in matching_rules(rules, subject):
        for strat in rule.get("strategies", []):
            fn = STRATEGIES.get(strat.get("type"))
            if not fn:
                continue
            before = len(text)
            try:
                text = fn(text, strat)
            except Exception:
                # one bad strategy must not lose the whole output
                continue
            trace.append({"rule": rule.get("name"), "strategy": strat.get("type"),
                          "chars_before": before, "chars_after": len(text)})
    return text, trace


def _est_tokens(chars):
    # cheap, provider-agnostic heuristic: ~4 chars/token
    return (chars + 3) // 4


def _stat(original, compressed):
    o, c = len(original), len(compressed)
    return {
        "chars_in": o, "chars_out": c,
        "tokens_in": _est_tokens(o), "tokens_out": _est_tokens(c),
        "pct_saved": round((1 - c / o) * 100, 1) if o else 0.0,
    }


# ----------------------------------------------------------------------------
# Command execution (capture combined stdout+stderr) with optional tree-kill.
# ----------------------------------------------------------------------------

def _kill_tree(proc):
    try:
        if sys.platform.startswith("win"):
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, timeout=10)
        else:
            proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run_capture(command, timeout=0):
    """Run command via shell, capture combined stdout+stderr. Returns (text, rc)."""
    # nosemgrep: subprocess-shell-true -- `command` is the operator-provided shell command to run+compress; shell semantics required, not untrusted input
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    try:
        out, _ = proc.communicate(timeout=timeout if timeout and timeout > 0 else None)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            out, _ = proc.communicate(timeout=2)
        except Exception:
            out = b""
        rc = None
    text = (out or b"").decode("utf-8", errors="replace")
    return text, rc


# ----------------------------------------------------------------------------
# Output helpers -- always UTF-8, never crash a cp1252 console.
# ----------------------------------------------------------------------------

def _reconfigure_utf8():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _emit_err(msg, quiet):
    if not quiet:
        sys.stderr.write("[tokenjuice] " + msg + "\n")
        sys.stderr.flush()


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def build_arg_parser():
    p = argparse.ArgumentParser(
        description="Deterministic token/context compression layer for tool output.",
        epilog="Everything after -- is the command. KILL SWITCH: TOKENJUICE_DISABLE=1.")
    p.add_argument("--stdin", action="store_true",
                   help="Compress piped stdin instead of running a command.")
    p.add_argument("--for", dest="subject", default=None,
                   help="Subject string used to select rules in --stdin mode.")
    p.add_argument("--no-user", action="store_true",
                   help="Ignore the user rule layer (~/.claude/tokenjuice/rules).")
    p.add_argument("--project-dir", default=None,
                   help="Override the project rule dir (default ./.tokenjuice/rules).")
    p.add_argument("--timeout", type=float, default=0.0,
                   help="Hard timeout for -- command; kills the tree (0 = none).")
    p.add_argument("--raw", action="store_true",
                   help="Skip compression (pass-through); still runs the command.")
    p.add_argument("--quiet", action="store_true",
                   help="Suppress the savings footer on stderr.")
    p.add_argument("--json", action="store_true",
                   help="Print a machine-readable stat line on stderr.")
    p.add_argument("--explain", action="store_true",
                   help="With --json, include the per-strategy trace.")
    p.add_argument("--condense", action="store_true",
                   help="Also apply the structure-aware condense strategy "
                        "(auto-detected JSON/code/log/text) after the rules.")
    p.add_argument("--probe", action="store_true",
                   help="Show which rules match --for/<command>, then exit 0.")
    p.add_argument("--list-rules", action="store_true",
                   help="Dump the merged ruleset as JSON, then exit 0.")
    p.add_argument("command", nargs=argparse.REMAINDER,
                   help="Command after -- (e.g. -- git status).")
    return p


def _strip_leading_dashdash(rest):
    return rest[1:] if rest and rest[0] == "--" else rest


def main(argv=None):
    _reconfigure_utf8()
    args = build_arg_parser().parse_args(argv)
    rules = load_rules(project_dir=args.project_dir, include_user=not args.no_user)

    if args.list_rules:
        print(json.dumps(rules, indent=2))
        return 0

    parts = _strip_leading_dashdash(args.command)
    command = " ".join(parts) if parts else None
    # On Windows, spaces in path components break cmd.exe shell parsing (e.g.
    # "C:/Users/Jane Doe/..." splits at the space). Use list2cmdline to
    # produce double-quoted tokens that cmd.exe understands.  The unquoted
    # `command` string is still used as the rule-matching subject so that rule
    # names like "git status" keep working unchanged.
    if parts and sys.platform.startswith("win"):
        exec_command = subprocess.list2cmdline(parts)
    else:
        exec_command = command
    subject = args.subject if args.subject is not None else command

    if args.probe:
        matched = matching_rules(rules, subject)
        print(json.dumps({
            "subject": subject,
            "matched": [{"name": r.get("name"), "layer": r.get("_layer"),
                         "strategies": [s.get("type") for s in r.get("strategies", [])]}
                        for r in matched],
        }, indent=2))
        return 0

    # ---- gather input text + (for -- mode) the command's exit code ----
    rc = 0
    if args.stdin or not command:
        try:
            original = sys.stdin.read()
        except Exception:
            original = ""
    else:
        original, rc = run_capture(exec_command, timeout=args.timeout)

    # ---- kill switch / raw: pass-through, no compression ----
    if os.environ.get("TOKENJUICE_DISABLE") == "1" or args.raw:
        sys.stdout.write(original)
        sys.stdout.flush()
        return 0 if rc is None else rc

    compressed, trace = compress(original, rules, subject)
    if args.condense:
        before = len(compressed)
        compressed = s_condense(compressed, {"content_type": "auto"})
        trace.append({"rule": "--condense", "strategy": "condense",
                      "chars_before": before, "chars_after": len(compressed)})
    sys.stdout.write(compressed)
    if compressed and not compressed.endswith("\n"):
        sys.stdout.write("\n")
    sys.stdout.flush()

    stat = _stat(original, compressed)
    if args.json:
        payload = {"subject": subject, "stat": stat}
        if args.explain:
            payload["trace"] = trace
        sys.stderr.write(json.dumps(payload) + "\n")
        sys.stderr.flush()
    elif not args.quiet and stat["chars_in"]:
        _emit_err("saved %.1f%% (%d -> %d chars, ~%d -> ~%d tokens)" % (
            stat["pct_saved"], stat["chars_in"], stat["chars_out"],
            stat["tokens_in"], stat["tokens_out"]), False)

    return 0 if rc is None else rc


if __name__ == "__main__":
    sys.exit(main())
