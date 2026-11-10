---
type: Index
title: devsec-tools — linters / scanners / supply-chain
description: Developer and security tooling — linters, scanners, supply-chain checks.
tags: [security, linters, supply-chain]
timestamp: 2026-11-04T00:00:00Z
---

# devsec-tools

Linters, scanners, supply-chain and security tooling relevant to the harness.

## Entries

- [skillspector-nvidia](/devsec-tools/skillspector-nvidia.md) — NVIDIA's official open-source agent-skill scanner; likely the real-world tool behind this project's own "skillspector" scan-before-trust rule — follow up by hand
- [mcp-scanner-cisco](/devsec-tools/mcp-scanner-cisco.md) — Cisco vendor-backed MCP server/tool scanner; re-verified active and healthy
- [snyk-agent-scan](/devsec-tools/snyk-agent-scan.md) — scans agents/MCP servers/skills for prompt injection & tool poisoning; re-verified, strong trajectory
- [cloudflare-security-audit-skill](/devsec-tools/cloudflare-security-audit-skill.md) — Cloudflare's official adversarial-validation code-audit skill; comparable to this project's own code-review verify pass
- [deepteam-redteam](/devsec-tools/deepteam-redteam.md) — org-backed LLM/agent red-teaming/attack-simulation framework, complements the scanners above
- [ai-infra-guard](/devsec-tools/ai-infra-guard.md) — Tencent red-team platform for agents/MCP/skills; v4.5.2/v4.6.0 shipped (LLM API poisoning detection)
- [aisoc](/devsec-tools/aisoc.md) — open-source "AI SOC" alert-triage agent; unverified, do-not-recommend pending review (self-reported figures, vendor-funded)
- [api-relay-audit](/devsec-tools/api-relay-audit.md) — audits LLM API relays/proxies for tampering (prompt injection, model substitution); unverified
- [malskanner](/devsec-tools/malskanner.md) — scans repos for hidden prompt-injection payloads before agent ingestion; unverified, stale, do-not-recommend
- [hexstrike-ai](/devsec-tools/hexstrike-ai.md) — offensive MCP pentest framework (awareness; do-not-auto-recommend); re-verified, grown to 13.3k stars, v7.0 still unreleased
- [shannon-ai-pentester](/devsec-tools/shannon-ai-pentester.md) — Keygraph's AI pentesting agent; live-exploit, awareness/do-not-auto-recommend, same bucket as hexstrike-ai
- [appsec-toolchain](/devsec-tools/appsec-toolchain.md) — phase->tool matrix (destructive flag) the /pentest engine reads; flagged stale (~57 days) this scan, re-verification still owed
- [npm-shai-hulud-scanner](/devsec-tools/npm-shai-hulud-scanner.md) — npm supply-chain worm scanner; unverified, do-not-recommend pending review; unchanged
- [memtensor-memos-compromise](/devsec-tools/memtensor-memos-compromise.md) — credential-stealing MemOS npm/PyPI builds (Sep 2026)
