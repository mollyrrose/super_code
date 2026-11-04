---
type: Queue
title: AI Radar — adoption queue
description: Findings that should change this repo, with status. The routine's Adopt step reads and updates this file; the user approves/rejects by editing status.
timestamp: 2026-11-04T00:00:00Z
---

# Adoption queue

Status flow: `proposed` -> (`approved` by user) -> `branch-pushed` -> `done`,
or `rejected`. Class A = docs/config text, B = code with smoketest, C = needs
the user. To approve or reject, change `status:` and optionally add `reason:`.

## Open

### graphifyy installed version is unaudited
- status: proposed
- class: C
- source: [knowledge/graphify](/knowledge/graphify.md)
- what: Local `graphifyy` is **0.9.31**, but the last manual audit
  (`~/.claude/.skillspector_log.jsonl`, 2026-07-31) covered **0.8.37**. Upstream
  is at 0.9.102 with ~100 point releases in 3 months. Either re-audit 0.9.31 or
  pin back to 0.8.37 (`pip install graphifyy==0.8.37`).
- risk: supply-chain drift on a package that reads every memory file.
- revisit_if: n/a — needs a decision.

### Stale model ids in the global tiering doc
- status: done (2026-11-04, applied locally in the interactive session)
- class: A
- source: [models/claude-opus-5-5](/models/claude-opus-5-5.md)
- what: `~/.claude/CLAUDE.md` + `home_dotclaude/CLAUDE.md` "Subagent model
  routing" listed `claude-opus-4-8` / `claude-sonnet-4-6` / `claude-fable-5`.
  Updated to the current ids. Opus 4.8 fast mode is removed 2026-11-30.

### Cloud routine: install SkillSpector in the sandbox
- status: done (2026-11-04, written into ROUTINE.md guardrail 2)
- class: A
- source: [devsec-tools/skillspector-nvidia](/devsec-tools/skillspector-nvidia.md)
- what: Confirmed `NVIDIA/skillspector` is the same tool installed locally at
  `~/.claude/tools/skillspector`. The cloud run now installs it with `uv tool
  install` before scanning, instead of marking every repo `unverified`.

### Routine silent-failure detection
- status: proposed
- class: B
- source: 2026-09-15..2026-11-03 run logs (403 `authentication_failed`, 8 runs)
- what: `RemoteTrigger` reports these runs as finished, so nobody noticed for 8
  weeks. Add a check to `/radar-check` (or qRem orientation): if the newest
  `okf/ai-radar/log.md` entry is older than 10 days, print one line saying the
  radar routine is not landing.
- revisit_if: n/a.

### Switch routine model to Sonnet 5.5
- status: proposed
- class: C
- source: [models/claude-sonnet-5-5](/models/claude-sonnet-5-5.md)
- what: Same price as Sonnet 5, ~30% faster. The exact API model id was not
  confirmed from a primary source, and a wrong id would break the routine
  silently. Confirm the id, then update the trigger's `model`.
- revisit_if: the id appears on the official models page.

## Rejected

### Hook `onFailure: "block"`
- status: rejected
- class: B
- source: [harness/claude-code-oct2026-updates](/harness/claude-code-oct2026-updates.md)
- reason: Opposite of this repo's silent-no-op hook contract (a broken hook
  must never block every Write/Edit).
- revisit_if: a hook becomes a real security gate where failing open is worse
  than blocking.

### Short `mcp__<prefix>` allow-rules
- status: rejected (no-op)
- class: A
- source: [harness/claude-code-oct2026-updates](/harness/claude-code-oct2026-updates.md)
- reason: Checked 2026-11-04: no `mcp__` allow-rules exist in `settings.json`,
  so the breaking change does not affect this setup.
- revisit_if: MCP allow-rules are added.

## Watch (no action yet)

- Idle compaction (200K+ tokens, ~54 min idle) overlaps the
  `context_budget_gate.py` qUpd-flush tier; check whether it fires before the
  flush does next time the gate is touched.
- Hook concurrency caps (12-24 per event) are a native backstop for the
  358-hung-hooks incident; `proc_registry.py reap-hooks` stays.
- Dreaming/consolidation counter-evidence supports memgraph-ingest's
  non-destructive design; no change.
