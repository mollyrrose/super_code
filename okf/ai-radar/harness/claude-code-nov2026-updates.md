---
type: pattern
title: "Claude Code - Nov 2026 harness updates (v2.1.319-2.1.322)"
description: "denyInsteadOfPrompting setting, MCP tasks backgrounded, /loop self-paced now ends without reschedule, Fable 5.2 default, MCP OAuth redirect secret-leak fix."
tags: [claude-code, hooks, mcp, loop, changelog]
timestamp: 2026-11-10T00:00:00Z
resource: https://code.claude.com/docs/en/changelog
status: current
supersedes: [harness/claude-code-oct2026-updates]
---

# Summary

Official changelog (first ~100k chars only), v2.1.319 (2026-11-06) to v2.1.322 (2026-11-10).

- **2.1.319:** MCP tasks background in the terminal (`CLAUDE_CODE_DISABLE_MCP_TASK_BACKGROUND` to wait);
  new `permissions.denyInsteadOfPrompting` (deny rather than block on a permission prompt);
  auto mode with telemetry/feature flags off no longer falls back to the built-in classifier
  (`CLAUDE_CODE_AUTO_MODE_SERVER=0` restores it); **self-paced `/loop` now ends when a turn does not
  reschedule** (`CLAUDE_CODE_LOOP_KEEPALIVE=1` = old behaviour); `/claude-api latency-optimize`.
- **2.1.321:** `claude-fable-5-2` is the default Fable model (1M ctx, $8/$40 per Mtok); saved Fable 5.1
  picks move to `fable`. Mods Claude writes no longer self-enable in auto/bypass modes. Fixed MCP OAuth
  sending refresh tokens to another host after a redirect, and a read-only Bash command running unsandboxed
  without a prompt. `claude remote-control --settings <file>`.
- **2.1.322:** fast mode on Vertex (global/us/eu).
- Opus 4.8 fast mode removal still due 2026-11-30 (secondary sources).

Relevance: any `/loop`-based repo workflow must set `CLAUDE_CODE_LOOP_KEEPALIVE=1` or reschedule explicitly;
`denyInsteadOfPrompting` suits unattended routines.
