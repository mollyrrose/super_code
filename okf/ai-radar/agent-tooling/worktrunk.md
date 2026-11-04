---
type: tool
title: worktrunk
description: Git worktree manager built explicitly for running multiple coding-agent sessions (Claude Code, Codex) in parallel on one repo.
tags: [git, worktree, agents, parallel-workflows, rust]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/max-sixty/worktrunk
status: current
supersedes: []
---

# Summary

`worktrunk` (`wt`) wraps `git worktree` with branch-name-mapped shortcuts
(`wt switch`, `wt list`, `wt merge`, `wt remove`), hooks, LLM-generated
commit messages/summaries, PR checkout, and shared build caches across
worktrees. Ships a first-class agent integration: `wt switch -x claude -c
feature-a -- 'Add user authentication'` launches an agent directly inside a
fresh worktree. ~10.8k stars, 396 forks, 41 open issues, 5,485 commits.
MIT OR Apache-2.0.

# Repo / source check

Real engineering signals: CI badge, Codecov, docs site, CHANGELOG, test
suite, benchmarks, and packaging via Homebrew/Cargo/winget/pacman/
conda-forge, plus signed releases (SignPath.io). The "most popular git
worktree manager" claim in its own banner is self-description, not
independently verified — treat as marketing, not a fact to cite elsewhere.
The parallel-agent-workflow framing is backed by real, documented commands
(not just a tagline), including dedicated Claude Code/Codex topic pages.

# Why this is in the radar

This project's own CLAUDE.md already documents a manual
`.worktrees/<branch>/`-based dual-window workflow for multi-window safety
(see "Multi-window safety and project boundaries" / `worktree_lifecycle.py`
in this repo's `scripts/`). `worktrunk` is a more polished, maintained,
third-party tool doing the adjacent job (worktree lifecycle + agent launch
convenience) rather than conflict/merge-safety classification, which this
project's own `worktree_lifecycle.py` already covers and `worktrunk` does
not attempt. Complementary, not competing — worth a look as a quality-of-
life layer on top of the existing worktree convention, not a replacement
for the conflict-prediction tooling.

# Notes

- No last-commit date surfaced via WebFetch; re-verify activity recency
  next scan.
