---
type: framework
title: Microsoft Agent Framework
description: Microsoft's unified successor to AutoGen and Semantic Kernel, reaching 1.0 GA in April 2026 with .NET and Python support; AutoGen itself moved to maintenance mode.
tags: [microsoft, orchestration, autogen, semantic-kernel, agent-framework]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/microsoft/agent-framework
status: current
supersedes: []
---

# Summary

Microsoft Agent Framework merges AutoGen (multi-agent orchestration) and
Semantic Kernel (enterprise plugin/skill abstractions) into one SDK,
reaching 1.0 general availability in April 2026 with both .NET and Python
support. Per independent secondary coverage, Microsoft moved AutoGen into
maintenance mode as part of this consolidation. Also relevant: Microsoft's
separately-released open-source Agent Governance Toolkit, designed to work
alongside LangChain/AutoGen/CrewAI rather than being tied to its own
framework.

# Repo / source check

This sweep's intake was via secondary-source aggregation (vendor/aggregator
blog roundups), not a direct primary-source fetch of Microsoft's own
announcement or the `microsoft/agent-framework` repo's README/releases —
flagged honestly rather than presented as independently verified. Treat the
April-2026 GA date and the AutoGen-maintenance-mode claim as
plausible-but-not-primary-sourced until a future scan fetches the repo and
Microsoft's own docs directly.

# Why this is in the radar

A named, major vendor's consolidation of two previously-separate, widely
used agent frameworks is significant context for the orchestration-pattern
landscape this topic tracks, and this bundle had no prior entry for either
AutoGen, Semantic Kernel, or their merger — this is a backfill of a
~7-month-old (April 2026) event missed across the ~57-day gap between this
sweep and the prior one (2026-09-08), not a "last 14 days" finding; noted
honestly per the sweep's coverage-gap reporting convention.

# Notes

- Re-fetch `github.com/microsoft/agent-framework` directly next scan for
  primary-source confirmation (license, real commit/release dates, current
  capabilities) rather than relying on secondary aggregation.
