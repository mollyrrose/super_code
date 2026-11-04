---
type: model
title: Gemini 3.7 Flash
description: Google's current Flash-tier model — 1M context, positioned as the workhorse for coding/agents.
tags: [google, gemini, flash, mid-tier]
timestamp: 2026-11-04T00:00:00Z
resource: https://ai.google.dev/gemini-api/docs/latest-model
status: current
supersedes: []
---

# Summary

Gemini 3.7 Flash released 2026-08-13, roughly three weeks after the prior
Flash update. 1,048,576 token context window, 65,536 max output tokens.
Pricing $0.75/$3.75 per MTok (input/output) through 2026-12-31, rising to
$1.50/$7.50 on 2027-01-01. Positioned by Google as its "most intelligent
workhorse" model for coding and agentic use cases.

# Why this is in the radar

Not previously tracked in the bundle. Recorded as superseding the prior Flash
generation in Google's own lineup, though no `models/gemini-3-6-flash` entry
existed here to formally supersede.

# Repo / source check

Closed-source model, no GitHub repo to inspect. Grounding: official Google
AI docs page (`resource`), cross-checked via WebSearch against DataNorth.ai
and Axios coverage of the 2026-08-13 release (direct fetch of ai.google.dev
was not attempted in this pass; recommend a follow-up direct fetch to confirm
the docs page reflects 3.7 Flash as current at the next scan).

# Notes

- Verify against ai.google.dev directly at the next scan if egress allows.
- **2026-11-04 re-check:** no newer Gemini release found as current.
  Reports describe a "Gemini 4 Pro" rumored for an October 2026 target
  (single-source, unverified) and The Information reporting Google aims to
  ship Gemini 4 before end-of-2026 with no confirmed date — treat both as
  rumor, not release, until an official Google source confirms. This entry
  stays `current` pending that.
