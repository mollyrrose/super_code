---
type: model
title: Claude Sonnet 5
description: Anthropic's former mid-tier model; superseded by Sonnet 5.5 (2026-09-28).
tags: [anthropic, claude, sonnet, mid-tier, superseded]
timestamp: 2026-11-04T00:00:00Z
resource: https://www.anthropic.com/news/claude-sonnet-5
status: superseded
supersedes: []
---

# Summary

Claude Sonnet 5 (model id `claude-sonnet-5`) launched 2026-06-30. 1M token
context, 128K max output, adaptive thinking on by default. Launch pricing of
$2/$10 per MTok (input/output) was introductory through 2026-08-31; on
2026-08-10 Anthropic announced it will NOT proceed with the planned hike to
$3/$15 on 2026-09-01, making $2/$10 the permanent rate. Performance approaches
Opus 4.8 at a fraction of the cost, aimed at cheaper agentic workloads.

# Why this is in the radar

This session itself runs on `claude-sonnet-5` (per the environment's model
identity). No existing bundle entry tracked the Sonnet line before this scan;
recorded here as a new current entry rather than a supersession, since the
bundle had no prior `models/claude-sonnet-4-*` entry to supersede.

# Repo / source check

Closed-source model, no GitHub repo to inspect. Grounding: official Anthropic
announcement (`resource`), cross-checked via independent WebSearch against
TechCrunch, Qz, BigGo Finance, and explainx.ai coverage of both the
2026-06-30 launch and the 2026-08-10 permanent-pricing announcement (direct
fetch of anthropic.com/docs.anthropic.com was blocked by this sandbox's
egress proxy).

# Notes

- **Superseded 2026-11-04 scan:** Sonnet 5 was superseded 2026-09-28 by
  [Claude Sonnet 5.5](/models/claude-sonnet-5-5.md) — see that entry for the
  current mid-tier model. This entry is kept as a superseded marker per the
  bundle's `supersedes` -> "speak up" mechanic. Note: this session itself
  (and this project's CLAUDE.md model-identity references) are configured
  for `claude-sonnet-5`, one tier behind this radar's own current pick —
  recorded here, not auto-actioned, since a model-pin change is a deliberate
  decision for the user, not something this scan should do unprompted.
