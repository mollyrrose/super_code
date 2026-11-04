---
type: pattern
title: Star-count / commit-depth mismatch across trending "agent skill pack" repos
description: An unusual cluster of Claude-Code/Codex "skill pack" repos continues to show six-figure stars against low-hundreds-of-commits histories and low-profile maintainers — genuine viral moment or star-gaming remains unresolved.
tags: [github-trending, skills, unverified, awareness, lint]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/trending
status: unverified
supersedes: []
---

# Summary

This week's GitHub-trending sweep surfaced an unusually consistent pattern:
several "AI agent skill" repos show very high total star counts paired with
thin commit histories and a single, low-profile maintainer —
`obra/superpowers` (283k stars / 681 commits), `mattpocock/skills` (257k
stars / 459 commits), `DietrichGebert/ponytail` (132k stars / 222 commits),
`tt-a1i/archify` (54k stars / 236 commits, anonymous author), and
`blader/humanizer` (45k stars / 75 commits) all show the same shape. Two of
these (`ponytail`, `archify`) posted the two largest single-week star gains
of anything AI-related in this sweep (+12,834 and +14,946 respectively).

**2026-11-04 re-check (~8 weeks later):** the two tracked repos kept growing
but did not blow up further relative to their own curves —
`obra/superpowers` 283k -> 312.1k stars (+29k, +10%, still 687 commits on
`main`) and `mattpocock/skills` 257k -> 312.1k stars (+55k, +21%, 553
commits) — i.e. both now show the identical 312.1k star count despite
different commit counts, which is itself worth independent verification
(coincidence, a shared counting/caching quirk in the trending-page capture,
or a real convergence). Two new repos fit the same shape and are added to
this entry rather than written up separately:
- `multica-ai/andrej-karpathy-skills` — 229.3k stars on just 28 commits (a
  single `CLAUDE.md` + a Cursor rule). The repo's own install instructions
  point to `forrestchang/andrej-karpathy-skills`, not `multica-ai` — this
  looks like an unattributed fork/mirror of another project, which is an
  additional provenance concern on top of the star-count mismatch.
- `Donchitos/Claude-Code-Game-Studios` — 35.2k stars on 43 commits (~819
  stars/commit, higher than either `superpowers` or `mattpocock/skills`).
  Fork ratio (~13%) and watcher count (238) look organic-template-shaped
  rather than obviously bot-inflated, and the code itself is real and
  functional (see its own brief entry), but the star/commit ratio puts it
  squarely in this pattern — tracked here rather than recommended.

# Repo / source check — unverified

This pattern recurs across unrelated authors, which reads either as (a) a
genuine September-2026 zeitgeist around Claude Code/Codex skill packs
pushing organic virality far beyond normal curves, or (b) coordinated
star-gaming/bot amplification of the trending algorithm. This sweep could
not resolve which — that needs a star-history.com pull or the GitHub API's
`/stargazers` timestamps, neither of which WebFetch-based trending-page
summarization can give reliably. Where an author has independent public
reputation (`obra/superpowers` — Jesse Vincent; `mattpocock/skills` — a
well-known TypeScript educator; `cathrynlavery/diagram-design` — identified
founder), the code/functionality itself looks legitimate even if the growth
curve is unconfirmed; the two most extreme mismatches
(`ponytail`, `archify`) have unknown/anonymous authors and are the ones
most worth an independent check before citing their popularity anywhere.

# Why this is in the radar

This is a lint-relevant finding about the trending-repo signal itself, not
a recommendation for or against any one of these tools: treat "trending
Claude Code skill pack" star counts as unverified until independently
confirmed, and prefer commit depth / issue engagement / author reputation
over raw star count when judging real adoption. Recorded as one entry
rather than five near-duplicate ones per the bundle's dedup convention.

# Notes

- Repos in scope: `obra/superpowers`, `mattpocock/skills`,
  `DietrichGebert/ponytail`, `tt-a1i/archify`, `blader/humanizer`,
  `cathrynlavery/diagram-design` (smaller mismatch, identified author),
  `multica-ai/andrej-karpathy-skills` (new 2026-11-04, unclear provenance),
  `Donchitos/Claude-Code-Game-Studios` (new 2026-11-04, real/functional code
  but same star-ratio shape).
- Re-check star trajectories at the next scan (ideally via the GitHub API
  rather than WebFetch) to see whether the growth curves normalize or keep
  compounding. The `superpowers`/`mattpocock/skills` identical 312.1k count
  this pass is specifically worth re-checking via the API next time, since a
  WebFetch snapshot can't rule out a capture-time artifact.
