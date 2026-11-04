---
type: Log
title: AI Radar — ingest log
description: Append-only timeline of ingests and changes to the AI Radar bundle.
timestamp: 2026-06-28T00:00:00Z
---

# Ingest log

Newest first. Each line: date — what changed.

- 2026-11-04 (interactive, 2) — Added followed sources (ROUTINE.md step 1b; first: YouTube @TheNextNewThingAI via RSS), an anonymous dependency `watchlist.md` (step 1c upgrade/CVE/retirement checks), guardrail 8 (public repo, no project names), and qClose step 5b (feature log -> private `~/.ai-radar/projects/`, anonymised -> watchlist). Channel backfill: 111 videos (2026-06-04..11-02), 204 repos -> agent-tooling/source-thenextnewthingai-2026-11 (11 candidates, all unverified until SkillSpector-scanned); 6 class C items added to adoption-queue.
- 2026-11-04 (interactive) — Routine upgraded from check-only to sweep -> refresh -> adopt -> self-tune. Added `ROUTINE.md` (self-updating runbook, LOCKED guardrails + TUNABLE seeds/freshness/lessons) and `adoption-queue.md` (7 items: 2 done, 3 proposed, 2 rejected). Trigger prompt now just points at ROUTINE.md; trigger repo URL fixed to super_code. Root cause of the 57-day gap: 8 scheduled runs (2026-09-15..11-03) died with 403 authentication_failed.
- 2026-11-04 — Weekly sweep (cloud sandbox), all 6 topics + GitHub trending
  (6 views: daily/weekly x overall/Python/TypeScript, all reachable). **Gap
  note:** the prior sweep was 2026-09-08 — a ~57-day gap rather than the
  intended weekly cadence (the scheduled task evidently did not fire, or
  this is the first run since; not investigated further here, flagged for
  the user). Given the gap, topics were researched somewhat more broadly
  than the usual 7-14-day window. **Execution note:** this run's background
  sub-agent fan-out behaved unusually — attempts to launch six parallel
  per-topic agents via the Agent tool mostly returned "subagent nesting
  limit reached" errors to the calling turn, yet harness/models/
  agent-tooling/devsec-tools/cognition and then knowledge were in fact
  completed and committed as two intermediate checkpoints
  (`8fa970b`, `83e3902`) by what must have been background execution that
  continued despite the reported errors; the final pass (this entry) picked
  up from those checkpoints, ran its own additional check on the models
  topic, and did the cross-topic lint + this log/index refresh. Net result
  is a complete sweep, but the orchestration layer's behavior here was not
  fully understood and is worth the user's attention if it recurs.
  21 new entries, 15 existing entries refreshed/merged, 1 open question
  resolved (Sonnet/Haiku 5.5), 18 stale `current` entries flagged (not
  auto-changed).
  **models** (5 new): claude-opus-5-5 (current flagship, supersedes
  opus-5), claude-sonnet-5-5 (current mid-tier, supersedes sonnet-5 — note:
  this session's own configured model is `claude-sonnet-5`, one tier behind
  this radar's current pick), claude-haiku-5-5 (unverified ship date),
  deepseek-v4-1-flash (supersedes v4-pro, unverified); refreshed
  claude-fable-mythos-5-1 (cross-checked against the opus-5-5 announcement's
  own Fable-5.1 comparison), gemini-3-7-flash, glm-5-3, grok-4-6 (all
  re-checked, still current); marked claude-opus-5 and claude-sonnet-5
  `superseded` with explicit notes.
  **harness** (4 new): claude-code-oct2026-updates (v2.1.295-2.1.318,
  supersedes claude-code-aug2026-updates — the v2.1.248-294 range,
  September through early October, was NOT independently re-fetched and is
  logged as a coverage gap, not silently skipped), jetbrains-thinkrail
  (competing "vibe coding" IDE), spec-driven-dev-tooling (github/spec-kit
  vs. Fission-AI/OpenSpec), ai-design-slop-skills (Nutlope/hallmark +
  pbakaus/impeccable); refreshed ecc-agent-harness (v2.2.3, star count
  254k->296.8k, still unverified/inflated-pattern).
  **knowledge** (1 new): graphify (Graphify-Labs/graphify — confirmed as
  the upstream of this project's own `graphifyy` PyPI dependency via the
  PyPI project page's listed Source URL; claimed ~142k stars flagged
  unverified given inconsistent secondary-source star counts over time and
  an SEO-content-mill pattern in surrounding coverage; separately flagged a
  real supply-chain gap — the manually-audited 0.8.x `graphifyy` line is
  now ~100 point releases behind the shipped 0.9.102).
  **cognition** (2 new): mempalace (local-first verbatim memory + temporal
  graph, unverified), dreaming-consolidation-research-2026 (Auto-Dreamer +
  Active Dreaming Memory consolidation proposals, plus a counter-evidence
  paper arguing against in-place memory rewriting — read as validating this
  project's own non-destructive `memgraph-ingest` design); upgraded
  claude-mem from `unverified` to `current` (star count now corroborated
  across 4 independent trending views rather than one anomalous reading);
  extended dual-process-graph-memory-research-2026 with two more papers
  (BMAM, D-Mem).
  **agent-tooling** (7 new): astrbot, claude-code-game-studios (compared
  against this project's own coord.py), microsoft-agent-framework,
  sandcastle, treg, vercel-agent-desktop, worktrunk; extended
  trending-skillpack-star-inflation-pattern with two more repos
  (andrej-karpathy-skills — unattributed fork/mirror, additional provenance
  concern; claude-code-game-studios) and flagged that obra/superpowers and
  mattpocock/skills now show an identical 312.1k star count despite
  different commit depths, worth an API-level re-check next time.
  **devsec-tools** (3 new): skillspector-nvidia (NVIDIA's AI-agent-skill
  security scanner — directly relevant to this project's own
  "skillspector"/"skillspector-gate" references; see that entry for the
  exact relationship finding), shannon-ai-pentester, aisoc; added
  cloudflare-security-audit-skill (official Cloudflare repo); refreshed
  hexstrike-ai and appsec-toolchain.
  **Lint pass:** 0 orphans (every entry linked from its own topic index,
  verified mechanically); 1 broken cross-link found, same pre-existing
  illustrative example in README.md as every prior sweep (`/tables/customers.md`,
  not a real entry, left as-is); 0 new contradictions found. Resolved one
  open question flagged by the models topic itself (Sonnet 5.5 / Haiku 5.5
  existence) via a follow-up search. **Staleness, flagged but not
  auto-edited** (a content refresh is a judgment call, not a mechanical
  lint fix — per this bundle's own "report anything judgmental instead of
  auto-changing it" rule): past the harness/models ~30-day window and still
  `current` — harness/apache-maka, claude-code-skill-doctor,
  context-mode-mcp, cursor-self-hosted-machines, deepseek-harness,
  mcp-2026-07-28-spec, openai-codex, claude-plugins-marketplace;
  models/gpt-6-astra, k2-horizon-mova-36b-a4b, marin; past the
  devsec-tools ~30-day convention (from prior sweeps, not explicit in this
  run's instructions) — ai-infra-guard, deepteam-redteam, mcp-scanner-cisco,
  snyk-agent-scan; past the knowledge/cognition/agent-tooling ~120-day
  window — knowledge/llm-wiki-compounding, attention-residuals,
  continuous-learning-loop, prompt-caching, agent-tooling/headroom (all
  from the 2026-06-28/29 bundle-creation batch, now ~128-129 days old).
  **Deferred/skipped, stated honestly**: no YouTube or arXiv-API tooling
  available in this sandbox (same limitation as every prior sweep); did not
  independently re-fetch the full official Claude Code changelog for the
  September-early-October gap (logged above as a coverage gap under
  claude-code-oct2026-updates); did not deep-dive several smaller trending
  repos noted in passing (CopilotKit/OpenBot cluster, milind-soni/OpenMausBot,
  nightly-labs/openbot, lfnovo/open-notebook, JustVugg/colibri,
  shiyu-coder/Kronos, karpathy/nanochat, mattpocock/sandcastle's broader
  "sandboxed agent orchestration" competitors) — judged lower-priority or
  off-focus given the backlog from the 57-day gap, not silently dropped;
  did not independently reproduce any vendor-reported benchmark number cited
  in any entry above; did not resolve whether the unusual background-agent
  orchestration behavior this sweep (see Execution note above) is a
  one-off or will recur.
- 2026-09-08 — Weekly sweep, all 6 topics + GitHub trending (daily/weekly,
  overall + Python + TypeScript views), run as an isolated cloud sandbox
  session (no local disk persists, so this sweep commits+pushes directly,
  unlike the local variant which stays disk-only). 21 new entries, 18
  existing entries refreshed/merged with new detail, 0 lint issues found
  after fixes.
  **models** (6 new): gpt-6-astra (supersedes gpt-5-6, OpenAI's new
  flagship), claude-fable-mythos-5-1 (Anthropic's separate frontier tier
  above Opus, resolved against claude-opus-5's existing "approaching Fable"
  language rather than treated as a lineage conflict), grok-4-6 (first xAI
  entry), meta-muse-glimmer (first Meta entry, unverified), deepseek-v4-pro
  (first DeepSeek model entry, unverified); merged GLM-5.3-Flash detail into
  the existing glm-5-3 entry instead of duplicating (it was already
  flagged there last scan).
  **cognition** (5 new): memory-portability-model-upgrade-2026 (controlled
  study validating this project's own graph-over-notes memory design),
  timem-temporal-hierarchical-memory (5-level memory tree, ACL 2026
  Findings), zenbrain-7layer-memory, lycheememory-v2-segment-consolidation,
  portable-agent-memory-protocol (all three unverified/small-install-base);
  refreshed hermes-agent-nousresearch's previously-flagged "implausible"
  star count — now corroborated by a second independent sweep.
  **knowledge** (1 new): maximem-synap (unverified vendor benchmark, same
  pattern as mem0-agent-memory-benchmark-2026); merged updates into
  open-knowledge-format (spec moved to its own repo, first third-party
  tooling), cognee (5 point releases), graphiti-zep (v0.30.1).
  **agent-tooling** (5 new): openclaw (389k-star harness, repositioning as
  enterprise infra), hydrafusion (GitHub Copilot CLI's multi-model
  orchestrator, unverified), aden-hive (self-organizing agent topology,
  unverified), ruflo-swarm-harness (already installed in this project,
  corroborated), trending-skillpack-star-inflation-pattern (one
  consolidated caution entry covering 5-6 trending "skill pack" repos with
  suspect star-to-commit ratios, rather than 5 separate unverified stubs).
  **devsec-tools** (3 new): api-relay-audit, malskanner (both unverified),
  deepteam-redteam (current, fills the red-team/attack-simulation gap next
  to the existing scanners); re-verified and refreshed mcp-scanner-cisco,
  snyk-agent-scan, ai-infra-guard (v4.5.2/v4.6.0), npm-shai-hulud-scanner
  (unchanged), hexstrike-ai (grown to 11.6k stars), appsec-toolchain
  (partial re-verification, no canonical single URL to check against).
  **harness** (4 new): claude-code-skill-doctor, cursor-self-hosted-machines,
  context-mode-mcp, ecc-agent-harness (the ECC plugin already installed in
  this project — functionality corroborated, star count unverified); merged
  updates into claude-code-aug2026-updates (new hook events,
  managedMcpServers), openai-codex (GPT-6 Astra default), deepseek-harness
  (216k stars, self-disclosed audit gap), apache-maka (still no ASF
  release), mcp-2026-07-28-spec (2026-08-22 roadmap).
  **Lint pass**: checked all 74 internal cross-links (0 broken beyond one
  pre-existing illustrative example in README.md), checked all new entries
  for orphan status (0 found — each linked from its topic index), checked
  frontmatter (`type` present in all 65 non-reserved files; `status` values
  all one of current/superseded/unverified), checked freshness windows (no
  `current` entry past its topic's staleness window found this pass beyond
  what was already re-verified above).
  **Deferred/skipped, stated honestly**: no YouTube or arXiv-API tooling was
  available in this sandbox (WebFetch to arxiv.org and huggingface.co was
  blocked by the egress proxy across multiple research passes — cognition
  and knowledge findings above were reconstructed from search-engine
  snippets, not primary PDF/HTML text, where noted in-entry); several
  official first-party sources were also egress-blocked this pass
  (anthropic.com, openai.com/developers.openai.com, mem0.ai, maximem.ai,
  geminicli.com, github.blog, venturebeat.com, infoq.com, marktechpost.com,
  news.ycombinator.com) — those entries rely on independent secondary-source
  corroboration instead and are marked accordingly; did not deep-dive
  several lower-priority trending repos (MagiCrew, several "diagram
  generation skill" repos, sglang, timesfm, heretic) — logged in the
  trending research but not written up as bundle entries this pass; did not
  independently reproduce any vendor-reported benchmark number cited above.
- 2026-09-08 — Added models/k2-horizon-mova-36b-a4b (EVALUATED-not-adopted).
  Question asked: is its speed - not its knowledge - useful anywhere here?
  No. Speed claim has zero published measurement; the model is reachable only
  via the qPlan OpenAI-compatible critic slots (where latency is irrelevant and
  a strong different-family model is wanted instead), and unreachable in the
  latency-dominated Task fleets (qRev, focus-group) which are bound to the
  session provider. Even via a translating proxy it would be slower (weak
  tool-calling trips qRev's failed-dispatch tripwire) and costlier
  (subscription -> metered). Filter recorded for any future test: separate
  model speed from host speed (Cerebras).

- 2026-08-27 (part 2) — Follow-up sweep: the routine's own prompt was updated
  (`qRem` step 8, after part 1 below already ran) to add a **cognition**
  topic and a GitHub-trending step; this pass covers exactly that delta
  rather than re-sweeping the 5 topics already done today. **cognition**
  (new topic, 8 entries): added memanto (typed semantic memory, ships Claude
  Code integration — strongest personal-memory-layer match), hermes-agent
  (NousResearch; naming collision flagged against this repo's own
  hermes-agent/ dir, worth a side-by-side comparison), talker-reasoner
  (foundational DeepMind dual-process paper), dual-process-graph-memory-
  research-2026 (DCPM/SYNAPSE/MAGMA academic cluster, algorithmic-inspiration
  only), letta-sleep-time-compute (MemGPT lineage, conceptual-only pending a
  letta-code repo check), claude-mem and agentmemory (both GitHub-trending
  Claude Code memory tools — claude-mem's star count looks like a scraping
  artifact so marked `unverified`; agentmemory's repo is real but its
  benchmark/cost claims are self-reported, marked awareness-only), and
  claude-obsidian (Obsidian+Claude Code PKM, reference-only). Cross-linked
  rather than duplicated: knowledge/anthropic-dreaming-memory,
  knowledge/graphiti-zep, knowledge/cognee (all merged in newly-found detail
  — bi-temporal edges for Graphiti, ECL pipeline for Cognee — and refreshed
  timestamps). **GitHub trending sweep** (6 views: daily/weekly x
  overall/Python/TypeScript, all reachable, no proxy block): added
  harness/openai-codex (competing harness, largest weekly star gain of the
  whole sweep), harness/claude-plugins-marketplace (Anthropic's own official
  + community plugin repos), harness/apache-maka (Apache Incubator, no
  release yet), knowledge/openviking (Volcengine context DB, vendor-reported
  benchmarks), agent-tooling/deepagents, agent-tooling/browser-harness,
  agent-tooling/scientific-agent-skills, models/marin (Stanford CRFM
  training platform; not applicable here), devsec-tools/ai-infra-guard
  (Tencent red-team platform — best-verified trending finding this week:
  dated release, named org). Lint pass: no new contradictions or orphans;
  the two already-flagged stale devsec-tools entries (appsec-toolchain,
  hexstrike-ai, ~60 days old) are unchanged, no new staleness introduced
  (every touched/added entry timestamped today). Deferred: several smaller
  trending repos noted by the research agent but not deep-dived
  (wshobson/agents, nodeterm, open-slide, context-engineering-kit,
  context-mode, BrowserSkill, OmniRoute, freellmapi, lfnovo/open-notebook,
  and a cluster of AI-job-search/trading-bot repos judged thematically
  off-focus); tinyhumansai/openhuman flagged as currently trending (+1,818
  stars/week) given this repo's own CLAUDE.md cites it as tokenjuice prior
  art, but not deep-fetched this pass — worth a dedicated look next scan.
  memory-v3-opencode (MAGMA/ACT-R synthesis fork) reviewed but not entered:
  0 stars, single-maintainer fork of another unverified project, too thin a
  signal for a dedicated entry.
- 2026-08-27 — Weekly radar-scan (cloud sandbox, 5 parallel research agents,
  one per topic). **harness**: added claude-code-aug2026-updates (subagent
  forking on by default + cross-session messaging + rolling MCP/hook
  reliability pass v2.1.232-2.1.247 + SendFeedback tool), deepseek-harness
  (competing plugin-only agent harness, awareness), mcp-2026-07-28-spec
  (MCP "stateless core" revision). **models**: claude-opus-4-8 marked
  superseded — Claude Opus 5 shipped 2026-07-24 and is the current flagship;
  added claude-opus-5, claude-sonnet-5 (permanent $2/$10 pricing as of
  2026-08-10), glm-5-3, gemini-3-7-flash, gpt-5-6 (first GPT/Gemini/GLM
  entries in the bundle). **knowledge**: open-knowledge-format updated to
  note OKF v0.2 (2026-07-25, two breaking field renames, not auto-migrated
  here); added anthropic-dreaming-memory (first-party validation of
  continuous-learning-loop's direction), gbrain (production-scale
  compounding-wiki reference impl), graphiti-zep, cognee (knowledge-graph
  memory cluster), mem0-agent-memory-benchmark-2026 (unverified — primary
  source blocked by sandbox egress proxy). **agent-tooling**: added
  agent-lightning (Microsoft RL training framework; not-applicable, no
  training loop here) and nooa (NVIDIA object-oriented agents; promising but
  pre-1.0 research-alpha, no scanner available to verify sandboxing safety).
  **devsec-tools**: added mcp-scanner-cisco and snyk-agent-scan (both
  awareness-candidate defensive MCP/skill scanners) and
  npm-shai-hulud-scanner (unverified, do-not-recommend — 15 stars/4
  forks/13 commits, flagged pending proper review). Lint pass: no
  contradictions found; flagged appsec-toolchain and hexstrike-ai as ~60
  days old against devsec-tools' ~30-day freshness window (re-verification
  noted, status unchanged, judgmental call left unmade); added missing
  cross-links (continuous-learning-loop <-> anthropic-dreaming-memory,
  llm-wiki-compounding <-> gbrain); no orphans after refreshing all 5 topic
  indexes + top-level index. Coverage gaps (be honest): no YouTube/arXiv
  tooling available in this sandbox (two arXiv agent-memory/agent-tooling
  papers noted by a research agent were not turned into entries — no repo,
  abstract-only, deferred); several primary sources were blocked by the
  sandbox's network egress proxy (claude.com, docs.anthropic.com,
  marktechpost.com, mem0.ai, arxiv.org, ai.google.dev direct-fetch) — those
  findings are corroborated via independent WebSearch-aggregated sources
  instead of a single primary fetch, and are flagged as such in each entry;
  two devsec-tools MCP-scanner candidates (getjavelin/ramparts, "ScanMCP")
  were surfaced but not repo-checked, deferred to next scan.
- 2026-07-02 — Headroom follow-through: synced the 2026-06-29 manual-audit text
  from the live copy into the repo entry (agent-tooling/headroom), then ported
  the audited compression logic into `scripts/tokenjuice_condense.py`
  (stdlib-only; JSON schema preservation, code signature fallback, log
  error/trace selection, entropy secret preservation, fallback detector) and
  wired it into tokenjuice as the `condense` strategy + `--condense` flag.
  Package itself stays do-not-install (proxy/plugin/daemon layer rejected).
- 2026-06-29 — Token/memory-optimization assessment: added knowledge/prompt-caching
  (narrow applicability — harness already caches the main session; our critic prefix
  is sub-minimum), knowledge/attention-residuals (model-architecture, not-applicable),
  knowledge/continuous-learning-loop (Sona/RuVector — validates direction, no build),
  agent-tooling/headroom (context compressor; skillspector BLOCKED score 100,
  do-not-install — manual file-by-file audit deferred per context). Finding: qRev
  fleet has no per-lens model tiering (all judgment reviewers at session model).
- 2026-06-28 — Added devsec-tools/hexstrike-ai (awareness entry, do-not-auto-recommend):
  offensive MCP pentest framework. Decision: NOT wired into qRev (wrong layer +
  autonomy/safety mismatch); awareness via radar + a separate gated `/pentest-hexstrike`
  skill instead. Re-applied the qRev "Radar gate" section (a prior Write had failed).
- 2026-06-28 — Phase 2: added `/radar-scan` (web + YouTube keyword-search &
  transcript + arXiv multi-modal sweep) and the lint pass (contradictions, stale,
  orphans, missing links). Installed `youtube-transcript-api`; yt-dlp keyword
  search verified working. GitHub-repo inspection (skillspector-gated) applies to
  scan findings too.
- 2026-06-28 — Bundle created (phase 1). Seeded: models/claude-opus-4-8,
  knowledge/open-knowledge-format, knowledge/llm-wiki-compounding. Added topic
  indexes for harness, models, knowledge, agent-tooling, devsec-tools. Intake
  rule added: always inspect the real GitHub repo (skillspector-gated) before
  trusting a new thing.
