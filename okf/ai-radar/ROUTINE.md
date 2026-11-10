---
type: Runbook
title: AI Radar — routine runbook (self-updating)
description: The canonical instructions for the weekly AI Radar routine. The cloud trigger prompt only says "read this file and follow it", so the routine improves itself by editing the TUNABLE sections below.
timestamp: 2026-11-10T00:00:00Z
self_improve: on        # off = sweep + lint only (no Adopt step, no self-tuning)
max_adoptions_per_run: 2
max_stale_refresh_per_run: 8
---

# AI Radar routine

Three jobs per run, in this order: **sweep** (learn what is new), **refresh**
(re-verify what went stale), **adopt** (turn findings into real changes in this
repo). Then **self-tune** this file so the next run is better. Checking alone is
not the goal; every run should leave the repo a little better.

Run context: the cloud routine (trigger `trig_01SfqhMbYrnRqQwbk4XSQKHp`, repo
`mollyrrose/super_code`) commits and pushes; the local `/radar-scan` skill follows
the same file but stays disk-only and never pushes.

## LOCKED — guardrails (the routine must NOT edit this section)

1. **Branch rule.** Only `okf/ai-radar/**` may be committed to `main`. Every
   Adopt change outside `okf/ai-radar/` goes to its own branch
   `radar/adopt-<YYYY-MM-DD>-<slug>`, pushed as a branch, never merged. The user
   merges. (Decision-gate: merge to main is the irreversible step.)
2. **No dependency installs/upgrades without a scan.** Install SkillSpector first
   (`uv tool install git+https://github.com/NVIDIA/skillspector.git`, it is the
   bootstrap trust root) and scan any external repo before cloning or pinning it.
   Score >= 70 or any exfil/RCE finding -> `status: unverified`, no adoption.
3. **Never touch** `settings.json` hook wiring, credentials, `.env*`, the
   CONSTITUTIONAL block in any CLAUDE.md, or anything under `pentest*`.
4. **Hooks keep the silent-no-op contract.** A change to `scripts/*hook*.py` must
   run its `*_smoketest.py` and pass; failing smoketest = no push, log it.
5. **Respect the queue.** An item marked `rejected` in `adoption-queue.md` is
   never re-proposed unless its `revisit_if` condition is now met (say which).
6. **No nested fan-out.** Run topics sequentially in the main agent (or at most
   one level of subagents that do NOT spawn their own). The 2026-11-04 run hit
   "subagent nesting limit" and left half-understood checkpoint commits.
7. **Honest log.** Every run prepends one `log.md` entry including what it
   skipped, what it adopted (branch names), and every edit it made to this file.
8. **This repo is PUBLIC.** Never write private project names (other than
   `super_code`), paths, component maps, or business details into any file
   here. Per-project inventories live only in `~/.ai-radar/projects/` on the
   user's machine; the cloud sees only the anonymous `watchlist.md`.

## Step 1 — sweep

For each topic in **Seeds** (below): web search the seeds for the last ~7-14
days (widen to the gap if the previous `log.md` entry is older than 10 days),
plus github.com/trending (daily + weekly; overall, Python, TypeScript). For each
promising repo: README, last commit/release, license, stars trajectory, does
the code back the claim; SkillSpector scan if available. Distill/merge into
`okf/ai-radar/<topic>/<slug>.md` (frontmatter: `type`, `title`, `description`,
`tags`, `timestamp`, `resource`, `status`, `supersedes`, and `adoption:` one of
`candidate | awareness | algorithmic-inspiration-only | rejected`). Merge, do
not duplicate; supersede old entries explicitly.

### Step 1b — followed sources

For each row in **Sources** (below): fetch its feed (YouTube: the RSS URL via
WebFetch, no yt-dlp needed; for full descriptions use
`pip install yt-dlp` + `yt-dlp --skip-download --print description <url>` if
the sandbox allows). For every video/post since the row's `last_seen`, pull the
github.com links from the description, inspect each repo as in step 1, and
file it under the closest topic with `source: <channel>` in the body. Update
`last_seen`. A source that yields nothing adoptable 6 runs in a row: note it in
Lessons and propose dropping it (do not drop it yourself).

### Step 1c — watchlist upgrade check

Read `watchlist.md` (OSS packages / tools / model ids the user's projects run).
For each row: latest release on PyPI / npm / GitHub releases, deprecation or
retirement notices, security advisories (GitHub advisory DB / OSV). A row with
a newer major, a CVE, or a retirement date -> one `adoption-queue.md` item
(class C if it needs the user's machine) naming the package, current -> new,
and the breaking-change summary. No project names (guardrail 8).

## Step 2 — refresh (do it, don't just flag)

Lint the whole bundle mechanically:

```bash
python3 - <<'EOF'
import os, re, yaml, datetime
# parse every .md frontmatter with yaml.safe_load; report parse errors,
# orphans (not linked from any index), broken /topic/x.md links, and
# status:current entries older than the topic window in Freshness.
EOF
```

Fix YAML errors and missing index lines directly. Then actually **re-verify**
the `max_stale_refresh_per_run` oldest stale `current` entries (re-fetch the
source, update facts + timestamp, or set `superseded`/`unverified`). Report the
rest as a punch-list.

## Step 3 — adopt (skip if `self_improve: off`)

1. Read `adoption-queue.md`. Add every new `adoption: candidate` finding as a
   `proposed` item with: what to change, which file(s), class, risk,
   `revisit_if`.
2. Pick up to `max_adoptions_per_run` items, preferring `approved` > class A >
   class B, smallest first.
   - **Class A** (docs/config text inside this repo: stale model ids, wrong
     paths, outdated notes in CLAUDE.md mirrors, README facts) — implement,
     verify with grep, branch + push.
   - **Class B** (code: a new script, a hook tweak, a version pin) — implement
     with a smoketest, run it, branch + push only if green.
   - **Class C** (needs the user's machine, accounts, or a judgment call) —
     never implement; leave `proposed` with a one-line ask.
3. Update the item: `status: branch-pushed` + branch name + test result. When a
   later run sees the branch merged into `main`, set `done`; if the branch was
   deleted unmerged, set `rejected` and copy the reason if one exists.

## Step 4 — self-tune (skip if `self_improve: off`)

Edit only the TUNABLE sections below, and list each edit in the `log.md` entry:

- **Seeds:** add a seed for any repo/term that surfaced in 2+ topics this run;
  drop a seed that produced nothing useful for 3 consecutive runs (keep a
  counter in its row).
- **Sources:** update `last_seen` / `empty-runs`; add a channel or blog that
  appeared as the origin of 2+ adoptable findings this run.
- **Freshness:** adjust a topic window only with a stated reason (e.g. "8 of 10
  models entries went stale within 20 days").
- **Lessons:** add one line per new failure mode or workaround (tool blocked,
  domain unreachable, prompt ambiguity). Remove lessons that no longer apply.

## Step 5 — commit, push, report

`okf/ai-radar/**` -> one commit on `main` (`radar-scan: weekly sweep YYYY-MM-DD`),
push. Adopt branches pushed separately. Final message: per topic new/updated,
refreshed count, adopted branches, queue changes, edits to this file, lint
punch-list. Terse.

## TUNABLE — Seeds

| topic | seeds | empty-runs |
|-------|-------|-----------|
| harness | "Claude Code" changelog, new hooks/skills/MCP, agent harness update | 0 |
| models | new Claude / OpenAI / Gemini / GLM / DeepSeek model, pricing, context limit, deprecation date | 0 |
| knowledge | OKF open knowledge format, RAG vs wiki, knowledge graph for agents, graphify releases | 0 |
| cognition | agent memory consolidation ("dreaming"), episodic vs semantic memory, dual-process agents, cognitive architectures for LLMs | 0 |
| agent-tooling | multi-agent orchestration, worktree/sandbox agent runners, prompting technique | 0 |
| devsec-tools | semgrep release, SkillSpector release, supply-chain scanner, AI code security tool | 0 |

Consumers to weight findings for: (a) this repo's Claude Code setup (hooks,
skills, coord.py, memgraph level-5 memory), (b) the community knowledge base.
Weight by concrete adoptability, not hype.

## TUNABLE — Sources

| source | feed | last_seen | empty-runs |
|--------|------|-----------|-----------|
| YouTube @TheNextNewThingAI | https://www.youtube.com/feeds/videos.xml?channel_id=UCNZEktrsM5oJZ-MK4jKPMOQ | 2026-11-02 (digest: agent-tooling/source-thenextnewthingai-2026-11) | 0 |

## TUNABLE — Freshness

models 30d, harness 30d, devsec-tools 30d, knowledge 120d, cognition 120d,
agent-tooling 120d.

## TUNABLE — Lessons

- Repo moved `super_claude` -> `super_code`; push to the new remote URL.
- GitHub star counts on trending AI skill packs are often inflated; never use
  stars alone as a trust signal (see agent-tooling/trending-skillpack-star-inflation-pattern).
- havoptic.com and some third-party changelog trackers are unreachable from the
  sandbox; use code.claude.com/docs/en/changelog directly.
- Quote YAML frontmatter values that contain `"` or `:` — two entries broke
  parsing on 2026-11-04.
- 2026-11-10: youtube.com and gulfnews.com do not resolve from the sandbox (network allowlist); step 1b
  source feed could not be fetched, `last_seen` left unchanged. Allow youtube.com to fix.
- Scheduled runs 2026-09-15..2026-11-03 died in ~10s with `403
  authentication_failed` (org had disabled subscription access for Claude Code);
  if the previous `log.md` entry is >10 days old, say so first in the report.
