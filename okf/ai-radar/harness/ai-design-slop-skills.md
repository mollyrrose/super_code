---
type: tool
title: "Anti-AI-slop" design skills for coding agents — Nutlope/hallmark and pbakaus/impeccable
description: Two trending agent-skill packages that lint/polish/audit AI-generated UI for generic "AI slop" visual patterns; impeccable's live mode discloses a permission-check bypass worth flagging before adoption.
tags: [agent-skills, design, claude-code, codex, cursor, github-trending, unverified]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/Nutlope/hallmark
status: unverified
supersedes: []
---

# Summary

Two trending skill packages address the same complaint — AI-generated UI
looking generically "AI-slop" — from different angles:

- **Nutlope/hallmark** — "Anti-AI-slop design skill for Claude Code, Cursor,
  and Codex." Ships a `sloplint.mjs` linter, a `theme.mjs` theme picker, and
  a curated photo library; claims ~50 themes and ~755 photos (counts not
  independently verified from the fetch). MIT. ~47.4k stars, 2.5k forks,
  334 commits (~140 stars/commit).
- **pbakaus/impeccable** — "The design vocabulary for your coding agent."
  Rule-based "slop detector" CLI plus `polish`/`critique`/`audit` commands,
  a Rust engine, and browser/VS Code extensions, claiming support across
  ~20 agent tools. Apache-2.0. ~102k stars, 6k forks, 2,624 commits
  (~39 stars/commit).

# Repo / source check — unverified

Both repos' file layout matches their README claims (real directories,
tests, CI config), so these are not empty wrapper repos. Neither page
exposed a last-commit/release date, so freshness is unconfirmed. Star-to-
commit ratios (140:1 and 39:1) are elevated but far less extreme than the
already-tracked
[trending-skillpack-star-inflation-pattern](/agent-tooling/trending-skillpack-star-inflation-pattern.md)
cluster (which saw 300-1,100:1) — plausibly real organic interest rather
than the same inflation pattern, but not confirmed either way this pass.

**Safety-relevant disclosure (impeccable):** its own README states that
"live mode" can invoke the `codex` or `claude` CLI with permission checks
disabled, and that its installed hooks run even when the model's own
commands are denied; it also sends anonymous telemetry about design-
direction choices. This is disclosed, not hidden, but it is a real
run-with-reduced-guardrails mode — worth reading the live-mode docs in full
before enabling it in any session with real credentials or production
access, not just skimming the install instructions.

Per this bundle's conservative-verification rule (no skillspector scanner
available in this sandbox), both entries are marked `unverified` rather than
recommended, pending a closer look at impeccable's live-mode implementation
and both projects' actual commit recency.

# Why this is in the radar

A second, independent project converging on the same "AI-generated UI looks
generic" problem as `hallmark` suggests this is a real, broadly-felt pain
point in agent-driven frontend work, not a one-off. Recorded as awareness,
not a recommendation, until the live-mode safety trade-off (impeccable) and
both projects' maintenance recency are independently confirmed.
