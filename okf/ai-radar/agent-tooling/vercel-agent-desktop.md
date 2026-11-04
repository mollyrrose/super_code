---
type: tool
title: Vercel Labs agent-desktop
description: CLI/library giving AI agents desktop computer-use via the OS accessibility tree instead of screenshots/pixel matching.
tags: [computer-use, agents, vercel, accessibility, rust]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/vercel-labs/agent-desktop
status: current
supersedes: []
---

# Summary

`agent-desktop` (Vercel Labs) reads the OS accessibility tree (AX API on
macOS, UI Automation on Windows, AT-SPI on Linux) and returns JSON with a
stable `ref` per actionable element plus `available_actions`. An agent acts
on a `ref`, re-observes to verify, and repeats — no screenshots or pixel
matching in the core loop. The model/agent logic lives in the caller, not in
this tool. ~14.0k stars, 954 forks, 58 open issues, 96 open PRs.

# Repo / source check

Apache-2.0, 328 commits. Real maturity signals: code of conduct,
contributing guide, security policy, changelog, GitHub Actions CI, gitleaks
+ clippy + cargo-deny, and distribution via npm/Homebrew/native archives
plus a versioned (v2.6) JSON output envelope. Carries an explicit
"LABS-PRODUCT" badge (not yet GA) and 4 of ~60 commands are currently
non-functional; no independent benchmarks published despite a `benchmarks/`
folder existing. The core "no screenshots" claim is accurate for the
documented loop (a separate `screenshot` command exists as a fallback, not a
contradiction). Code backs the claim.

# Why this is in the radar

Direct alternative to screenshot/pixel-based computer-use (the approach this
project's own computer-use tooling and skills assume) — accessibility-tree
based control is cheaper per-turn (no vision tokens) and more robust to
theme/resolution changes, at the cost of depending on each target app's
accessibility support quality, which the repo does not itself address.
Backed by Vercel, a credible maintainer with ongoing investment likely.

# Notes

- Re-check at next scan for a stable (non-LABS) release and for whether the
  4 broken input commands are fixed.
