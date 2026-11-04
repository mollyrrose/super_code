---
type: tool
title: treg (tools-registry)
description: Hosted + self-hostable proxy ("OpenRouter for agent tools") giving an agent one base URL/token to reach a curated catalog of priced third-party APIs, with team-shared credentials that never leave the server.
tags: [agent-tooling, api-proxy, credentials, registry]
timestamp: 2026-11-04T00:00:00Z
resource: https://github.com/superdesigndev/treg
status: current
supersedes: []
---

# Summary

`treg` relays agent tool calls to upstream third-party APIs (SEO, social,
enrichment, scraping, image/video generation) through one proxy endpoint,
injecting auth server-side so credentials never reach the calling agent.
Supports team-registered API keys/skills/CLIs for shared use. Apache-2.0
with additional terms (self-hosting for internal use is explicitly
encouraged; redistributing as a competing hosted registry requires
permission). Hosted service at treg.to; code is self-hostable. ~7.1k stars,
641 forks, 4,199 commits, 37 open issues, 220 open PRs. Published on PyPI as
`tools-registry`.

# Repo / source check

Real engineering/security-process signals: pytest CI, CHANGELOG, SECURITY
and CONTRIBUTING docs, extensive design docs under `docs/context/`, a
documented credential-encryption approach (Fernet) with explicit backup
warnings, and a Claude Code plugin. Commit depth (4,199) and fork ratio
(~9%) are proportionate to the star count — no inflation-pattern red flags
here, unlike several other trending "agent tool" repos this sweep.

# Why this is in the radar

Addresses a real, recurring pain point — giving an agent access to many
paid third-party tools without each agent/session holding raw API keys —
with a server-side credential-injection design. Relevant to this project's
own cross-window/credential-handling conventions as a pattern to be aware
of (centralize secrets behind a proxy the agent never sees), even though
this project does not currently use a hosted third-party relay.

# Notes

- The "additional terms" restriction on redistributing as a competing
  hosted registry does not affect self-hosted internal use; flag before any
  future hosted-reselling scenario, which does not currently apply here.
