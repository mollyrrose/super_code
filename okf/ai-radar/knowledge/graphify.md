---
type: tool
title: Graphify (Graphify-Labs) -- codebase-to-knowledge-graph tool for coding agents
description: GitHub-trending tool that turns a codebase/docs/PDFs into a queryable knowledge graph for Claude Code et al.; same project as this repo's own graphifyy PyPI dependency, but its claimed star count does not hold up to scrutiny.
tags: [knowledge-graph, codebase, claude-code, tree-sitter, github-trending, star-count-caution, unverified]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/Graphify-Labs/graphify
status: unverified
supersedes: []
---

# Summary

Graphify (org: Graphify-Labs, YC S26) is an open-source tool that parses a
codebase locally with tree-sitter (no LLM needed for code) and optionally
runs a semantic pass over docs/PDFs/media, storing calls, imports,
definitions and references as typed edges in a queryable graph. For Claude
Code it installs a PreToolUse hook that nudges the agent toward graph
queries instead of grep-style search; `/graphify .` builds an interactive
graph, a markdown report, and a JSON file. Also integrates with Cursor,
Codex, and Gemini CLI. License: dual Apache-2.0/MIT. Surfaced via GitHub
trending this week with a claimed star count in the ~142k range.

# Relationship to this repo's own `graphifyy` dependency -- SAME PROJECT

This project's CLAUDE.md documents a "Level-5 memory layer" running on the
PyPI package `graphifyy` (0.8.x at the time it was audited, 2026-07-31).
Checked directly: the `graphifyy` PyPI project page
(pypi.org/project/graphifyy/) lists its Homepage as `https://graphify.com`
and its Source as `https://github.com/Graphify-Labs/graphify` -- the exact
repo being evaluated here. So this is confirmed to be **the same project**,
not a fork and not an unrelated same-named competitor: `graphifyy` is the
PyPI distribution name for `Graphify-Labs/graphify`. The PyPI page's listed
description ("turn any folder of code, docs, papers, images, or videos into
a queryable knowledge graph") matches the GitHub README's claim verbatim in
substance.

Supply-chain note: PyPI's latest `graphifyy` release is **0.9.102**, dated
2026-11-03 (yesterday relative to this scan) -- a jump from the 0.8.x line
audited in July to over a hundred 0.9.x point releases in roughly three
months. That release velocity is unusually high and means the manually
audited 0.8.x snapshot is well behind current `main`. This does not by
itself prove anything is wrong, but it does mean the 2026-07-31 audit should
not be treated as covering the code actually installed today -- worth a
re-audit before the next graphifyy version bump, not something this entry
can resolve on its own.

# Repo / source check -- unverified, caution on the star count

Via direct WebFetch of the GitHub repo page: 142.1k stars, Apache-2.0/MIT,
2,831 commits visible, 711 open issues, 898 open pull requests -- but the
page did not surface a last-commit date or any release/tag date on this
fetch, which is unusual for an active repo and could not be independently
confirmed (this sandbox has no authenticated GitHub API access to this repo
to pull `pushed_at`/`releases` directly; `add_repo` was not used since this
is read-only research on someone else's public repo, not work on this
project's own repos).

Several independent signals point to the claimed star count being inflated
relative to real usage/activity, consistent with this bundle's standing
caution about GitHub-trending star inflation on AI tool repos:

- Secondary sources disagree sharply on the count depending on when they were
  written: ~40k stars (May), ~58k (mid-May), ~73k (July), ~88k-90k (per two
  different "today" snapshots), and the 142k figure surfaced via this week's
  trending page. A roughly 3.5x jump from ~40k to 142k in six months is not
  impossible for a hyped AI tool, but it is a steep enough curve to warrant
  caution rather than acceptance at face value.
- A user complaint surfaced in search results (via a dev.to review quoting
  Reddit): "58,000 Stars, a YC Backing, and a 0% Adoption Rate with Claude"
  -- i.e. a real-world usefulness complaint sitting alongside a large star
  count, the classic mismatch pattern for star-count gaming.
- The surrounding web coverage is dominated by what reads as SEO-content-mill
  posts (dev.co, augmentcode.com/learn, enterprisedna.co, neura.market,
  everydev.ai, multiple near-identical "graphify review NNk star" dev.to
  posts) rather than independent technical writeups -- consistent with
  coordinated promotion, though this is circumstantial, not proof.
- Multiple same-named repos turned up in search (`safishamsi/graphify`,
  `Sirhan1/graphify`) alongside `Graphify-Labs/graphify` -- plausibly
  unrelated forks/clones/namesquats, not inspected further here, but adding
  to the overall confusion around what "Graphify" even refers to.

None of this proves malicious intent or a fake project -- the PyPI linkage to
a real, functioning package this repo's own tooling depends on is a point in
its favor -- but per this bundle's grounding rule, a claim (the ~142k star
count, and by extension "this is a trustworthy, battle-tested tool") that
cannot be verified from primary signals is marked `status: unverified` here
and is not recommended for further adoption beyond what is already running
locally as `graphifyy`.

# Why this is in the radar

Directly relevant to this project's own level-5 memory layer, which already
runs the PyPI side of this exact project. Also sits in the same
knowledge-graph-for-agent-knowledge cluster as
[gbrain](/knowledge/gbrain.md), [cognee](/knowledge/cognee.md), and
[graphiti-zep](/knowledge/graphiti-zep.md), but is differentiated by being
code-graph-first (tree-sitter AST over a codebase) rather than
markdown/ontology-first.

# Notes

- 2026-11-04 (local): `graphifyy` upgraded 0.9.31 -> **0.9.102** after a
  hand audit + SkillSpector triage (no exfil/RCE; HIGH hits were defensive
  code). The audit gap above is closed for 0.9.102.

- Re-verify the star count and release cadence at the next scan using an
  authenticated GitHub API pull if available (`pushed_at`, `releases`,
  `stargazers_count` history) rather than a scraped page render.
- If this project ever bumps past the audited 0.8.x `graphifyy` line, that
  bump should get its own fresh audit given the release velocity noted
  above -- flagged here for whoever runs that audit, not actioned by this
  entry.
