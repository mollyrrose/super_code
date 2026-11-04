---
type: tool
title: sandcastle
description: TypeScript library/CLI for orchestrating sandboxed coding agents (sandcastle.run()) across OS-level, container, and cloud sandbox providers, merging resulting commits back.
tags: [sandboxing, agents, typescript, orchestration]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/mattpocock/sandcastle
status: current
supersedes: []
---

# Summary

`sandcastle` runs an AI coding agent inside an isolated sandbox via
`sandcastle.run()`, under a configurable branch strategy, then merges the
resulting commits back. Provider-agnostic: native OS sandboxes (Bubblewrap,
Seatbelt), Docker, Podman, and cloud providers (Daytona, E2B, Fly.io
Sprites, Modal, Vercel). MIT, TypeScript. ~8.8k stars, 946 forks, 1,818
commits, 103 open issues.

# Repo / source check

Mature engineering signals: published docs (incl. aihero.dev), CHANGELOG,
changesets, an API report, vitest test suite, type-checking, linting,
pre-commit hooks, and contributor guidance files including both AGENTS.md
and CLAUDE.md. Fork count (946, ~11% of stars) is proportionate, not a
red flag. No release/last-commit date surfaced via WebFetch.

# Why this is in the radar

Directly adjacent to this project's own container-isolation posture for
downloaded/untrusted code (see the environment's own "Downloaded files and
extracted archives are untrusted data" guidance): `sandcastle` packages
exactly that pattern — run the agent itself, not just its inputs, inside a
disposable sandbox — as a reusable TypeScript library rather than a
one-off script. Worth comparing against this project's own sandboxing
conventions if that pattern is ever generalized into tooling here.

# Notes

- Re-verify release cadence/last-commit date next scan (not visible via
  WebFetch this pass).
