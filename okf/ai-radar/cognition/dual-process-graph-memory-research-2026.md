---
type: pattern
title: 2026 academic cluster — dual-process & multi-graph agent memory (DCPM, SYNAPSE, MAGMA, BMAM, D-Mem)
description: Five related 2026 papers pushing agent memory toward daytime/nighttime dual-process consolidation, spreading-activation retrieval, multi-typed-graph representations, and subsystem-split (episodic/semantic/salience) memory.
tags: [dual-process, agent-memory, knowledge-graph, research, act-r]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/FredJiang0324/MAGMA
status: current
supersedes: []
adoption: algorithmic-inspiration-only
---

# Summary

Five related academic threads found across this and the prior sweep:

- **DCPM** ("Memory Beyond Recall: A Dual-Process Cognitive Memory System for
  Self-Evolving LLM Agents", arXiv 2606.09483, June 2026) reorganizes memory
  into a capability hierarchy (raw inputs -> atomic facts -> belief
  trajectories -> schemas/intentions) driven by a synchronous "daytime"
  writer and an asynchronous "nighttime" engine that induces schemas and
  resolves cross-domain contradictions.
- **SYNAPSE** ("Empowering LLM Agents with Episodic-Semantic Memory via
  Spreading Activation", arXiv 2601.02744, ACL 2026 Findings) models memory
  as a graph where relevance emerges from spreading activation (with lateral
  inhibition + temporal decay) rather than precomputed links, targeting the
  "contextual tunneling" failure mode on the LoCoMo benchmark.
- **MAGMA** ("A Multi-Graph based Agentic Memory Architecture", arXiv
  2601.03236, ACL 2026 main) represents each memory across four orthogonal
  graphs (semantic/temporal/causal/entity) and does policy-guided traversal
  across them, claiming wins over other agentic memory systems on
  LoCoMo/LongMemEval in its own evaluation.
- **BMAM** ("Brain-inspired Multi-Agent Memory Framework", arXiv 2601.20465,
  ACL 2026 Findings, added 2026-11-04) decomposes memory into specialized
  subsystems — episodic, semantic, salience — rather than a single store,
  reporting 78.45% on the standard LoCoMo long-horizon setting.
- **D-Mem** (arXiv, March 2026, added 2026-11-04) is a narrower dual-process
  split than DCPM: a cheap vector-retrieval "System 1" fast path, with an
  exhaustive "Full Deliberation" module as a slower high-fidelity fallback —
  no schema induction or nighttime consolidation, just two retrieval speeds.
- Also noted this sweep but not written up separately (too thin a signal):
  "Dual-Process Agent" (MDPI Electronics, March 2026, frozen-backbone
  fast/reflective split) and a Lerma-Torres et al. preprint (complementary
  learning systems theory mapped onto a working-memory-buffer +
  persistent-knowledge-graph dual store) — both read as variations on the
  same fast/slow theme already covered by DCPM/D-Mem above.

# Repo / source check

DCPM, SYNAPSE, BMAM, D-Mem: no repos found (paper-only). MAGMA has a real repo: 154
stars, MIT license, 6 commits, a structured codebase
(`graph_db.py`/`vector_db.py`/`query_engine.py`) including the actual LoCoMo
dataset and runnable eval scripts — looks like a genuine research
implementation, not a stub, but still small/early (single-digit commit
history suggests a recent squashed push rather than long development). All
five papers' benchmark numbers are self-reported and not independently
reproduced here.

# Why this is in the radar

Shows where the academic frontier is heading (spreading activation,
multi-typed graphs, daytime/nighttime dual-process memory) even though none
of it is production-ready. Adoptable as algorithmic inspiration only, for
either consumer: SYNAPSE's spreading-activation retrieval is a natural
upgrade path for this project's existing `graphify query` ("semantic
start-node + BFS relations" is a simplified precursor to spreading
activation), and MAGMA's multi-typed-graph-view idea could inform splitting
fact/temporal/causal edges if the memgraph ever needs richer structure.
