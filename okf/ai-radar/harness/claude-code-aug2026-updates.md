---
type: pattern
title: Claude Code — August 2026 harness updates (v2.1.232-2.1.247)
description: Subagent forking on by default, cross-session messaging, a rolling MCP/hook reliability pass, and the new SendFeedback tool.
tags: [claude-code, hooks, mcp, subagents, changelog]
timestamp: 2026-09-08T00:00:00Z
resource: https://code.claude.com/docs/en/changelog
status: superseded
supersedes: []
---

# Summary

Three harness-relevant changes landed in the official Claude Code changelog
between v2.1.232 (2026-08-13) and v2.1.247 (2026-08-26):

1. **Subagent forking on by default.** `subagent_type: "fork"` now inherits
   the full parent conversation and prompt cache by default (previously
   opt-in via env var). Forked subagents skip re-briefing and avoid the
   "compression tax" of long sessions.
2. **Cross-session messaging.** `@name` mentions reach another live Claude
   Code session; `SendMessage` can deliver to bare session names; sessions
   get unique auto-generated names (`name-word-word`). Turns concurrent
   windows into an addressable mesh — directly relevant to this repo's own
   `coord.py` cross-window coordination layer (see project CLAUDE.md).
3. **MCP/hook reliability hardening (rolling, ~10 point releases).** Hook and
   background-agent output overflow no longer wedges sessions; MCP tool-call
   interrupts report explicit errors instead of silently returning empty
   output; empty-schema (`{}`) MCP tool arguments no longer get stringified;
   remote MCP servers in `-p`/SDK sessions auto-reconnect after drops; stdio
   MCP servers no longer receive `server/discover` before `initialize`;
   plugin marketplaces gained GitLab support and control-character name
   rejection; self-hosted runner sessions gained server-supplied hook
   support.
4. **`SendFeedback` tool (v2.1.247, 2026-08-26).** Claude can draft an
   in-session feedback report for the user to review/send via `/feedback`.

# Why this is in the radar

Item 3 lands directly on the surfaces this repo's own hook system depends on
(the `hook_dispatch.py` consolidation, silent-no-op-on-bad-input discipline,
MCP tool usage throughout). Item 2 (cross-session messaging) overlaps in
spirit with this repo's own `coord.py`/`work.md` cross-window coordination —
worth a look at whether the built-in mesh reduces the need for the custom
layer, or whether they're complementary (built-in mesh is interactive/adhoc,
`coord.py` is file-based and survives across restarts).

# Repo / source check

Closed-source harness; grounding is the official Claude Code changelog
(`resource`), corroborated by an independent explainer
(joinnextdev.com) for item 1. `code.claude.com` itself was reachable in this
pass; `claude.com`'s blog was not (egress-proxy block in this sandbox).

# Notes

- No action taken on this entry beyond recording it — evaluating whether to
  adopt cross-session `@name` messaging alongside `coord.py` is a separate,
  deliberate decision, not an automatic radar "speak up".

# Update (2026-09-08 scan): more hook events, org-wide managed MCP servers

Further releases through v2.1.263 (confirmed nothing newer as of this
scan): v2.1.248 added per-agent `experimental.cacheTtl` frontmatter for
per-agent prompt-cache control. v2.1.251 (2026-08-28) added
`PreModelSwitch`/`PostModelSwitch` hook events (can block/confirm/annotate a
model switch) and enriched `SessionStart` resume hooks with
session-staleness and estimated re-cache-cost data. v2.1.259 (2026-09-02)
added a `managedMcpServers` setting so orgs can push HTTP/SSE MCP servers to
every user (command-based entries skipped for safety) and tightened
`allowedMcpServers` semantics. Related fixes: MCP tool-call interrupt
handling in headless/remote sessions, MCP arguments sent as raw JSON
strings for empty-schema params, nested background-subagent results not
persisting into the parent transcript, and a symlink-swap bug that let file
tools escape the approved working directory after permission checks
passed. Also see [claude-code-skill-doctor](/harness/claude-code-skill-doctor.md)
(v2.1.261) for the new skill-auditing command from the same window.

# Superseded (2026-11-04 scan)

Superseded by [claude-code-oct2026-updates](/harness/claude-code-oct2026-updates.md),
which covers v2.1.295-v2.1.318 (2026-10-08 through 2026-11-04). The v2.1.248-294
range (most of September through early October) was not independently
re-fetched from the official changelog this pass — flagged there as a
coverage gap rather than silently skipped.
