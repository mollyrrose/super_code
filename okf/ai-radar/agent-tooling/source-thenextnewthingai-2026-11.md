---
type: digest
title: 'Source digest — YouTube @TheNextNewThingAI, 2026-06-04..2026-11-02'
description: 111 videos, 204 unique GitHub repos linked in descriptions; about 10 are relevant to this setup, the rest are consumer apps, SaaS clones, star-inflated skill packs, or tools already in use.
tags: [source-digest, youtube, github-trending, skills, memory, tts, forecasting]
timestamp: 2026-11-04T00:00:00Z
resource: https://www.youtube.com/@TheNextNewThingAI
status: current
supersedes: []
adoption: awareness
---

# Summary

First pass over this channel (now a followed source in
[ROUTINE.md](/ROUTINE.md) step 1b). The channel is a weekly "top GitHub repos"
show: 111 videos in 5 months, 205 GitHub links, 204 unique repos (1 dead:
`useautumn/autumn` 404). Metadata (stars, license, top language, last commit)
was scraped from the repo pages on 2026-11-04; nothing was cloned or installed,
and **no SkillSpector scan has run on any of these yet** — every candidate
below is `unverified` until it does.

## Worth a closer look (candidates)

| repo | what | why it may matter here | lic | stars | last commit |
|------|------|------------------------|-----|-------|-------------|
| rtk-ai/rtk | CLI wrapper that compresses dev-command output for LLMs | same job as `tokenjuice.py`; worth a head-to-head on real commands | Apache-2.0 | 85.6k | 2026-11-04 |
| mksglu/context-mode | keeps tool output out of the agent context (sandboxed MCP) | addresses the "a hook cannot rewrite a tool result" limit tokenjuice documents; see [context-mode-mcp](/harness/context-mode-mcp.md) | none | 33.4k | 2026-11-04 |
| google-research/timesfm | pretrained time-series foundation model | zero-shot forecasting baseline for a time-series workload | Apache-2.0 | 35.2k | 2026-09-29 |
| TauricResearch/TradingAgents | multi-agent LLM framework for market analysis | design reference for multi-agent strategy review (algorithmic inspiration only) | Apache-2.0 | 120.6k | 2026-11-04 |
| languagetool-org/languagetool | style/grammar checker, 25+ languages, self-hostable server | automated QA pass on machine-translated content | LGPL-2.1 | 15.2k | 2026-11-04 |
| jamiepine/voicebox | local voice studio: clone, dictate, TTS | could replace several side-by-side TTS stacks with one (MIT) | MIT | 59.4k | 2026-10-07 |
| debpalash/VoiceStudio | local ElevenLabs alternative | same niche as voicebox; AGPL and a suspiciously steep star count | AGPL-3.0 | 100.7k | 2026-11-04 |
| heygen-com/hyperframes | HTML -> video renderer built for agents | alternative to an ffmpeg/Remotion render path | Apache-2.0 | 78.8k | 2026-11-04 |
| vectorize-io/hindsight | agent memory that learns from trajectories | compare against the level-5 memgraph layer (see [claude-mem](/cognition/claude-mem.md)) | MIT | 58.7k | 2026-11-04 |
| DeusData/codebase-memory-mcp | local code-intelligence graph over MCP | overlaps [graphify](/knowledge/graphify.md); awareness | MIT | 48.1k | 2026-11-03 |
| alibaba/open-code-review | hybrid static + LLM code review | compare against qRev's fleet on the same diff | Apache-2.0 | 49.4k | 2026-11-04 |

## Already in use or already tracked

affaan-m/ECC ([ecc-agent-harness](/harness/ecc-agent-harness.md)),
DietrichGebert/ponytail, ayghri/i-have-adhd, blader/humanizer,
mvanhorn/last30days-skill, Graphify-Labs/graphify, ruvnet/ruflo, morluto/rea,
headroomlabs-ai/headroom (do-not-install, see
[headroom](/agent-tooling/headroom.md)), mattpocock/skills, obra/superpowers,
cloudflare/security-audit-skill ([entry](/devsec-tools/cloudflare-security-audit-skill.md)),
thedotmack/claude-mem, max-sixty/worktrunk ([entry](/agent-tooling/worktrunk.md)),
pbakaus/impeccable ([entry](/harness/ai-design-slop-skills.md)),
volcengine/OpenViking ([entry](/knowledge/openviking.md)), apache/maka,
openai/codex ([entry](/harness/openai-codex.md)).

## Not for this setup (rejected, with the reason)

- **Free-LLM gateways** (diegosouzapw/OmniRoute, tashfeenahmed/freellmapi):
  route prompts through unknown third-party providers; exfiltration and ToS risk.
- **Token gimmicks** (teamchong/pxpipe renders text as images; ooples/token-optimizer-mcp,
  jia-gao/leanctx): either lossy or duplicating tokenjuice + condense.
- **SaaS replacements and consumer apps** (~120 repos: Nextcloud, Immich,
  Vaultwarden, Cal.diy, Twenty, PostHog, OBS, kdenlive, Penpot, AppFlowy,
  Excalidraw, Ghost, RustDesk, PS5/TV/macOS tools, finance and CRM apps):
  useful software, but nothing these projects lack.
- **Star-inflation cluster** (morluto/rea 430k, mattpocock/skills 313k,
  obra/superpowers 312k, multica-ai/andrej-karpathy-skills 229k with a
  2026-04 last commit): see
  [trending-skillpack-star-inflation-pattern](/agent-tooling/trending-skillpack-star-inflation-pattern.md).
- **OSINT / account-lookup tools** (megadose/holehe, last commit 2024;
  p1ngul1n0/blackbird): out of scope.

# Repo / source check

Channel videos and descriptions via yt-dlp; repo signals from each GitHub page,
its commits Atom feed, and shields.io language badges. No repo was cloned. Star
counts are as displayed and carry the usual inflation caveat. Next step for any
candidate is a SkillSpector scan before it is installed anywhere.

# Why this is in the radar

The user asked for this channel to be followed. The digest records what was
checked so later runs only look at videos after `last_seen`, and the candidate
rows feed `adoption-queue.md`.
