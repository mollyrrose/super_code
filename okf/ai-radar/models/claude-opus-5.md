---
type: model
title: Claude Opus 5
description: Anthropic's former flagship model; superseded by Opus 5.5 (2026-09-22).
tags: [anthropic, claude, opus, flagship, superseded]
timestamp: 2026-11-04T00:00:00Z
resource: https://www.anthropic.com/news/claude-opus-5
status: superseded
supersedes: [models/claude-opus-4-8]
---

# Summary

Claude Opus 5 (model id `claude-opus-5`, 1M-context variant `claude-opus-5[1m]`)
launched 2026-07-24 as Anthropic's new flagship, with a minor update on
2026-08-12 improving inference speed and scientific-research performance.
1M token context, 128K max output. Pricing unchanged from Opus 4.8 at
$5/$25 per MTok (input/output). Adds a low/medium/high/xhigh/max thinking-effort
toggle for cost-vs-capability control. Positioned as approaching Fable 5
frontier intelligence at roughly half the price, and billed as Anthropic's
"most aligned" Opus model to date.

# Why this is in the radar

This is the top of the current haiku < sonnet < opus ladder and supersedes
`models/claude-opus-4-8` (previously the tracked flagship). Any local config
or CLAUDE.md that pins `claude-opus-4-8` or `claude-opus-4-7` should be
flagged to consider `claude-opus-5` instead — this drives the `supersedes`
"speak up" mechanic at the `/qRem`/`/qRev` gates.

# Repo / source check

Closed-source model, no GitHub repo to inspect. Grounding: official
Anthropic announcement (`resource`), cross-checked via independent WebSearch
against MarkTechPost, TechCrunch, and Fortune coverage of the 2026-07-24
launch (direct fetch of anthropic.com/docs.anthropic.com was blocked by this
sandbox's egress proxy, so this relies on search-aggregated corroboration
from multiple independent outlets rather than a single primary fetch).

# Notes

- **Superseded 2026-11-04 scan:** Opus 5 was superseded 2026-09-22 by
  [Claude Opus 5.5](/models/claude-opus-5-5.md) — see that entry for the
  current flagship. This entry is kept as a superseded marker per the
  bundle's `supersedes` -> "speak up" mechanic.
