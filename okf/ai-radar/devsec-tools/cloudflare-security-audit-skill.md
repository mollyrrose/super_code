---
type: tool
title: Cloudflare security-audit-skill
description: Cloudflare's official open-source coding-agent skill that turns an agent into a multi-phase, adversarially-validated security auditor over a codebase (not a live-target pentest tool).
tags: [devsec, sast, skill, cloudflare, code-review, adversarial-validation]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/cloudflare/security-audit-skill
status: current
supersedes: []
adoption: awareness-candidate
---

# Summary

`cloudflare/security-audit-skill` is Cloudflare's official, MIT-licensed
coding-agent skill (install via `npx skills add
https://github.com/cloudflare/security-audit-skill --skill security-audit`)
that orchestrates isolated sub-agents through six phases: (1)
reconnaissance mapping architecture/trust-boundaries/input-surfaces, (2)
coverage-led hunting against a coverage ledger, (3) candidate validation by
a fresh verifier that tries to disprove each finding, (4) structured
confirmed/needs_validation/rejected output, (5) independent record
verification, (6) reporting (`REPORT.md`, `FINDINGS-DETAIL.md`,
`NEEDS-VALIDATION.md`). Ships attack-class playbooks (memory safety,
AI/LLM apps, web protocols, client-side, supply chain, cloud, desktop/
mobile) and zero-dependency Node.js validators for its own output files.
58.5k stars / 3.8k forks / 212 watchers, 14 commits — a thin commit count for
that star count, consistent with a skill-file repo (mostly markdown/
playbooks) rather than a large codebase, not necessarily a red flag by
itself. No dated last-commit/release shown on the repo page. Per its own
README it is the public starting point for Cloudflare's internal
vulnerability-discovery harness; multiple runs are additive (authors report
a single run finds roughly half of what repeated runs find in total).

# Repo / source check

Inspected the real repo (README, license, phase design, install mechanism,
star/fork/commit counts). Official Cloudflare org account; design is
specific and internally consistent (adversarial validation, severity
requires demonstrated impact, sandboxed execution requirements explicitly
called out). Did not independently run the skill or verify its
find-rate claims. `status: current`, `adoption: awareness-candidate` — not
yet compared head-to-head against this project's own `/code-review` and
`security-review` skills, which use a related but not identical
adversarial-verification pattern (reviewer finds, separate pass verifies).

# Why this is in the radar

Directly comparable to this project's own review/verification pattern
(see the `code-review` skill's verify pass and `ReportFindings`
CONFIRMED/PLAUSIBLE verdicts) — a named, official, vendor-maintained example
of the same "never let the finder also be the verifier" design converging
independently at Cloudflare. Non-offensive (static analysis of the target's
own code, not live exploitation against running infra), so it sits in a
different risk tier than hexstrike-ai/shannon in this same topic folder —
closer in spirit to this project's own tooling than to the offensive-agent
cluster. Worth a side-by-side comparison in a future scan to see whether its
playbooks or coverage-ledger mechanism suggest improvements to this
project's own review gates.

# Notes

- Re-check commit/release dates at next scan; 14 commits for a 58.5k-star
  repo is unusual enough to revisit once more signal (issues, discussion,
  external write-ups) accumulates.
