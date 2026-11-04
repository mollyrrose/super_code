---
type: model
title: Claude Fable 5.1 and Claude Mythos 5.1
description: Anthropic's efficiency refresh of its Fable/Mythos frontier-agentic line — a 75% cache-read price cut at unchanged headline pricing.
tags: [anthropic, claude, fable, mythos, pricing, context-window, release]
timestamp: 2026-11-04T00:00:00Z
resource: https://platform.claude.com/docs/en/models/fable-5-1/whats-new-fable-5-1
status: current
supersedes: []
---

# Summary

Shipped 2026-09-01. Fable 5.1 and Mythos 5.1 keep the 1M-token context
window and $10/M input / $50/M output pricing of Fable 5 / Mythos 5, but cut
prompt-cache reads from $1.00/M to $0.25/M (75% cheaper) and improve
cache-write efficiency — roughly 25% lower cost for typical token-billed
work, up to ~45% lower for agentic workloads. No new headline capability
claim; framed purely as a cost/efficiency update (MarkTechPost cites a
52.6% Terminal-Bench-Science score). Mythos 5.1 stays gated to vetted
"Project Glasswing" customers (cybersecurity/life-sciences research) and
lacks Fable's safety-classifier refusal behavior; Fable is generally
available via the Claude API, Bedrock, Vertex AI, and Microsoft Foundry.

Fable/Mythos is **not** a rename or rival of the Opus line: the bundle's
existing [claude-opus-5](/models/claude-opus-5.md) entry already noted
Opus 5 is "positioned as approaching Fable 5 frontier intelligence at
roughly half the price" — Fable/Mythos is Anthropic's separate, pricier,
long-horizon/agentic-research tier sitting above the standard Opus flagship,
not a lineage that competes with or supersedes it. This is simply the first
bundle entry to track that line directly.

# Repo / source check

Closed-source, no repo. `anthropic.com`'s marketing page was blocked by this
sandbox's egress proxy; verified instead via the official
`platform.claude.com` docs page (fetched directly), cross-checked against
VentureBeat, MarkTechPost, DataCamp, and llm-stats.com, which all agree on
the 75% cache-read cut and 2026-09-01 date.

# Why this is in the radar

First tracked entry for the Fable/Mythos line, which the bundle had
previously only referenced in passing from the Opus 5 entry. Establishes a
baseline for future Fable/Mythos scans.

**2026-11-04 re-check:** not independently re-verified this pass beyond a
cross-reference from the new [claude-opus-5-5](/models/claude-opus-5-5.md)
entry, whose own announcement claims Opus 5.5 "performs at the level of
Claude Fable 5.1 on most work" — consistent with, not contradicting, this
entry. No newer Fable/Mythos release found. Timestamp refreshed; do a full
re-verification at the next scan.
