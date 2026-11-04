---
type: model
title: Claude Opus 5.5
description: Anthropic's current flagship — first model in the new Claude 5.5 family; supersedes Opus 5 at 20% lower pricing, claims near-Fable-5.1 performance.
tags: [anthropic, claude, opus, flagship, release]
timestamp: 2026-11-04T00:00:00Z
resource: https://www.anthropic.com/claude-opus-5-5
status: current
supersedes: [models/claude-opus-5]
---

# Summary

Claude Opus 5.5 (model id expected `claude-opus-5-5`) launched 2026-09-22 as
the first model in a new "Claude 5.5" family (Sonnet 5.5 and Haiku 5.5
flagged by Anthropic as following — not yet independently confirmed as
shipped at the time of this scan; see `models/claude-sonnet-5.md` and
re-check at the next scan).

Pricing: $4/M input, $20/M output, $0.20/M cache reads, $5/M cache writes —
roughly 20% below Opus 5 on input/output and 60% below on cache reads. A
"fast mode" (up to 2.5x speed) costs $8/M input, $40/M output. Anthropic
says it costs ~40% less than Opus 5 on typical workloads while scoring
higher on most of its own listed benchmarks, and that it "performs at the
level of Claude Fable 5.1 on most work" — Anthropic frames its own
Opus-vs-Fable gap as narrower than the raw benchmark table suggests. Output
is reported as 30%+ faster than Opus 5. Safety: best score on Anthropic's
automated behavioral audit, ~85% fewer attempts to circumvent containment
boundaries vs. Opus 5/Mythos 5.1, improved prompt-injection resistance.
Available on AWS, Google Cloud, and Azure in addition to the Claude API.

This session itself is configured for `claude-sonnet-5` with fallback to
`claude-opus-5-5[1m]` / `claude-opus-5[1m]` (see this session's own model
identity block) — so Opus 5.5 is not just an external data point, it is
already one of this setup's configured fallback models.

# Repo / source check

Closed-source model, no GitHub repo to inspect. Grounding: **directly
fetched** `anthropic.com/claude-opus-5-5` this pass (not proxy-blocked this
time, unlike several prior scans) — pricing and the Fable-5.1 comparison
come straight from the first-party announcement. Cross-checked via
WebSearch against Unite.AI, DataNorth.ai, and powerdrill.ai, which agree on
the 2026-09-22 date and pricing; one secondary source (emergent.sh) claimed
no Anthropic announcement existed as of 2026-09-22, which directly
contradicts the first-party page fetched here — treated as the outlier and
disregarded.

# Why this is in the radar

Directly supersedes `models/claude-opus-5` (previously tracked flagship,
now marked `superseded`). Also the first real-world confirmation that
Anthropic is closing the Opus/Fable gap from the Opus side rather than only
discounting Fable (contrast with `models/claude-fable-mythos-5-1`, which cut
cache-read cost without a capability claim).

# Notes

- **Resolved 2026-11-04 (same scan, later pass):** Sonnet 5.5 confirmed
  shipped 2026-09-28, see [claude-sonnet-5-5](/models/claude-sonnet-5-5.md)
  (now supersedes `claude-sonnet-5`). Haiku 5.5 followed ~2026-10-07, see
  [claude-haiku-5-5](/models/claude-haiku-5-5.md) (date unverified,
  secondary sources disagree).
- Context window and max-output figures were not stated on the announcement
  page fetched this pass; confirm against platform.claude.com model docs at
  the next scan.
