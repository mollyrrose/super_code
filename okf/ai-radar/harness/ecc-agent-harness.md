---
type: tool
title: affaan-m/ECC — agent-harness performance-optimization stack
description: Performance-optimization plugin stack (68 agents/286 skills/94 commands) for Claude Code, Codex, Cursor — already installed and partially hook-disabled in this project for performance reasons.
tags: [claude-code, agent-harness, skills, mcp, github-trending, unverified]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/affaan-m/ECC
status: unverified
supersedes: []
---

# Summary

Surfaced via GitHub trending on both the daily (#4) and weekly (#2, largest
gain of the sweep at +7,735) overall boards. README cites a v2.1 refresh
adding a "Plan Canvas" browser-based plan reviewer, Kimi-harness support,
and self-hosted GPU integration ("Itô") as recent drivers. MIT license,
2,667 commits.

# Repo / source check — unverified

254k stars / 38k forks is disproportionate to the repo's commit depth/age —
part of the same stars-vs-commits mismatch pattern flagged in
[trending-skillpack-star-inflation-pattern](/agent-tooling/trending-skillpack-star-inflation-pattern.md).
Star/growth numbers are marked `unverified` accordingly. However, the
plugin's *functionality* is independently corroborated: this project's own
CLAUDE.md documents having the ECC plugin installed with several of its
hooks (`pre:observe`, `stop:check-console-log`, etc.) explicitly disabled
via `ECC_DISABLED_HOOKS` after they caused spawn timeouts and Stop-hook
errors under load — i.e. this is a real, in-the-wild tool actually running
in this environment, not vaporware, even though its growth metrics are
unconfirmed.

# Why this is in the radar

Already a live dependency of this repo (see the project CLAUDE.md's "ECC
plugin hooks disabled on this setup" section) — tracking its upstream
releases matters directly for whether the local hook-trimming workaround
needs re-applying after a plugin-cache update.

# Update (2026-11-04 scan)

Current release is **v2.2.3 (2026-10-01)**: confirmed directly from the repo
page. The three v2.1-era claims are now verified rather than cited
secondhand — "Plan Canvas browser review" is a real v2.2 "What's New" item;
Kimi-harness support is real (`--target kimi`, project-local `.kimi-code/`
files, verified against Kimi Code 0.31.x, no hooks configured by the Kimi
adapter); "Itô" GPU integration is narrower than "self-hosted GPU
integration" implied last scan — it's a GPU-compute *sponsor* with an
`ecc ito` CLI bridge to a separately-installed client; `find` only submits a
live RFQ (does not reserve capacity), managed inference through Itô is "not
live yet," and the `ito-compute-cli` package is unpublished. New since last
scan (v2.2 line): guided manifest-driven setup for Claude Code/Codex/Kimi
Code with doctor/repair/uninstall, native Antigravity install, a Pi adapter,
and a unified `ecc memory` vault.

Star count has grown 254k -> ~296.8k (43.9k forks, 4,321 commits) over the
~57 days since last scan — continued fast growth, still disproportionate to
commit depth, still part of the same pattern tracked in
[trending-skillpack-star-inflation-pattern](/agent-tooling/trending-skillpack-star-inflation-pattern.md)
(flagged there for that entry's own next refresh: two of its repos,
`obra/superpowers` and `mattpocock/skills`, now show near-identical star
counts of ~312.1k each, which reads less like organic virality and more
like a shared trending-page artifact or coordinated inflation — worth
checking via the GitHub API's `/stargazers` rather than trending-page
summaries next time agent-tooling is swept). Status stays `unverified` on
growth; functionality remains independently corroborated as real.
