---
type: model
title: DeepSeek V4-Pro-0813 (GA)
description: DeepSeek's agentic/tool-use model, exited preview to GA in August 2026; functionally retired 2026-09-14 when DeepSeek began routing its traffic to V4.1-Flash.
tags: [deepseek, open-weight, pricing, context-window, release, agentic, superseded]
timestamp: 2026-11-04T00:00:00Z
resource: https://api-docs.deepseek.com/updates/
status: superseded
supersedes: []
---

# Summary

DeepSeek-V4-Pro-0813 had been in preview since April 2026 and became
officially GA (app/web/API) in August 2026, focused on agentic tool-use and
multi-step workflow tasks. Up to 1M-token context, up to 384,000 output
tokens, switchable thinking/non-thinking modes. No official DeepSeek V5
announcement, changelog entry, or live model string found as of this sweep
— V5 remains rumor-only.

# Repo / source check — unverified

DeepSeek is open-weight; a Hugging Face/GitHub model card likely exists for
V4-Pro but was not fetched directly this pass — license terms (DeepSeek has
historically used a custom, not strictly MIT/Apache, license) need
confirming before citing. GA-date claim cross-checked against Yahoo
Tech/Axios coverage and the official DeepSeek API changelog listing, both of
which agree on the August GA.

# Why this is in the radar

DeepSeek was entirely untracked in this bundle despite being one of the
most-watched open-weight competitors on price; this closes that gap. Note:
distinct from [deepseek-harness](/harness/deepseek-harness.md), which
tracks DeepSeek's separate agent-harness product, not its models.

# Notes

- **Superseded 2026-11-04 scan:** DeepSeek began routing all V4-Pro traffic
  to [DeepSeek V4.1-Flash](/models/deepseek-v4-1-flash.md) from
  2026-09-14 04:00 UTC, billed at Flash rates — a functional retirement
  pending a future V4.1-Pro release. See that entry for current detail.
