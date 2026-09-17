---
type: tool
title: Headroom (context compressor)
description: Local LLM-context compressor — same niche as our tokenjuice, far more capable. Manual source audit (2026-06-29) found NO malware; stays do-not-install because it MITMs the session + self-rewrites the hook/config layer this setup owns.
tags: [tokens, compression, context, cost, tokenjuice, blocked, audited]
timestamp: 2026-06-29T00:00:00Z
resource: https://github.com/chopratejas/headroom
status: current
supersedes: []
adoption: AUDITED-CLEAN-but-do-not-install (architecturally invasive to our harness; use only the isolated library API if ever wanted)
destructive: no
---

# Summary

Compresses LLM context (tool outputs, logs, files, RAG chunks, history) BEFORE it
reaches the model — claims 60-95% fewer tokens, "same answers". Apache 2.0, very
active (53k+ stars, releases through 2026-06). Algorithms: SmartCrusher (JSON),
CodeCompressor (AST), Kompress (trained prose model), CacheAligner (KV-cache prefix
stabilization), CCR (reversible — stores originals, LLM calls `headroom_retrieve`).
Modes: library `compress(messages)`, proxy, CLI wrapper, MCP server. Same niche as
our `scripts/tokenjuice.py`, much more capable.

# Repo / source check — skillspector BLOCKED, then manual audit (2026-06-29)

`skillspector` scan-before-trust verdict was **score 100, severity CRITICAL,
DO_NOT_INSTALL** (1135 issues, mostly MEDIUM). That auto-blocked it. The deferred
follow-up — a manual file-by-file source audit — was then DONE: shallow-cloned the
repo (source only, no `pip install`, nothing executed) into a gitignored scratch
dir and read the trust-sensitive surfaces. Repo is large and multi-language (1015
.py, 179 .rs, 92 .ts; Rust crates + Python pkg + TS SDK + Docker + SBOM +
`.gitleaks.toml` + `.gitguardian.yaml` + `SECURITY.md` + `deny.toml`).

## Audit result: NO malware indicators

The score-100 is consistent with FALSE POSITIVES from a legitimate but
system-level-heavy project, exactly as the original caveat predicted:

- **Install-time execution**: no `setup.py`. Build backend is `maturin` (standard
  Rust+Python). The one `build.rs` (`crates/headroom-py`) is a documented glibc
  compat shim for manylinux wheels (issue refs in comments). Only `postinstall` is
  `docs/package.json` -> `fumadocs-mdx` (docs build). No malicious install hook.
- **Network**: every destination is localhost (`127.0.0.1` proxy) or a NAMED,
  expected endpoint — GitHub Copilot auth (`api.githubcopilot.com`,
  `api.github.com/copilot_internal`), GitHub releases for prebuilt binaries
  (`binaries.py`, mirror-overridable), Gemini/OpenAI-Codex/Qdrant provider URLs
  routed by the multi-provider proxy. No unexplained C2/exfil host.
- **Secrets**: credential reads are scoped to **GitHub Copilot OAuth tokens** only
  (macOS keychain / Windows CredEnumerate / Linux secret-tool / `~/.copilot`), to
  auth as the user to Copilot for the proxy. NO `~/.ssh`/`id_rsa`/AWS/browser-cookie
  harvesting, no full-environment dumps (all `os.environ.get` are named config vars).
- **Obfuscation**: `exec/eval/compile` hits are in tests and the AST `code_compressor`
  (expected for a code compressor). No base64-decode-then-exec, marshal/pickle from
  network, etc.
- **Telemetry**: OFF by default, opt-in; `beacon.py` states "Nothing is sent to
  Headroom Labs" (local in-process collector + `/stats`). The only external POST is
  the commercial **LicenseReporter** (runs ONLY with a `license_key` set) to
  `https://app.headroomlabs.ai/v1/license/{validate,usage}` carrying a license key +
  AGGREGATE COUNTS ONLY (requests, token totals, model names) — no prompt/response/
  file content. Standard SaaS metering, not covert exfil.

## Why it STAYS do-not-install on this host (reason shifted, verdict held)

Not "unknown danger" anymore — "audited clean, but architecturally invasive to OUR
exact harness." `headroom init` (which the bundled Claude Code plugin's SessionStart
+ PreToolUse(Bash|PowerShell) hook calls via `headroom init hook ensure`):
1. starts a **persistent detached background daemon** (`start_detached_agent`);
2. rewrites **`ANTHROPIC_BASE_URL`** (and openai/codex base URLs) to `127.0.0.1:<port>`
   so ALL our LLM traffic flows through its local proxy — the MITM-in-the-critical-path
   already flagged;
3. **self-installs hooks into `~/.claude` settings** (and `.codex`/copilot configs) —
   would collide/interleave with our own hook dispatcher, coord, banner, and budget
   hooks;
4. re-asserts itself **before every Bash/PowerShell tool call** (constant overhead).

So it would fight the very hook/config layer this setup owns. If ever wanted, the
ONLY acceptable path is the isolated **library `compress(messages)` API** in a
sandboxed/one-off context — never `headroom init`, the proxy, or the plugin.

# Why it was on the radar

A possible upgrade to the tokenjuice opt-in slot (compress known-noisy output). The
gate did its job (blocked first, audited second). Parked as awareness,
`adoption: AUDITED-CLEAN-but-do-not-install`. Source clone lives under the super_code
repo's gitignored `.scratch/headroom-audit/` for re-inspection; safe to delete (text
only, nothing executed).

# Follow-up (2026-07-02): compression logic PORTED, package still not installed

The valuable part — the structure-preserving compression policies — was ported
by hand into `scripts/tokenjuice_condense.py` (stdlib-only, Apache-2.0
attribution in the module docstring) and wired into tokenjuice as the
`condense` strategy + `--condense` flag. Ported surfaces: the JSON key/schema
preservation policy (`json_handler.py`), the regex signature fallback of the
code handler (`code_handler.py`), the log error/trace/summary selection
(`log_compressor.py` Python mirror), the word-level entropy secret
preservation (`masks.py`), and the fallback content detector (`detector.py`).
Deliberately NOT ported: Magika ML detection, tree-sitter AST path, the Rust
text crusher, CCR retrieval store, adaptive Kneedle sizing, and everything
proxy/plugin/daemon shaped. The headroom PACKAGE remains do-not-install; the
port is pure text-transform code with no network/exec/fs access. Measured:
~54% savings on a 24K-char JSON dump where the command rules alone saved 0%.
