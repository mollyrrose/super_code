# AI Radar — an OKF knowledge bundle

A compounding, agent-maintained knowledge base of "what is new / what is better"
in the AI world. It follows the Open Knowledge Format (OKF v0.1): a directory of
markdown files with YAML frontmatter, no schema registry, no required tooling.
If you can `cat` a file you can read it; if you can `git clone` you can ship it.

Source of truth: this repo (`okf/ai-radar/`). Live copy synced to
`~/.claude/okf/ai-radar/` so skills can read it from any project.

## Why it exists

1. Learn new things from the AI world (tools, techniques, models, patterns) into
   a wiki that *compounds* instead of re-deriving on every query (the
   Karpathy/llm-wiki pattern, not static RAG).
2. Speak up: when project work touches something the radar marks as
   `superseded`, the `/qRem` and `/qRev` gates surface a single high-signal line
   ("you use X; Y is now better/safer, because Z — see resource").

## Layout

```
ai-radar/
  index.md            # catalog (OKF reserved)
  log.md              # append-only ingest timeline (OKF reserved)
  ROUTINE.md          # routine runbook: sweep, refresh, adopt, self-tune
  adoption-queue.md   # findings -> repo changes, with approve/reject status
  watchlist.md        # anonymous list of deps/models the projects run (upgrade checks)
  harness/            # Claude Code / hook / skill / MCP capabilities
  models/             # Claude / OpenAI / GLM releases, price, limits, capability
  knowledge/          # RAG, OKF, knowledge-graph, agent-memory patterns
  agent-tooling/      # autonomous frameworks, orchestration, prompting
  devsec-tools/       # linters, scanners, supply-chain
```

## Entry frontmatter (OKF + two custom fields)

```yaml
---
type: tool | technique | model | pattern   # OKF-required (non-empty)
title: ...
description: one sentence
tags: [...]
timestamp: 2026-06-28T00:00:00Z            # freshness (ISO 8601)
resource: <source URL>                      # citation, anti-hallucination
status: current | superseded                # custom: is this still preferred?
supersedes: [models/old-thing]              # custom: what this replaces -> drives "speak up"
---
```

Body favors structural markdown (headings, tables, lists, fenced code) over prose.
Cross-link with bundle-relative paths, e.g. `[customers](/tables/customers.md)`.

## How knowledge gets in (hybrid)

- Manual: `/radar-add <url | note>` — distill a source into an entry, merge into
  existing entries (no duplicates), append to `log.md`.
- Weekly auto: `/radar-scan [topic]` — multi-modal sweep across the 5 topics:
  - **Web** (WebSearch / `deep-research` / `hermes-blogwatcher`),
  - **YouTube** — keyword search (`yt-dlp "ytsearchN:<phrase>"`) + read the video
    transcript (`hermes-youtube-content` helper, yt-dlp auto-subs fallback),
  - **arXiv** (`hermes-arxiv`) for knowledge / agent-tooling.
  Then distill/merge entries and run a **lint pass** (contradictions, stale,
  orphans, missing cross-links). Scheduled weekly in phase 4; runnable by hand now.

### Always inspect the real GitHub repo (grounding rule)

For any interesting-sounding new thing that HAS a code repo, intake MUST look at
the actual GitHub repository — not just the blog post / announcement / hype — and
base its `description`, `status`, `supersedes`, and any recommendation on what the
repo actually shows. Concretely, before trusting and ingesting a repo:

1. Run the `skillspector-gate` scan first (standing rule in `~/.claude/CLAUDE.md`:
   scan GitHub code before downloading/trusting it). Verdict policy applies —
   block + ask on high score or any likely-malicious finding.
2. Read the repo's real signals: README, last-commit / release date (is it
   alive?), open-issue and star trajectory, license, language, and whether the
   code backs the claims. URL-form scan (`skillspector scan "<git-url>"`) inspects
   WITHOUT cloning into the tree.
3. Record in the entry: `resource` = the repo URL, plus a short "repo check" note
   (alive? license? does the code match the claim?). If the repo contradicts the
   marketing, say so in the entry — that contradiction IS the useful signal.

An entry whose claim is not backed by a real, inspected repo is marked
`status: unverified` and never drives a "speak up" at the gates.

## Kill switches

- `AI_RADAR_DISABLE=1` — silences the gate "speak up" in `/qRem` and `/qRev`.
- The manual `/radar-add` and `/radar-scan` are opt-in by nature.
- Delete `okf/` (and `~/.claude/okf/`) to remove the whole capability; nothing
  else depends on it.

## Conformance note (OKF v0.1)

Consumers MUST tolerate: missing optional fields, unknown `type` values, broken
cross-links. The only hard requirement is parseable frontmatter with a non-empty
`type` in every non-reserved `.md` file.
