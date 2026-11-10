---
type: model
title: GPT-6 Astra
description: OpenAI's new flagship — 1.05M-token context, "computer use," and tiered long-context pricing; supersedes GPT-5.6 as the current OpenAI family.
tags: [openai, gpt, pricing, context-window, release, computer-use]
timestamp: 2026-09-08T00:00:00Z
resource: https://developers.openai.com/api/docs/models/gpt-6-astra
status: current
supersedes: [models/gpt-5-6]
---

# Summary

Released as a limited preview 2026-09-03, to paid users 2026-09-04. Context
window 1,050,000 tokens, up to 128,000 output tokens. Standard pricing $10/M
input, $50/M output for prompts up to 272K tokens ($1/M cached input,
$12.50/M cache-write); prompts over 272K tokens bill the *entire* request at
long-context rates ($20/M input, $2/M cached input, $25/M cache-write,
$75/M output) — a new "whole-request-repriced-past-threshold" pattern also
seen this cycle in Grok 4.6 (see [grok-4-6](/models/grok-4-6.md)). Headline
capability is "computer use" (navigating a computer like a human) plus
claimed gains in math, software engineering, and defensive cybersecurity.
OpenAI said it was trained on 100,000+ GPUs at the Stargate Texas site, its
largest training run to date. This is the "Astra" codename the bundle's
`gpt-5-6` entry already flagged as in-development/unreleased as of the last
scan.

# Repo / source check

Closed-source, no repo. `developers.openai.com`/`openai.com` were blocked
by this sandbox's egress proxy; pricing and context-window figures were
cross-checked across four independent aggregators (OpenRouter, llm-stats.com,
pricepertoken.com, layer3labs.io) that all agree — high confidence despite
the missing first-party fetch.

# Why this is in the radar

Directly supersedes the previously-tracked `gpt-5-6` as OpenAI's flagship;
the tiered long-context pricing is a new competitive pattern worth watching
against Anthropic's flatter 1M-token pricing.

# Notes

- Re-verify against an official OpenAI source once the sandbox's egress
  block on `openai.com` is confirmed lifted or worked around.

## 2026-11-10 note (unverified)

A search headline (gulfnews, page unreachable from the sandbox) reports "GPT-6.1 Sol" launched at one-fifth
the price after OpenAI scrapped an Astra upgrade; also GPT-6 Cyber in API 2026-11-05 at $20/$100 per Mtok
(datastudios roundup). Not confirmed from a primary source; re-verify next run before superseding this entry.
