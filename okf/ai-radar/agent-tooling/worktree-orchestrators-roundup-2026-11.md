---
type: pattern
title: "Worktree-per-agent orchestrators roundup (Nov 2026)"
description: "Orkestra, Daintree, SwarmGit, Baton, microsoft/conductor: all isolate agents in git worktrees; none scanned."
tags: [orchestration, worktree]
timestamp: 2026-11-10T00:00:00Z
resource: https://www.augmentcode.com/tools/open-source-agent-orchestrators
status: unverified
adoption: awareness
---

Search-only findings, no dates, no SkillSpector scan. Same pattern as this repo's `.worktrees/` + coord.py
approach; Baton notes worktree isolation does not prevent collisions on shared services. Nothing to adopt.
