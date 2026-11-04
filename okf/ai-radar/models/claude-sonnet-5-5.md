---
type: model
title: Claude Sonnet 5.5
description: Anthropic's current mid-tier model — second in the Claude 5.5 family; same $2/$10 pricing as Sonnet 5, 30%+ faster, up to 30% cheaper per task.
tags: [anthropic, claude, sonnet, mid-tier, release]
timestamp: 2026-11-04T00:00:00Z
resource: https://www.anthropic.com/claude-sonnet-5-5
status: current
supersedes: [models/claude-sonnet-5]
---

# Summary

Claude Sonnet 5.5 shipped 2026-09-28 as the second model in the new
"Claude 5.5" family (after [Opus 5.5](/models/claude-opus-5-5.md) on
2026-09-22, before Haiku 5.5). API pricing is unchanged from Sonnet 5: $2/M
input, $10/M output, $0.20/M cache reads. Output runs 30%+ faster than
Sonnet 5, and Anthropic reports per-task cost falling up to 30% for most
work. Anthropic pitches it for everyday coding, bug fixes, document work,
slide decks, and spreadsheets, and highlights strong design-related-task
results. One vendor-reported benchmark cites Terminal-Bench 4.0 at 70.6%
vs. 10.3% for Sonnet 5 — a large jump that is self-reported and not
independently reproduced here.

This resolves the open question left in
[claude-opus-5-5](/models/claude-opus-5-5.md)'s Notes section (added
2026-09-22-equivalent scan, re-checked here): yes, Sonnet 5.5 is real and
shipped. **This session's own configured model is `claude-sonnet-5`**
(not `-5-5`) with fallbacks `claude-opus-5-5[1m]` / `claude-opus-5[1m]` —
i.e. this exact session is running one tier behind its own radar's current
mid-tier model.

# Repo / source check

Closed-source, no repo. Primary `anthropic.com/claude-sonnet-5-5`
announcement page was not directly fetched this pass (not attempted; time
budget went to confirming existence/date/pricing via WebSearch first).
Corroborated via multiple independent outlets (inside.com.tw, technews.tw,
digg.com, windowsreport.com, af.net, tech.ifeng.com) that converge on the
2026-09-28 date and the pricing/speed figures. Re-verify via a direct
`anthropic.com` or `platform.claude.com` fetch at the next scan if egress
allows.

# Why this is in the radar

Directly supersedes `models/claude-sonnet-5`, the entry this project's own
CLAUDE.md and session-identity block describe this exact setup as running
on. Also completes the "Claude 5 family" picture this session's own system
context names (Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5) — see
[claude-haiku-5-5](/models/claude-haiku-5-5.md) for the fourth member.

# Notes

- Haiku 5.5 followed ~2026-10-07 — tracked separately at
  [claude-haiku-5-5](/models/claude-haiku-5-5.md).
- No context-window or max-output figures independently confirmed this
  pass; assume unchanged from Sonnet 5 (1M context, 128K max output) pending
  confirmation.
