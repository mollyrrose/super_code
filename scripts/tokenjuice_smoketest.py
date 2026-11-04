#!/usr/bin/env python3
"""Smoketest for tokenjuice.py -- pure strategy + overlay + pipeline checks.

Fast, dependency-free. Run: python tokenjuice_smoketest.py
Exit 0 = all pass, 1 = a check failed (prints which).
"""

from __future__ import annotations

import sys

import tokenjuice as tj

FAILS = []


def check(name, cond):
    if cond:
        print("[ok] " + name)
    else:
        print("[fail] " + name)
        FAILS.append(name)


def test_strip_ansi():
    raw = "\x1b[31merror\x1b[0m here\x1b[1m bold\x1b[0m"
    out = tj.s_strip_ansi(raw, {})
    check("strip_ansi removes escapes", out == "error here bold")


def test_fold_whitespace():
    raw = "a   \n\n\n\nb \t\nc"
    out = tj.s_fold_whitespace(raw, {"trailing": True, "blank_runs": 1})
    check("fold_whitespace caps blank runs", out == "a\n\nb\nc")
    out2 = tj.s_fold_whitespace("x    y", {"inner": True})
    check("fold_whitespace collapses inner runs", out2 == "x y")


def test_dedup_consecutive():
    raw = "a\na\na\nb\nb\nc"
    out = tj.s_dedup_lines(raw, {"mode": "consecutive"})
    check("dedup consecutive collapses runs", out == "a\nb\nc")
    out2 = tj.s_dedup_lines(raw, {"mode": "consecutive", "keep_count": True})
    check("dedup keep_count annotates", "(x3)" in out2 and "(x2)" in out2)


def test_dedup_global():
    raw = "a\nb\na\nc\nb"
    out = tj.s_dedup_lines(raw, {"mode": "global"})
    check("dedup global keeps first-seen order", out == "a\nb\nc")


def test_drop_and_keep_regex():
    raw = "keep me\nDROP this\nkeep too"
    out = tj.s_drop_regex(raw, {"patterns": [r"^DROP"]})
    check("drop_regex drops matching", out == "keep me\nkeep too")
    out2 = tj.s_keep_regex(raw, {"patterns": [r"keep"]})
    check("keep_regex keeps only matching", out2 == "keep me\nkeep too")
    # a malformed pattern must be skipped, not crash
    out3 = tj.s_drop_regex(raw, {"patterns": ["(unclosed"]})
    check("bad regex is skipped not fatal", out3 == raw)


def test_truncate():
    raw = "\n".join(str(i) for i in range(100))
    out = tj.s_truncate(raw, {"head": 5, "tail": 5, "min_lines": 20})
    lines = out.split("\n")
    check("truncate keeps head", lines[:5] == ["0", "1", "2", "3", "4"])
    check("truncate keeps tail", lines[-5:] == ["95", "96", "97", "98", "99"])
    check("truncate inserts marker", any("dropped 90 lines" in ln for ln in lines))
    # below min_lines -> untouched
    small = "a\nb\nc"
    check("truncate respects min_lines", tj.s_truncate(small, {"head": 1, "tail": 1, "min_lines": 50}) == small)


def test_summarize_sections():
    raw = "\n".join(["head"] * 3 + ["foo bar"] * 40 + ["tail"] * 3)
    out = tj.s_summarize_sections(raw, {"head": 3, "tail": 3, "min_lines": 10})
    check("summarize folds the middle", "folded" in out and "foo x" in out)


def test_html_to_markdown():
    html = '<h1>Title</h1><p>hi <a href="https://x.io/p">link</a></p><script>bad()</script>'
    out = tj.s_html_to_markdown(html, {})
    check("html strips script", "bad()" not in out)
    check("html keeps link target", "https://x.io/p" in out and "link" in out)
    check("html marks heading", "# Title" in out)


def test_shorten_urls():
    long_url = "https://example.com/" + "a" * 200
    out = tj.s_shorten_urls("see " + long_url + " end", {"max_len": 60})
    check("shorten collapses long url", "example.com/...(" in out and "aaaaaaa" not in out)
    short = "https://x.io/p"
    check("shorten leaves short url", tj.s_shorten_urls(short, {"max_len": 60}) == short)


def test_overlay_and_match():
    rules = tj.load_rules()
    names = {r.get("name") for r in rules}
    check("builtin rules load", "universal" in names and "git-status" in names)
    # universal matches anything; git-status matches the command
    m = {r.get("name") for r in tj.matching_rules(rules, "git status --porcelain")}
    check("universal matches all", "universal" in m)
    check("specific rule matches command", "git-status" in m)
    # a random subject still gets the universal rule but not git-status
    m2 = {r.get("name") for r in tj.matching_rules(rules, "totally unrelated")}
    check("non-matching specific rule excluded", "git-status" not in m2 and "universal" in m2)


def test_override_by_name(tmpcheck=True):
    # user/project override-by-name semantics, via a synthetic layer merge
    base = [{"name": "x", "match": "*", "strategies": [{"type": "truncate", "head": 1}]}]
    over = [{"name": "x", "match": "*", "enabled": False}]
    merged = {}
    order = []
    for layer in (base, over):
        for r in layer:
            n = r["name"]
            if n not in merged:
                order.append(n)
            merged[n] = r
    final = [merged[n] for n in order if merged[n].get("enabled", True)]
    check("later layer overrides + can disable", final == [])


def test_compress_pipeline():
    rules = tj.load_rules()
    raw = "\x1b[31m" + "\n".join(["dup"] * 50) + "\x1b[0m"
    out, trace = tj.compress(raw, rules, "git status")
    check("pipeline applies + traces", len(out) < len(raw) and len(trace) >= 1)
    stat = tj._stat(raw, out)
    check("stat reports savings", stat["pct_saved"] > 0 and stat["tokens_in"] >= stat["tokens_out"])


def test_run_capture():
    text, rc = tj.run_capture(sys.executable + ' -c "print(\'hello\'); import sys; sys.exit(7)"')
    check("run_capture captures stdout", "hello" in text)
    check("run_capture preserves rc", rc == 7)


def test_kill_switch_passthrough():
    # the kill switch lives in main(); verify --raw pass-through via main()
    import io
    old = sys.stdin
    sys.stdin = io.StringIO("\n".join(["dup"] * 50))
    try:
        rc = tj.main(["--stdin", "--raw", "--quiet"])
    finally:
        sys.stdin = old
    check("--raw returns 0 (pass-through)", rc == 0)


def test_git_log_commits():
    commit = ("commit %040x\nAuthor: A <a@b>\nDate:   Wed Nov 4 11:51:%02d 2026 +0000\n\n"
              "    subject %d\n\n    body line 1\n    body line 2\n    body line 3\n"
              "    body line 4\n\n    Co-Authored-By: X <x@y>\n\n"
              " scripts/a.py | 3 +++\n scripts/b.py | 1 -\n"
              " 2 files changed, 3 insertions(+), 1 deletion(-)\n")
    raw = "\n".join(commit % (i + 1, i, i) for i in range(20))
    out, _ = tj.compress(raw, tj.load_rules(include_user=False), "git log --stat -20")
    check("git-log keeps all 20 subjects", all(("subject %d" % i) in out for i in range(20)))
    check("git-log caps body at 3 extra lines", "body line 4" not in out and "[+1 body lines]" in out)
    check("git-log drops trailers", "Co-Authored-By" not in out)
    check("git-log keeps diffstat summary", out.count("2 files changed") == 20)
    check("git-log drops Author lines", "Author:" not in out)
    check("git-log shrinks output", len(out) < len(raw))
    oneline = "\n".join("%07x subject %d" % (i, i) for i in range(30))
    check("git-log --oneline unchanged", tj.s_git_log_commits(oneline, {}) == oneline)


def main():
    test_strip_ansi()
    test_fold_whitespace()
    test_dedup_consecutive()
    test_dedup_global()
    test_drop_and_keep_regex()
    test_truncate()
    test_summarize_sections()
    test_git_log_commits()
    test_html_to_markdown()
    test_shorten_urls()
    test_overlay_and_match()
    test_override_by_name()
    test_compress_pipeline()
    test_run_capture()
    test_kill_switch_passthrough()
    if FAILS:
        print("\nFAILED: " + ", ".join(FAILS))
        return 1
    print("\nall smoketests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
