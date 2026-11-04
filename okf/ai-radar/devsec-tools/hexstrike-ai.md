---
type: tool
title: HexStrike AI
description: MCP server + autonomous offensive agents orchestrating 150+ pentest tools against LIVE targets — offensive, dynamic, high-caution.
tags: [offensive, pentest, red-team, mcp, ctf, awareness, high-caution]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/0x4m4/hexstrike-ai
status: current
supersedes: []
adoption: do-not-auto-recommend
---

# Summary

HexStrike AI is an MCP server (FastMCP, localhost:8888) plus 12+ autonomous
OFFENSIVE agents (BugBounty / CTF / CVE-Intelligence / ExploitGenerator) that
orchestrate 150+ offensive security tools (nmap, rustscan, amass, gobuster, sqlmap,
nuclei, wpscan, ghidra, radare2, gdb, prowler, scout suite, trivy, volatility,
steghide, exiftool, ...). It selects tools, tunes parameters, and chains attacks.

It is **dynamic and offensive**: it attacks LIVE running targets (network services,
web apps, cloud infra) — it does NOT review source code or a diff. v6.0, MIT,
10k+ stars, active development.

# Repo / source check

- Inspected the real repo (not just announcements). Offensive / red-team by design;
  intended for AUTHORIZED pentest, bug-bounty, CTF, red-team only.
- Heavy footprint: 150+ external tools, Chrome/Chromium, a resident service on :8888.
- The project's own docs warn: run in isolated VMs / dedicated security testing
  environments, and "never test systems without permission".
- High caution: widely reported as abused by threat actors in the wild. Treat as a
  dual-use, authorization-gated capability, never an ambient one.
- Pre-trust: a skillspector scan of the repo URL is REQUIRED before any install/use
  (standing scan-before-trust rule). See the AI Radar README intake rule.

# Why this is in the radar

Two reasons, both awareness — NOT a recommendation to wire it into everyday flows:

1. **Defensive threat-intel.** These are the autonomous offensive TTPs (recon ->
   web/app testing -> exploit chaining) that an AI-driven attacker can now run at
   scale. Knowing the shape of this tooling informs the defensive posture.
2. **Correct placement.** It does NOT belong in `/qRev` (static, fast, diff-scoped,
   auto-firing code review) — wrong layer and an autonomy/safety mismatch. If used
   at all, it lives in a separate, manually-invoked, VM-sandboxed,
   authorization-gated pentest skill (`/pentest-hexstrike`), never autonomous,
   never referenced by a hook or by qRev/qRem.

`adoption: do-not-auto-recommend` — `/radar-check` must NEVER surface this as a
"there is something better, adopt it" gate flag; it is an offensive capability, not
a dependency upgrade.

# Update (2026-09-08 scan): re-verified, adoption scale grown

Re-checked directly: `0x4m4/hexstrike-ai` now 11,664 stars / 2,412 forks /
127 open issues, pushed 2026-08-03, updated 2026-09-08 — one of the most-
forked offensive-MCP frameworks tracked in this bundle. Multiple
copycat/mirror repos exist (not the original); the canonical repo stays
`0x4m4/hexstrike-ai`. Also separately confirmed via GitHub trending: v6.0
release, with a v7.0 roadmap (250+ tools, containerized deployment).
`adoption: do-not-auto-recommend` unchanged — the caution reasoning above
still applies at this larger scale.

# Update (2026-11-04 scan): continued growth, v7.0 still unreleased

Re-checked directly: now 13.3k stars / 2.7k forks / 196 watchers / 66 open
issues (up from 11,664 stars at the 2026-09-08 check, +~1.7k over the ~57-day
gap between sweeps). README still headlines v6.0 "150+ tools / 12+ agents";
the v7.0 announcement ("250+ Specialized AI Agents/Tools," Docker support,
native desktop client, one-command setup, 40% memory reduction) remains an
unreleased "Coming Soon!" roadmap item, unchanged since the last check.
README also surfaces unverified, unsourced performance claims (e.g. "98.7%"
detection rate, "24x faster") with no methodology given — treat as marketing,
not a measured result. No change to `adoption: do-not-auto-recommend`.
