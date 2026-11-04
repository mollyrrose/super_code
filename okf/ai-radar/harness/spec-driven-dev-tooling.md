---
type: tool
title: Spec-driven development (SDD) tooling — github/spec-kit and Fission-AI/OpenSpec
description: Two MIT-licensed toolkits that add a structured spec/proposal/design/tasks planning layer in front of AI coding agents, both trending with six-figure star counts.
tags: [spec-driven-development, github-trending, claude-code, codex, cursor]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/github/spec-kit
status: current
supersedes: []
---

# Summary

Two separate but same-shaped projects surfaced together on this sweep's
GitHub-trending Python view:

- **github/spec-kit** (official GitHub org repo) — "Toolkit to help you get
  started with SDD or any other process." Installs via `uv tool install
  specify-cli`; ships templates/commands for spec-driven development, bug
  fixing, and idea assessment. ~146.9k stars, 13.2k forks, 2,342 commits,
  92 open issues/115 open PRs. MIT.
- **Fission-AI/OpenSpec** — adds a proposal -> specs -> design -> tasks
  planning layer in front of 30+ AI coding assistants via slash commands,
  claims to be built with its own tool (repo contains its own `openspec/`
  dir). ~73.9k stars, 5.1k forks, 1,028 commits, 134 open issues/60 open PRs.
  MIT.

Both are structurally real (source/test/build dirs, CI workflow badges,
changelogs) rather than thin wrapper repos, and both sit in the same
emerging category: making an agent pause for an explicit, reviewable spec
before writing code — the same shape as this project's own `/qPlan` gate,
just as a separate open-source convention rather than a project-local skill.

# Repo / source check

Both repos' directory layout matches their README claims (spec-kit:
`src/specify_cli`, `templates`, `extensions`, `presets`; OpenSpec: `src`,
`test`, `vitest.config.ts`, changesets). Neither page exposed a last-commit
or last-release date to this fetch, so freshness/active-maintenance is
plausible (commit counts, open issue/PR volume) but not independently
timestamped this pass. Individual command behavior (e.g. spec-kit's
`/speckit-bug-assess`) was not exercised. No safety red flags found in
either README. Given the un-timestamped maintenance signal, treat the
"actively maintained" claim as **plausible, not confirmed** — re-check with
a dated commit/release fetch next sweep rather than auto-upgrading beyond
`current`.

# Why this is in the radar

Validates (via a second, independently-authored, high-star project) that
"explicit spec gate before code" is becoming a recognized pattern across
the open-source agent-tooling ecosystem, not just an Anthropic-specific or
project-local convention — useful corroboration for anyone evaluating
whether this project's own `/qPlan` step is reinventing something or
tracking an emerging norm (it's the latter, converging independently).

# Notes

- Re-check commit/release dates directly (not via trending-page summary)
  next sweep to confirm ongoing maintenance for both.
- A third related repo, JetBrains/thinkrail, ships its own "living specs"
  (`SPEC.md`) system inside an IDE rather than as a standalone CLI — see
  [jetbrains-thinkrail](/harness/jetbrains-thinkrail.md).
