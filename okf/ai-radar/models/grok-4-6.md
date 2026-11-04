---
type: model
title: Grok 4.6 (xAI)
description: xAI's mid-cycle Grok update for long-running agentic/coding/research work; 500K context, tiered long-context pricing. First xAI entry in this bundle.
tags: [xai, grok, pricing, context-window, release]
timestamp: 2026-11-04T00:00:00Z
resource: https://x.ai/api
status: current
supersedes: []
---

# Summary

Launched 2026-08-12 (model id `grok-4.6`), just before this sweep's window
but previously untracked. 500,000-token context window, aimed at
long-running agentic tasks, coding, research, and interactive/visual work.
Standard pricing $2.00/M input, $0.50/M cached input, $6.00/M output for
prompts under 200K tokens; past 200K tokens the *entire* request bills at
long-context rates ($4.00/M input, $1.00/M cached input, $12.00/M output) —
the same whole-request-repriced-past-threshold pattern
[gpt-6-astra](/models/gpt-6-astra.md) uses at its own threshold. Grok 4.7
(rumored ~2.1T params, up from 4.6's ~1.5T) is expected mid-September 2026
per Musk's public comments but has not shipped as of this sweep.

# Repo / source check

Closed-source, no repo. xAI's own API docs were not directly fetched this
pass; figures come from multiple aggregator/explainer sites (kingy.ai,
layer3labs.io, mem0.ai, benchlm.ai, codersera.com) that agree closely on
context window and the two-tier pricing structure. Recommend an official-source
check before treating pricing as final.

# Why this is in the radar

xAI/Grok was entirely untracked in this bundle — closing that gap now,
especially since the shared-pricing-pattern with GPT-6 Astra is worth
watching as a possible industry norm forming this cycle.

# Notes

- Grok 4.7 is rumor-only; do not treat as released until confirmed.
- **2026-11-04 re-check:** still rumor-only. Musk reportedly said (early
  August 2026, per a single third-party site) Grok 4.7 would follow "3-4
  weeks later" and Grok 5 "before year-end" — neither found shipped as of
  this scan; xAI's own docs still list 4.6 as latest per the sources
  checked. This entry stays `current` pending an actual release.
