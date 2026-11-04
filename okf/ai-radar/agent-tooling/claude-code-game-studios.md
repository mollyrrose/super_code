---
type: tool
title: Claude Code Game Studios
description: Template pack turning Claude Code into a game-dev "studio" (49 agents, 74 skills, engine-specific Godot/Unity/Unreal sets); real and functional, but its star count fits a flagged inflation pattern.
tags: [claude-code, game-dev, skills, agents, unverified-popularity]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/Donchitos/Claude-Code-Game-Studios
status: unverified
supersedes: []
---

# Summary

A Claude Code template providing 49 agent definitions in a three-tier studio
hierarchy, 74 slash-command skills (About text says 72 — the two disagree),
15 hooks, 14 path-scoped rules, 62 document templates, and engine-specific
agent sets for Godot/Unity/Unreal. MIT license. ~35.2k stars, 4.6k forks,
238 watchers, 43 commits on `main`, 48 open issues.

# Repo / source check

The code itself looks real: changelog, upgrade guide, contributing and
security-policy files, a `studio-tests/` directory, documented 7-phase
workflow, GitHub Discussions. The agent/skill-count claims are largely
corroborated by the README's own command list. However star count against
commit depth (~819 stars/commit) is a stronger mismatch than either
`obra/superpowers` or `mattpocock/skills` in this bundle's existing
`agent-tooling/trending-skillpack-star-inflation-pattern.md` entry, which
this repo has now been added to. Fork ratio (~13%) and modest watcher count
look template-shaped rather than obviously bot-inflated, but this sweep
cannot independently confirm the star trajectory (no star-history API pull
available). Marked `unverified` on popularity grounds, not on
functionality/safety grounds — the template itself appears legitimate.

# Why this is in the radar

A genuinely novel, specific application of the "many Claude Code skills"
pattern (game studio roles) rather than a generic skill pack; worth
awareness for anyone doing game-dev-with-Claude-Code work, but do not cite
its star count as a popularity signal without independent verification.

# Notes

- Cross-linked with
  [trending-skillpack-star-inflation-pattern](/agent-tooling/trending-skillpack-star-inflation-pattern.md).
- Re-verify the 74-vs-72 skill-count discrepancy and star trajectory next
  scan.
