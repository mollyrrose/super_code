---
type: tool
title: NVIDIA SkillSpector — official open-source agent-skill scanner
description: NVIDIA's open-source static (+ optional LLM) scanner for AI agent skills (Claude Code, Codex, MCP) — prompt injection, exfiltration, supply-chain risk, malicious code. Runs as CLI or MCP server. Directly relevant to this project's own "skillspector" scan-before-trust rule.
tags: [devsec, agent-skills, scanner, mcp, nvidia, supply-chain, prompt-injection]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/NVIDIA/skillspector
status: current
supersedes: []
adoption: awareness-candidate
---

# Summary

SkillSpector is NVIDIA's open-source security scanner for AI agent skills.
It statically analyzes a skill (git repo, URL, zip, directory, or single
file) for prompt injection, data exfiltration, supply-chain risk, and
malicious code *before* the skill is installed or run — it does not execute
the skill under test. Two-stage pipeline: fast static analysis (AST dangerous-
code detection, taint tracking, YARA signatures, MCP least-privilege /
tool-poisoning checks) plus an optional LLM semantic-review stage. Output as
terminal, JSON, Markdown, or SARIF.

Introduced as part of the NVIDIA-Verified Agent Skills program (~May 2026,
broader public coverage from 2026-08-03 onward, e.g. Help Net Security).
SkillSpector is the scanner stage of that pipeline: skills that pass are
listed in NVIDIA's own skill catalog. Apache-2.0, 24.3k stars / 2.1k forks /
81 watchers, 1,819 commits — an active, substantial project, though the repo
page does not surface a dated last-commit or release timestamp.

Install: `uv tool install git+https://github.com/NVIDIA/skillspector.git`
(add the `[mcp]` extra for the MCP server). CLI: `skillspector scan <path>`.
MCP server: `skillspector mcp` (stdio by default; HTTP transport exists but
the README warns it ships with **no authentication** — do not expose it
beyond loopback). README claims 71 vulnerability patterns across 17
categories (the per-category tables in the README actually list 73 rows —
an internal inconsistency, not independently reconciled here) and cites a
self-reported "26.1% of scanned skills contain vulnerabilities" figure from
the authors' own dataset, not an independent audit. Limitations section
self-discloses: no runtime/dynamic analysis, may miss non-English content,
text embedded in images, and encrypted/compiled payloads.

# Repo / source check

Inspected the real repo (README, license, star/fork/commit counts, install
paths) rather than only the announcement coverage. Apache-2.0 license, large
and apparently active (1,819 commits), official NVIDIA org account. The
code backs the marketing claim as far as this check goes (real static-
analysis engine with named detection techniques, not just a wrapper around
an LLM prompt), but the exact pattern-count claim (71 vs. 73) is internally
inconsistent and the "26.1% vulnerable" figure is self-reported, so treat
both as directional rather than verified. No independent third-party audit
of SkillSpector itself was found in this pass. `status: current` reflects
"this looks like a real, maintained, vendor-backed tool worth tracking," not
a verified safety guarantee for skills it clears.

# Why this is in the radar

This project's own `~/.claude/CLAUDE.md` and this repo's `CLAUDE.md` /
ai-radar entries repeatedly reference a standing "skillspector-gate" /
"scan GitHub code before trusting it" rule and a `~/.claude/.skillspector_log.jsonl`
audit trail (see `okf/ai-radar/README.md`'s "Always inspect the real GitHub
repo" section and prior sweeps' notes that "no skillspector available in
this sandbox"). This GitHub repo, `NVIDIA/skillspector`, matches that name
and purpose closely: a scanner specifically for AI *agent skills* (not
generic code), checking for the same threat classes (prompt injection,
exfiltration, supply-chain risk) this project's own scan-before-trust rule
targets.

**This is likely the real-world tool that rule has been informally
invoking by name** — or, at minimum, the first verifiable, officially-
released, open-source implementation of that exact concept. It was not
previously catalogued in this bundle (should have been caught in the
2026-09-08 sweep or earlier, given its ~2026-05 origin; this is a genuine
coverage gap from the ~57-day gap between sweeps). Flagging for the user:
worth confirming by hand whether `~/.claude/.skillspector_log.jsonl` /
existing `skillspector scan "<git-url>"` invocations in this project's docs
already refer to this exact package (same CLI surface: `skillspector scan
<path>`) — if so, it can likely now be installed for real in sandboxes that
currently lack it (this cloud session included: "You do NOT have
skillspector in this sandbox" was explicitly called out in this sweep's own
instructions). Not independently confirmed as installed/working here this
pass — recommend a follow-up manual check rather than assuming.

# Notes

- MCP HTTP transport ships with no auth — if ever run as an MCP server in
  this project's stack, keep it stdio-only or loopback-bound.
- Re-verify the 71-vs-73 pattern-count discrepancy and look for a dated
  release/changelog at the next scan.
