---
type: Index
title: AI Radar — catalog
description: Top-level catalog of the AI Radar OKF bundle.
timestamp: 2026-11-04T00:00:00Z
---

# AI Radar

Compounding knowledge of what is new / better in the AI world. See `README.md`
for the format and `log.md` for the ingest timeline. The weekly routine follows
[ROUTINE.md](/ROUTINE.md) (self-updating runbook); findings that should change
the repo go through [adoption-queue.md](/adoption-queue.md); dependencies the
projects run (anonymous) are in [watchlist.md](/watchlist.md).

## Topics

- [harness](/harness/index.md) — Claude Code / hook / skill / MCP capabilities
- [models](/models/index.md) — Claude / OpenAI / GLM releases, price, limits
- [knowledge](/knowledge/index.md) — RAG, OKF, knowledge-graph, agent-memory
- [cognition](/cognition/index.md) — brain-inspired memory/thinking architectures for agents
- [agent-tooling](/agent-tooling/index.md) — frameworks, orchestration, prompting
- [devsec-tools](/devsec-tools/index.md) — linters, scanners, supply-chain

## Entries (curated highlights)

- [models/claude-opus-5-5](/models/claude-opus-5-5.md) — current Anthropic flagship; supersedes opus-5; 20% cheaper, near-Fable-5.1 performance
- [models/claude-sonnet-5-5](/models/claude-sonnet-5-5.md) — current Anthropic mid-tier; supersedes sonnet-5 (the model this session itself still runs on)
- [models/claude-haiku-5-5](/models/claude-haiku-5-5.md) — low-cost tier, last of the Claude 5.5 family; ship date unverified
- [models/claude-fable-mythos-5-1](/models/claude-fable-mythos-5-1.md) — Anthropic's separate frontier-agentic tier above Opus; 5.1 cuts cache-read cost 75%
- [models/gpt-6-astra](/models/gpt-6-astra.md) — OpenAI's current flagship; supersedes gpt-5-6
- [models/deepseek-v4-1-flash](/models/deepseek-v4-1-flash.md) — DeepSeek's current default; supersedes v4-pro; unverified
- [knowledge/graphify](/knowledge/graphify.md) — same project as this repo's own `graphifyy` dependency; claimed ~142k stars unverified, supply-chain gap flagged (audited 0.8.x vs. shipped 0.9.102)
- [devsec-tools/skillspector-nvidia](/devsec-tools/skillspector-nvidia.md) — NVIDIA's agent-skill security scanner; directly relevant to this project's own "skillspector" references
- [harness/claude-code-oct2026-updates](/harness/claude-code-oct2026-updates.md) — latest official Claude Code harness changes (v2.1.295-2.1.318)
- [harness/ecc-agent-harness](/harness/ecc-agent-harness.md) — plugin already installed in this project; v2.2.3, star count still unverified/inflated-pattern
- [agent-tooling/trending-skillpack-star-inflation-pattern](/agent-tooling/trending-skillpack-star-inflation-pattern.md) — lint caution: multiple trending skill-pack repos now show identical 312.1k star counts despite different commit depths
- [harness/spec-driven-dev-tooling](/harness/spec-driven-dev-tooling.md) — github/spec-kit vs. Fission-AI/OpenSpec, both trending
- [cognition/claude-mem](/cognition/claude-mem.md) — star count now corroborated across 4 independent trending views, upgraded to current
- [cognition/mempalace](/cognition/mempalace.md) — local-first verbatim memory + temporal graph; unverified
- [cognition/dreaming-consolidation-research-2026](/cognition/dreaming-consolidation-research-2026.md) — offline-consolidation research cluster, including counter-evidence against in-place memory rewriting
- [cognition/memory-portability-model-upgrade-2026](/cognition/memory-portability-model-upgrade-2026.md) — controlled study validating this project's own graph-over-notes memory design
- [agent-tooling/openclaw](/agent-tooling/openclaw.md) — 389k-star open-source agent harness, now repositioning as team/enterprise infra
- [knowledge/open-knowledge-format](/knowledge/open-knowledge-format.md) — OKF v0.1 -> v0.2 spec; now its own repo, first third-party tooling appearing
- [knowledge/llm-wiki-compounding](/knowledge/llm-wiki-compounding.md) — compounding wiki vs RAG; past the 120-day freshness window, needs re-verification
- [devsec-tools/hexstrike-ai](/devsec-tools/hexstrike-ai.md) — offensive MCP pentest framework (awareness); re-verified
- [devsec-tools/npm-shai-hulud-scanner](/devsec-tools/npm-shai-hulud-scanner.md) — unverified; do-not-recommend pending review
- [agent-tooling/headroom](/agent-tooling/headroom.md) — context compressor (audited clean, do-not-install); past the 120-day freshness window
- [cognition/memanto](/cognition/memanto.md) — typed semantic memory, ships Claude Code integration
- [harness/openai-codex](/harness/openai-codex.md) — competing terminal coding agent
- [models/k2-horizon-mova-36b-a4b](/models/k2-horizon-mova-36b-a4b.md) — evaluated for a speed role, not adopted
