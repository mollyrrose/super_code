---
type: tool
title: claude-mem — cross-session memory plugin for Claude Code
description: Adds persistent cross-session memory to Claude Code by capturing tool observations, AI-compressing them, and reinjecting relevant context in later sessions. Star count now corroborated across 4 independent trending views; activity signals look real.
tags: [claude-code, agent-memory, cross-session]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/thedotmack/claude-mem
status: current
supersedes: []
---

# Summary

claude-mem adds persistent cross-session memory to Claude Code and other
agents: it captures tool observations, compresses them with an AI pass, and
reinjects relevant context in later sessions. Single-command install
(`npx claude-mem install`), optional cloud sync, Apache-2.0. Now at ~3,894
commits, 79 PRs, 54 open issues, 9.8k forks, version badge 15.9.0. The
README promotes a paid "CMEM Pro" hosted tier and a third-party "CMEM"
token the maintainer has "officially embraced" — a commercial incentive to
note, not itself evidence of star manipulation.

# Repo / source check

Previously flagged `unverified` (2026-08-27) because a single fetch showed
~92.2k stars, which looked implausible. This sweep (2026-11-04) the repo
shows ~112.4k stars/9.8k forks *consistently* across 4 independent GitHub
Trending views (daily overall, weekly overall, weekly TypeScript, daily
TypeScript) rather than one anomalous reading — repeated independent
corroboration is itself evidence against the earlier "scraping artifact"
theory, matching this bundle's existing precedent for
[hermes-agent-nousresearch](/cognition/hermes-agent-nousresearch.md) (star
count upgraded from flagged to corroborated after a second independent
sweep). Combined with real activity signals (high commit/PR/issue counts,
Apache-2.0, multi-agent support), this is now recorded `status: current`.
No GitHub stargazer-timeline API access in this sandbox to directly confirm
growth history — if that ever becomes available, use it to close this gap
for good.

# Why this is in the radar

Directly overlaps this project's own level-5 memory layer design goal.
Unlike this project's typed-markdown + knowledge-graph approach, claude-mem
compresses raw tool-call observations rather than extracting structured
facts — a different point on the same "agent forgets between sessions"
design space, useful as a comparison, not a replacement.
