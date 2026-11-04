---
type: tool
title: MemPalace — local-first verbatim memory with a temporal knowledge graph
description: Stores AI-tool conversation/project history verbatim (no summarization) under a wings/rooms/drawers hierarchy, with a separate SQLite-backed temporal entity graph and hybrid keyword+vector+temporal retrieval.
tags: [agent-memory, knowledge-graph, local-first, temporal-graph]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/MemPalace/mempalace
status: unverified
supersedes: []
---

# Summary

MemPalace is a local-first memory system for AI tools. It stores
conversation history and project content as verbatim text (explicitly does
NOT summarize or paraphrase) and retrieves it with hybrid semantic + keyword
+ temporal-proximity search, with an optional LLM reranker. Content is
organized into "wings" (people/projects), "rooms" (topics), and "drawers"
(original content). Defaults to ChromaDB, MIT licensed, 2,533 commits on
`develop`, version badge 3.12.0. A separate temporal knowledge graph
(SQLite-backed, validity windows, add/query/invalidate/timeline operations)
is a supplementary feature, not the primary retrieval mechanism.

# Repo / source check

MIT license confirmed. 2,533 commits suggests real, sustained development,
but no commit/release date was visible in the fetched page, and the
Releases section was empty — can't independently confirm the claimed ~60.4k
star count against an activity timeline the way
[claude-mem](/cognition/claude-mem.md) could be partly corroborated this
sweep (4 independent trending views agreeing). The README itself names its
own benchmark honestly (avoids claiming "100%," says the final gap was
reached by inspecting wrong answers) and separately warns about "impostor
domains" for the official repo/package — a legitimate-sounding caution, but
also a signal this project has had real confusion/copycat issues worth
being careful about. Per this bundle's conservative rule: `status:
unverified` pending a direct github.com check of the stargazer timeline and
recent commit dates.

# Why this is in the radar

Different point in the same design space as this project's own memory
layer and as claude-mem: MemPalace keeps memory verbatim rather than
extracting structured facts (this project's typed-markdown + graph
approach) or AI-compressing it (claude-mem's approach), relying instead on
hierarchical scoping (wings/rooms/drawers) plus a temporal graph as a
supplementary filter. No consolidation/replay step — worth noting as a
counterpoint to the consolidation-heavy research in
[dreaming-consolidation-research-2026](/cognition/dreaming-consolidation-research-2026.md):
MemPalace's bet is "never lose the original," which is closer to the
counter-evidence paper's recommendation in that entry than to the
consolidation papers.
