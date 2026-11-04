---
type: Index
title: knowledge — RAG / OKF / knowledge-graph / agent-memory
description: Patterns for structuring knowledge that AI agents consume and maintain.
tags: [rag, okf, knowledge-graph, memory]
timestamp: 2026-11-04T00:00:00Z
---

# knowledge

RAG, OKF, knowledge-graph, and agent-memory patterns.

## Entries

- [open-knowledge-format](/knowledge/open-knowledge-format.md) — OKF v0.1 -> v0.2 spec; now its own standalone repo, first third-party tooling (okf-skills) appearing
- [llm-wiki-compounding](/knowledge/llm-wiki-compounding.md) — compounding wiki vs RAG
- [prompt-caching](/knowledge/prompt-caching.md) — Anthropic prefix cache; narrow applicability to us
- [attention-residuals](/knowledge/attention-residuals.md) — model-architecture method; not-applicable
- [continuous-learning-loop](/knowledge/continuous-learning-loop.md) — Sona/RuVector framing; validates our direction
- [anthropic-dreaming-memory](/knowledge/anthropic-dreaming-memory.md) — first-party between-session memory consolidation
- [gbrain](/knowledge/gbrain.md) — self-wiring markdown knowledge graph (production-scale reference impl)
- [graphiti-zep](/knowledge/graphiti-zep.md) — temporal knowledge graph for agent memory; v0.30.1 released 2026-09-01
- [cognee](/knowledge/cognee.md) — graph-native agent memory framework; active weekly release cadence (v1.5.1-v1.5.4)
- [mem0-agent-memory-benchmark-2026](/knowledge/mem0-agent-memory-benchmark-2026.md) — claimed benchmark, unverified
- [maximem-synap](/knowledge/maximem-synap.md) — new vendor agent-memory SDK, self-reported benchmarks vs. mem0; unverified
- [openviking](/knowledge/openviking.md) — self-evolving context DB (Volcengine); vendor-reported benchmarks
- [graphify](/knowledge/graphify.md) — codebase-to-knowledge-graph tool for Claude Code et al.; same project as this repo's own `graphifyy` dependency, claimed ~142k star count unverified

See also the [cognition](/cognition/index.md) topic for brain-inspired
memory/thinking architectures split out from this topic on 2026-08-27.
