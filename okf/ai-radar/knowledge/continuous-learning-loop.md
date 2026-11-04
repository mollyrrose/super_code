---
type: technique
title: Continuous-learning loop (Sona / RuVector framing)
description: 'Intelligence in the loop — frozen base + adaptive layer, EWC anti-forgetting, learn-from-trajectories, topology memory. Validates our existing direction; no new build.'
tags: [continuous-learning, ruvector, lora, ewc, memory, agent-memory]
timestamp: 2026-06-29T00:00:00Z
resource: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
status: current
supersedes: []
adoption: validates-existing-direction-no-build
---

# What it is

A framing (from a "Sona self-optimizing neural architectures / RuVector" talk) that
the intelligence lives in the LOOP, not the frozen model: keep base weights frozen,
learn in a thin adaptive layer (micro-LoRA), evolve a topology/graph memory at runtime,
use EWC-style consolidation to avoid catastrophic forgetting, and learn from query
TRAJECTORIES rather than static RAG lookup. "Original implementation: RuVector."

# Does it apply to US? Validates direction; nothing new to build.

These are model-TRAINING concepts (LoRA, EWC, runtime weight mutation) — we don't train
a model, so the literal machinery is a category mismatch (and building a neural training
loop violates lowest-autonomy / boring-is-beautiful).

But the PHILOSOPHY already underpins our setup:
- The **AI Radar** is exactly a compounding, agent-maintained wiki that learns over time
  (see [[llm-wiki-compounding]]) — not static RAG.
- The **PCN "data first, algorithm later"** groundwork accumulates trajectory data
  (`.smart_router_eval.jsonl`, `.qrev_verdict_log.jsonl`, `.decision_log.jsonl`, qclose
  index) for an eventual learned predictor — the "learn from trajectories" idea.
- **RuVector** already exists in this repo (`ruvector.db`, the ruflo-core memory graph).
- The radar **lint pass** (contradiction/staleness) is the EWC-analog: consolidation to
  keep the knowledge base coherent.

# Repo / source check

Karpathy gist + the talk; no installable artifact for us. Verdict: confirms the path we
are already on (compounding memory + accumulate-data-then-learn); `adoption: no new
build`. The one forward step it points at — smart_router moving rule-based -> learned
once enough eval data accrues — is already the documented PCN plan.

# External validation (2026-08-27 scan)

Anthropic's own "Dreaming" primitive for Claude Managed Agents — see
[anthropic-dreaming-memory](/knowledge/anthropic-dreaming-memory.md) — is a
first-party vendor product doing the same between-session memory
consolidation this entry already argued for. Cited here as corroborating
evidence, not as a new build target.
