---
type: Index
title: cognition — brain-inspired memory and thinking architectures
description: Dual-process thinking, hierarchical/episodic-semantic memory, consolidation ("dreaming"), and cognitive-architecture patterns applied to LLM agents.
tags: [cognition, memory, dual-process, cognitive-architecture, agent-memory]
timestamp: 2026-11-04T00:00:00Z
---

# cognition

Brain-inspired memory and thinking architectures for AI agents: dual-process
(fast/slow) thinking, hierarchical + episodic/semantic memory, consolidation
and replay ("dreaming"), and cognitive architectures (ACT-R/Soar lineage)
applied to LLMs. Findings here are weighted by concrete adoptability for one
of two downstream consumers: (a) this project's own personal Claude Code
memory layer (typed markdown memory files + a knowledge graph over them), or
(b) a community-wide shared knowledge base ("community brain") — not by
hype.

New topic as of 2026-08-27. Two existing entries under `knowledge/` predate
this topic and are cross-linked here rather than duplicated:
[anthropic-dreaming-memory](/knowledge/anthropic-dreaming-memory.md) and
[graphiti-zep](/knowledge/graphiti-zep.md) / [cognee](/knowledge/cognee.md)
(knowledge-graph memory cluster).

## Entries

- [memory-portability-model-upgrade-2026](/cognition/memory-portability-model-upgrade-2026.md) — controlled study: fixed-schema graph memory survives a model swap, free-text notes don't; validates this project's memgraph-over-MEMORY.md design bet
- [timem-temporal-hierarchical-memory](/cognition/timem-temporal-hierarchical-memory.md) — 5-level temporal memory tree with complexity-aware recall; ACL 2026 Findings, SOTA on LoCoMo/LongMemEval-S
- [memanto](/cognition/memanto.md) — typed semantic memory, ships Claude Code integration; strongest direct match for the personal-memory-layer
- [hermes-agent-nousresearch](/cognition/hermes-agent-nousresearch.md) — open-source self-improving agent with MEMORY.md-nudge pattern; star count now corroborated by a second independent sweep
- [zenbrain-7layer-memory](/cognition/zenbrain-7layer-memory.md) — 7-layer neuroscience-inspired memory, ships an MCP server; small install base, self-reported benchmarks
- [claude-mem](/cognition/claude-mem.md) — cross-session Claude Code memory plugin; star count now corroborated 4x independently, upgraded to current
- [mempalace](/cognition/mempalace.md) — local-first verbatim memory, wings/rooms/drawers hierarchy + temporal graph; unverified
- [dreaming-consolidation-research-2026](/cognition/dreaming-consolidation-research-2026.md) — Auto-Dreamer + Active Dreaming Memory consolidation proposals, plus counter-evidence against in-place memory rewriting
- [agentmemory](/cognition/agentmemory.md) — hook-based multi-agent persistent memory; benchmark claims self-reported/unverified
- [claude-obsidian](/cognition/claude-obsidian.md) — local-first Obsidian+Claude Code PKM integration
- [talker-reasoner](/cognition/talker-reasoner.md) — foundational dual-process (fast/slow) agent architecture paper
- [dual-process-graph-memory-research-2026](/cognition/dual-process-graph-memory-research-2026.md) — 2026 academic cluster: DCPM, SYNAPSE, MAGMA, BMAM, D-Mem
- [letta-sleep-time-compute](/cognition/letta-sleep-time-compute.md) — MemGPT-lineage async "sleep-time agent" memory consolidation
- [lycheememory-v2-segment-consolidation](/cognition/lycheememory-v2-segment-consolidation.md) — semantic segment-level consolidation, cuts token cost; unverified
- [portable-agent-memory-protocol](/cognition/portable-agent-memory-protocol.md) — provenance-verified cross-agent memory-transfer protocol proposal; community-brain relevant; unverified

## Further reading (curated lists, not radar entries)

- https://github.com/TsinghuaC3I/Awesome-Memory-for-Agents — 100+ papers 2020-2026, organized by short/long-term and application category
- https://github.com/Shichun-Liu/Agent-Memory-Paper-List — companion to the "Memory in the Age of AI Agents" survey (arXiv 2512.13564)

## Cross-topic

- [knowledge/anthropic-dreaming-memory](/knowledge/anthropic-dreaming-memory.md)
- [knowledge/graphiti-zep](/knowledge/graphiti-zep.md)
- [knowledge/cognee](/knowledge/cognee.md)
- [knowledge/gbrain](/knowledge/gbrain.md)
