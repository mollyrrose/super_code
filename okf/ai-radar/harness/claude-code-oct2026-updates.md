---
type: pattern
title: Claude Code — Oct-Nov 2026 harness updates (v2.1.295-2.1.318)
description: Fork subagents on by default outside the terminal, new agent.spawn/prompt.change mod hooks, MCP tool-description limits raised then version-negotiated, idle compaction, and per-event hook concurrency caps.
tags: [claude-code, hooks, mcp, subagents, skills, changelog]
timestamp: 2026-11-04T00:00:00Z
resource: https://code.claude.com/docs/en/changelog
status: superseded
supersedes: [harness/claude-code-aug2026-updates]
---

# Summary

Official changelog fetched directly (code.claude.com/docs/en/changelog), covering
v2.1.295 (2026-10-08) through v2.1.318 (2026-11-04) — the most recent ~4 weeks.
Highlights:

- **Hooks:** command/HTTP hooks gained `onFailure: "block"` (a hook that can't
  start, times out, or errors now blocks the action rather than silently
  passing — directly relevant to this project's own "silent no-op on bad
  input" hook convention, which is the opposite default; worth re-reading
  against `hook_dispatch.py`'s philosophy). New `agent.spawn` mod hook can
  rewrite a workflow agent's `prompt`/`model`; new `prompt.change` mod hook
  fires on non-typed prompt-box changes. `UserPromptSubmit` now runs before
  skill/command expansion. Hook concurrency is capped (max 12-24 running at
  once per event, depending on version) — a protection this project's own
  `proc_registry.py reap-hooks` sweep (see CLAUDE.md, the 358-hung-hooks
  incident) would have benefited from natively.
- **Subagents:** fork subagents (`subagent_type: "fork"`) are now **on by
  default** outside the terminal (`-p`, Agent SDK, desktop, VS Code) as of
  v2.1.302 — `CLAUDE_CODE_FORK_SUBAGENT=0` opts out. New
  `CLAUDE_CODE_SUBAGENT_EFFORT` and `CLAUDE_CODE_WORKFLOW_SUBAGENT_MODEL` env
  vars for tiering. Subagents on a non-default model now keep that model's
  own saved effort level instead of inheriting the session's.
- **MCP:** default protocol version negotiation moved to 2026-07-28; tool
  description/server instruction length limits were raised (2,048 -> 4,096 ->
  16,384 chars across point releases); `mcp__<server>__*` allow-rules now
  require the server's full normalized name (a prefix like `mcp__a` no longer
  matches `a__b`) — a breaking change worth checking against any
  `allowed-tools`/`extra_allowed_tools` lists that use short MCP server
  prefixes.
- **Performance:** Sonnet 5.5 cache-read pricing dropped $0.20 -> $0.10/MTok.
  Idle compaction now runs in-terminal for 200K+-token conversations idle
  ~54 minutes (`CLAUDE_CODE_IDLE_COMPACT_MIN_TOKENS` / `"idleCompaction":
  false` to tune/disable) — a built-in counterpart to this project's own
  `context_budget_gate.py` pre-compact qUpd-flush tier.
- **Plugins:** marketplace re-cloning-on-every-refresh bug fixed (v2.1.302);
  scheduled cloud tasks now load plugins enabled on the account.
- **Fast-mode deprecation:** Fast mode for Opus 4.8 is deprecated as of
  2026-10-30 and will be **removed 2026-11-30** (requests will error, no
  fallback) — migrate to Opus 5.5 before that date.

# Repo / source check

Primary source: the official changelog page, fetched directly (not blocked
this pass, unlike several prior sweeps). Covers roughly 2026-10-08 onward;
the gap back to the last-tracked version here (v2.1.247, 2026-09-08) was not
independently re-verified from the official page this pass (time-budgeted —
a third-party tracker, havoptic.com, that could have back-filled Sept/early-Oct
detail was unreachable this sweep: `ENOTFOUND`, likely outside this sandbox's
allowed network domains). A third-party claim that v2.1.293 (2026-10-07) made
Haiku 5.5 the default model was seen in search snippets only, from the same
now-unreachable tracker — **not independently confirmed**, flagged for the
models topic to check separately rather than asserted here.

# Why this is in the radar

This is the harness this project runs on; several items directly intersect
existing project infrastructure (hook `onFailure` semantics vs. this repo's
silent-no-op convention; hook concurrency caps vs. `proc_registry.py
reap-hooks`; fork-subagents-on-by-default vs. this repo's existing fork usage
pattern; idle compaction vs. `context_budget_gate.py`'s qUpd-flush tier; the
`mcp__<server>__*` allow-rule tightening vs. any MCP permission entries in
`settings.json`). None of these require an immediate code change here, but
each is a candidate to re-check next time those subsystems are touched.

# Notes

- Re-fetch the Sept 2026 - early Oct 2026 changelog range next sweep to close
  the v2.1.247 -> v2.1.295 gap properly, and re-try havoptic.com (or another
  third-party tracker) for the Haiku-5.5-default claim.
- Mind the Opus 4.8 fast-mode removal date (2026-11-30) if anything in this
  project pins fast mode explicitly.
