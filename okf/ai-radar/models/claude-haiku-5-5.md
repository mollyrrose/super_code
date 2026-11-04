---
type: model
title: Claude Haiku 5.5
description: Fourth and last model in the Claude 5.5 family — fast, low-cost tier; release date not confirmed from a primary source.
tags: [anthropic, claude, haiku, low-cost, release]
timestamp: 2026-11-04T00:00:00Z
resource: https://www.anthropic.com/claude-haiku-5-5
status: unverified
supersedes: []
---

# Summary

Haiku 5.5, the third/last model in the "Claude 5.5" family (after Opus 5.5
on 2026-09-22 and Sonnet 5.5 on 2026-09-28), was named by Anthropic as
"following in the coming weeks" when Opus 5.5 launched. Secondary sources
disagree on the exact ship date: a Vals AI model listing and a Japanese
tech blog both point to 2026-10-07; one other source claims 2026-10-03 and
reads as less reliable; a fourth source as of 2026-10-05 reported no
release date existed yet. No pricing, benchmark, or capability detail was
independently confirmed this scan beyond "aimed at high-throughput,
low-cost workloads."

# Repo / source check

Closed-source, no repo. No official Anthropic announcement page was found
in this scan's search results — every source is secondary and they
disagree on the exact date. Per this bundle's grounding rule, `status:
unverified` until a primary-source date/pricing confirmation lands.

# Why this is in the radar

This project's own model-tiering policy (see the global CLAUDE.md
"Subagent model routing (tiering)" section, surfaced into context via
`smart_router_prompt_hook.py`'s `[model-router hint]`) explicitly routes
some subagent work to the haiku tier — so confirming Haiku 5.5's actual
availability/pricing matters directly for that routing logic, unlike the
Opus/Sonnet 5.5 entries which mostly inform awareness. Re-verify at the
next scan: exact ship date, pricing, and whether the tiering policy should
reference `claude-haiku-5-5` by name.
