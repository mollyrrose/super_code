---
type: model
title: DeepSeek V4.1-Flash
description: DeepSeek's new default model after retiring V4-Pro — asymmetric MoE (8B active read / 16B active write), multimodal, ~1M context, MIT-licensed open weights.
tags: [deepseek, open-weight, pricing, context-window, release, multimodal]
timestamp: 2026-11-04T00:00:00Z
resource: https://thenextweb.com/news/deepseek-v4-1-flash-launch-v4-pro-retired-price-cut
status: unverified
supersedes: [models/deepseek-v4-pro]
---

# Summary

DeepSeek V4.1-Flash began limited internal beta 2026-09-08 and launched
publicly 2026-09-10, on a new "asymmetric" MoE architecture: 552B total
parameters, activating 8B for reading input and 16B for generating output.
Accepts image and text input (multimodal), ~1M-token context window.
Pricing reported as $0.15/M input / $0.60/M output on OpenRouter, vs.
DeepSeek's own listed $0.3/M input / $1.2/M output at peak (half off-peak).
Weights posted to Hugging Face under the MIT license.

DeepSeek says V4.1-Flash beats the previously-tracked
[deepseek-v4-pro](/models/deepseek-v4-pro.md), and from 2026-09-14 04:00 UTC
began routing all V4-Pro API requests to V4.1-Flash at Flash rates — a
functional retirement of V4-Pro pending a future V4.1-Pro release.

# Repo / source check — unverified

Open-weight (Hugging Face, MIT license per secondary sources), but this
pass could not reach either DeepSeek's own API docs
(`api-docs.deepseek.com`, DNS-blocked by this sandbox's egress allowlist)
or OpenRouter's model page (`openrouter.ai`, same DNS block) to verify
directly. Grounded instead via WebSearch cross-corroboration across five
independent outlets (TheNextWeb, thebridge.jp, technews.tw, tproger.ru,
ai-indeed.com) that agree closely on the architecture, date, and routing
change — but none of this is a primary-source fetch, and the benchmark
claims backing "beats V4-Pro" are DeepSeek's own, not independently
reproduced. Kept `unverified` per the bundle's grounding rule until a
direct fetch of the model card or API docs succeeds.

# Why this is in the radar

Closes the gap in the bundle's only-partially-tracked DeepSeek lineage: the
prior `deepseek-v4-pro` entry is now functionally retired (DeepSeek itself
routes its traffic away), so `supersedes` here drives the same "speak up"
mechanic the bundle uses for Claude/GPT lineage changes. DeepSeek remains
one of the most price-aggressive open-weight competitors worth watching.

# Notes

- Retry `api-docs.deepseek.com` and `openrouter.ai` at the next scan — both
  were DNS-blocked by this sandbox's network allowlist this pass, not
  confirmed genuinely unreachable from a different environment.
- Watch for V4.1-Pro, which per DeepSeek's own routing note is still
  pending.
