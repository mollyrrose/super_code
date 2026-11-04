---
type: tool
title: AiSOC
description: Open-source "AI Security Operations Center" — ingests security telemetry, correlates alerts, runs LLM-agent investigations with logged reasoning, proposes human-approved responses. Self-reported figures, commercial-vendor-funded; not independently verified.
tags: [devsec, soc, mcp, llm-agent, unverified]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/beenuar/AiSOC
status: unverified
supersedes: []
adoption: do-not-recommend-pending-review
---

# Summary

AiSOC ingests security telemetry, correlates alerts, runs LLM-agent
investigations with logged reasoning, and proposes responses that require
human approval; ships an MCP server and a Docker Compose deployment. MIT
license, README badge version 22.0.0, 7.1k stars / 730 forks / 219 watchers,
4 open issues, 1,863 commits. Has real engineering scaffolding (CI, CodeQL,
OpenSSF Scorecard badges, SECURITY.md, CONTRIBUTING.md, GOVERNANCE.md,
MAINTAINERS.md, tests, Makefile) and development is funded by Cyble, a
commercial security vendor.

# Repo / source check

Inspected the real repo. Signals are mixed: substantial commit history and
proper OSS scaffolding cut toward "real," but unusual root-level clutter
(multiple progress-tracker markdown files like `DEPTH_PROGRESS.md`,
`FIX_PASS_PROGRESS.md`, plus several committed `.whl` binary packages) is
not typical of a clean, mature repo. The README leans on precise
self-reported figures (rule counts, benchmark claims) that the project
itself qualifies as partly beta, and it states no hosted LLM provider has
actually been tested against it. No independent stargazer-timeline or
contributor-breadth check was done this pass to judge whether the star
count is organic. No skillspector available in this sandbox to scan the
repo. Given the mix of real scaffolding plus self-reported/unverified
claims plus commercial-vendor funding (potential promotional-star
incentive), this is marked `status: unverified` and
`adoption: do-not-recommend-pending-review` rather than trusted outright —
consistent with this bundle's existing conservative posture (compare
[npm-shai-hulud-scanner](/devsec-tools/npm-shai-hulud-scanner.md) and
[malskanner](/devsec-tools/malskanner.md)).

# Why this is in the radar

Surfaced via GitHub trending (Python, weekly view) during this sweep. Logged
as a candidate for the "LLM-driven SOC / alert triage" niche, which nothing
else in this topic currently covers, but not recommended for adoption until
a deeper audit (stargazer timeline, contributor breadth, and at least one
independent LLM-provider test run) resolves the open questions above.

# Notes

- Re-check at next scan: has the stargazer trajectory normalized, has the
  "no LLM provider tested" gap closed, has the root-level file clutter been
  cleaned up.
