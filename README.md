# super_code

> Personal Claude Code setup that runs on your **Claude Pro / Max subscription** for inference, extended with a ~165-item skill bundle, automatic self-curate, smart prompt router, multi-tier automatic code review, and a custom statusline. No separate Anthropic or OpenAI API key needed for the core features.

This README covers the full feature catalog of the project. For original Hungarian setup notes see [`hermes-agent/CLAUDE_ELOFIZETES.md`](hermes-agent/CLAUDE_ELOFIZETES.md) and the architecture deep-dive in [`hermes-agent/INTEGRATION_CLAUDE_CODE.md`](hermes-agent/INTEGRATION_CLAUDE_CODE.md).

---

## Repository layout

```
super_code/
- CLAUDE.md                          (project-level rules, extends the global ~/.claude/CLAUDE.md)
- README.md                          (this file)
- LICENSE                            (Apache 2.0, inherited from upstream Hermes)
- home_dotclaude/
   - CLAUDE.md                       (versioned mirror of ~/.claude/CLAUDE.md, the global rules)
- scripts/
   - statusline_with_weekly.js       (custom statusline, install to ~/.claude/scripts/)
- hermes-agent/
   - claude_code_integration/        (hooks, curator, skill lifecycle, smart router)
   - claude_skills_backup/           (~165 skills converted to Claude Code format)
   - CLAUDE_ELOFIZETES.md            (Pro/Max OAuth setup guide, Hungarian)
   - INTEGRATION_CLAUDE_CODE.md      (architecture writeup)
   - LICENSE                         (Apache 2.0)
```

The full upstream Hermes runtime (agent core, gateway, TUI, web, docker, Hermes CLI, ...) is intentionally NOT shipped here -- the Claude integration does not need it. If you want the full fork, see <https://github.com/nousresearch/hermes-agent>.

State files (`ruvector.db`, `.hermes_*.json`, `.qrev_auto_state.json`, `.statusline_baselines.json`, `.credentials.json`, `.ecc-session-bridge/`) are gitignored and never reach the repo. See `.gitignore` for the full exclusion list.

---

## Feature catalog

### 1. Skill bundle (~165 skills)

Bundled in `hermes-agent/claude_skills_backup/`. After install they land in `~/.claude/skills/hermes-*/` and are callable as slash commands.

Categories: code review (`code-review-and-quality`, `code-review-expert`, `solid`, `karpathy-guidelines`), build / test resolvers (`hermes-debugging-*`), language patterns (TypeScript, Python, Go, Rust, Kotlin, Swift, Dart/Flutter, ...), framework patterns (FastAPI, Django, Laravel, Spring, Quarkus, Nest, Nuxt, ...), domain knowledge (finance, legal, marketing, healthcare HIPAA, e-commerce, ...), workflow skills (`qPlan`, `qGoal`, `qRem`, `qMin`, `qUpd`, `qDo`, `qRev`, `rev`, `hunt`, `think`, `learn`, `write`, `read`, `check`, `tw`, ...), knowledge graph (`graphify`), creative / design (`hermes-p5js`, `hermes-pixel-art`, `hermes-baoyu-*`, `design`, `compose`, ...), and many more.

`graphify` ships as an upstream-tracked skill — bundled verbatim from <https://github.com/safishamsi/graphify> (`v1` branch, MIT, compatible with this repo's Apache 2.0 because the manifest is unmodified). It needs the companion PyPI package: `pip install graphifyy` (note: double-y; Python 3.10+ required). After install, trigger with `/graphify`, `/graphify <path>`, `/graphify query <q>`, etc. — see the upstream README for the full command surface. The auto-learning routing for `graphify`, `hermes-curate`, and `hermes-learn` is pinned in the global `~/.claude/CLAUDE.md` "Skills index and routing" section.

### 2. Auto-curate (Pro/Max subscription, no extra API key)

Stop hook records every finished session into `~/.claude/.hermes_curator_queue.json` (instant, free, offline). The next session's UserPromptSubmit hook checks the queue: when >= 3 sessions are pending or >= 7 days have passed since the last drain, it injects an `additionalContext` instructing Claude to silently re-read the queued transcripts, extract high-confidence recurring patterns, and write fresh skills directly under `~/.claude/skills/hermes-auto-<slug>/`. The work runs inside the current Claude session -- your subscription covers it. The reply gets prepended with `- curator: drained N session(s), wrote M auto-skill(s)`.

Same pattern for `/qPlan` runs via the separate `~/.claude/.hermes_qplan_curator_queue.json` queue.

### 3. Smart prompt router

`smart_router_prompt_hook.py` runs on every user prompt and applies deterministic rules. If the prompt looks like a build error, security review request, etc., it appends a relevant skill suggestion as `additionalContext`. Rule-based, no LLM call, costs nothing.

### 4. Skill lifecycle

`skill_lifecycle.py` runs from the UserPromptSubmit hook once every 7 calendar days. It scans `~/.claude/skills/` for skills that haven't been invoked in the last 90 **coding days** (the bicycle principle: only days with real session activity count) and moves them to `~/.claude/skills-archive/`. The list of detected skill invocations comes from a transcript scan that runs after every session in the Stop hook, written into `~/.claude/.hermes_skill_state.json`.

### 5. Multi-tier automatic code review (`/qRev` auto)

Three tiers, all automatic, threshold-driven, no manual prompts:

| Tier | Trigger | Action | Wall-clock |
|---|---|---|---|
| 1 -- Static | every Write/Edit | Semgrep if the repo has a `.semgrep.yml` | ~1-3 s, no LLM cost |
| 2 -- qMin | 50 edits OR 5000 LOC since last review | next prompt: Claude silently runs `/qMin` (5-axis lens) on the uncommitted diff before answering | ~15-60 s, 1 LLM turn |
| 3 -- qRev | 250 edits OR 25000 LOC since last review (preempts tier 2) | next prompt: Claude silently runs full `/qRev` (qMin + Phase A + 3-pass exhaustive agent fleet) | 15-30 min, subscription-covered |

Threshold overrides via environment variables: `QREV_AUTO_LEVEL` (0/1/2/3), `QREV_AUTO_QMIN_EDITS`, `QREV_AUTO_QMIN_LOC`, `QREV_AUTO_QREV_EDITS`, `QREV_AUTO_QREV_LOC`.

Implementation: `qrev_edit_counter.py` (`PostToolUse` matcher `Write|Edit`) increments per-session counters into `~/.claude/.qrev_auto_state.json` and flips `pending_qmin` / `pending_qrev` at threshold. `qrev_auto_inject.py` (`UserPromptSubmit`) emits the `additionalContext` instruction when a flag is set. `qrev_mark_done.py` is the CLI Claude calls after the auto-review to reset the matching counters.

**Auto-fix** -- `/qMin` and `/qRev` carry a standing pre-approval: after the verdict / synthesis report, Claude immediately starts applying surgical fixes for each P0 -> P1 -> P2 -> P3 finding without waiting for confirmation. Each fix is logged inline as `- fix [P<n>/<source>] <file>:<line>: <what changed>`. Findings that need a real design decision get a `- skip [<source>] <file>:<line>: <reason>` line. Same policy for direct calls and the auto-tier hooks.

The `/qRev` skill itself (`~/.claude/skills/qRev/SKILL.md`) is a fused review that wraps `/qMin` + `/rev exhaustive`. Argument forms:

- `/qRev` -- qMin + Phase A + exhaustive 3-pass on the uncommitted diff
- `/qRev topic:<name>` -- same but exhaustive depth with agent roster filtered to `security` / `db` / `perf` / `ml` / `tests`
- `/qRev PR#<n>` / `/qRev branch` / `/qRev full` / `/qRev <path>` / `/qRev fast` -- alternate scopes
- Case-insensitive: `/qrev`, `/Qrev`, `/QRev`, `/QREV` all route to the same skill.

### 6. Custom statusline (`statusline_with_weekly.js`)

Three half-width progress bars in one line, refreshed every prompt. Layout:

```
O4.7 2Compact S##...26%full| 5h##...32%full(01:23 r,69%)A| 1w##...12%full(4d5h r,39%)A
```

- **`O4.7`** -- shortened model label (no `Opus 4.7 (1M context)` clutter).
- **`2Compact S`** -- session context bar. Shows how close you are to auto-compact (the 16.5% reserved buffer is treated as the danger floor, so 100% on the bar = auto-compact fires now). Threshold colors: green `< 50%`, yellow `< 65%`, orange `< 80%`, blinking red `>= 80%`.
- **Per-session baseline subtraction** -- at session start (and after `/clear`), the system prompt + skill list takes ~10-15% raw. The statusline subtracts this baseline so your bar starts at 0% and only shows your own context consumption. State per session in `~/.claude/.statusline_baselines.json`. After `/clear` the bar detects the drop and re-baselines automatically.
- **`5h` and `1w` bars** -- rate-limit consumption with countdown (`HH:MM r` for hour-scale, `Xd Yh r` for day-scale) and a time-proportional reference percentage. A solid up-triangle (green) means you're significantly under-pace (more headroom than the elapsed time would predict). A solid down-triangle (red) means you're over-pace. The tolerance band is `+/- elapsed%/3`, so the arrow fires only when the deviation is significant.
- **All three bars** share the same color gradient based on used %, including the 5h/1w bars (they used to be fixed blue/orange).

**Source in this repo**: [`scripts/statusline_with_weekly.js`](scripts/statusline_with_weekly.js). Install by copying (or symlinking) it to `~/.claude/scripts/statusline_with_weekly.js`, then wire it as the statusline in `~/.claude/settings.json` (`"statusLine": { "type": "command", "command": "node ~/.claude/scripts/statusline_with_weekly.js" }`).

PowerShell install:
```powershell
New-Item -ItemType Directory -Force -Path "$HOME\.claude\scripts" | Out-Null
Copy-Item .\scripts\statusline_with_weekly.js "$HOME\.claude\scripts\statusline_with_weekly.js" -Force
```

Bash / WSL install:
```bash
mkdir -p ~/.claude/scripts
cp scripts/statusline_with_weekly.js ~/.claude/scripts/statusline_with_weekly.js
```

### 7. No-decorative-unicode rule

Global (`~/.claude/CLAUDE.md`) and project (`./CLAUDE.md`) carry a rule against decorative unicode in code, docs, comments, and commit messages: no rightward arrow, checkmark, cross, decorative bullets, stars, or pointing triangles. ASCII (`->`, `[ok]`, `[fail]`, `-`, `*`) is preferred. Windows cp1252 console crashes on these chars and search tools miss them. The rule explicitly allows the statusline's functional UI glyphs (bar fill, pace triangles) because they carry visual state with no plain-text substitute.

### 8. Dual-window workflow (`.worktrees/`)

Two Claude Code windows on the same project but on **different branches** simultaneously, without working-tree thrashing. Uses `git worktree`: one `.git` directory backs N independent checked-out trees, each on its own branch.

Canonical layout — linked worktrees live under `.worktrees/<branch>/` inside the project, gitignored:

```powershell
# one-time, from the main tree
git worktree add .worktrees/feat-x -b feat-x          # new branch
git worktree add .worktrees/feat-x feat-x             # existing branch

# in a fresh Claude window
cd D:\Projects\super_code\.worktrees\feat-x
claude

# cleanup when the branch is merged or abandoned
git worktree remove .worktrees/feat-x
git branch -d feat-x
```

Why it's safe to run two windows simultaneously: an audit of the hook layer confirmed that all per-session state files (`~/.claude/.qrev_auto_state.json`, `.hermes_curator_queue.json`, `.statusline_baselines.json`, `.ecc-session-bridge/`, semgrep findings under each tree's local `.claude/review-log/`) are keyed by `session_id`, not by working-directory path. Two concurrent windows get two distinct session IDs and never collide. Each worktree gets its own `.claude/settings.local.json` — you'll see fresh permission prompts the first time you do something in the new tree; that's expected.

For shared `exclude/TODO.md` / `TODO.md` files that both windows may read, see the per-window `[w-...]` identifier rule plus the `pid host start hb` liveness protocol in [`CLAUDE.md`](CLAUDE.md). A returning window can deterministically tell whether the original author is still alive (so the task is taken) or dead (so the task can be claimed).

### 9. `qPlan` panel critic — multi-agent planning fleet

`qPlan` is an author↔critic iteration loop that deepens a plan via a guaranteed-terminating ledger + tier-rubric. Original v1 had two critic providers: same-session Claude, or a cross-model OpenAI critic via `~/.claude/skills/qPlan/scripts/openai_critic.py`.

The new default is **`critic_provider: panel`**: the single critic turn becomes a parallel fan-out across a curated set of planning lenses (requirements / architecture / business / spec / estimation / risk / openai), each one an independent agent invocation that returns the same `{verdict, suggestions[]}` JSON the loop already understands. The merge step de-dupes via the existing ledger semantic-match and tags each surviving suggestion with `source_lens` for the audit trail.

This is the same structural move `/rev` made for code review (~12-15 specialist agents in parallel with skill bundles). The author↔critic outer loop, the materiality ledger, the tier rubric, and the termination conditions (`phase_a_converged`, `verdict_converged`, `no_progress >= K`, `hard_cap_rounds`) are unchanged — the panel only changes *what counts as a critic turn*.

Backwards-compat: `critic_provider: claude` and `critic_provider: openai` keep v1 single-critic behavior verbatim.

See [`hermes-agent/claude_skills_backup/qPlan/SKILL.md`](hermes-agent/claude_skills_backup/qPlan/SKILL.md) for the full configuration block and the lens roster.

### 10. AI video pipeline (`comfyui-local` + `sora-cloud` MCP servers)

Hybrid AI-video stack drivable from Claude Code via MCP:

- **Local** ComfyUI + LTX-Video 0.9.8 distilled fp8 (2B). Free, runs on consumer GPUs (8 GB VRAM minimum), ~5-15 min per 5 s 480p clip on an RTX 4070 Laptop.
- **Cloud** OpenAI Sora 2 / Sora 2 Pro. $0.10-$0.30 per second, ~1-3 min per clip, much higher quality.

Both are exposed as MCP servers Claude Code can call: `comfyui-local` (local) and `sora-cloud` (cloud).

Auto-installer (Tier C-focused, idempotent — runs hardware detection, ComfyUI clone+venv+PyTorch cu126, ~23.5 GB model download, launcher generation, MCP runtime deps):

```powershell
.\scripts\setup_ai_video.ps1
# or to just check what tier you'd land in:
.\scripts\setup_ai_video.ps1 -Redetect
```

Hardware tier table, troubleshooting, what worked / what didn't on first install (e.g. why the ComfyUI Desktop NSIS installer is skipped — it crashes with `System.dll 0xc0000005` on Win11 26200), and the manual post-install steps (claude mcp add, OpenAI API key, workflow JSON save) all live in [`docs/AI_VIDEO_SETUP.md`](docs/AI_VIDEO_SETUP.md).

Source files in this repo:

- [`scripts/setup_ai_video.ps1`](scripts/setup_ai_video.ps1) — the installer
- [`hermes-agent/claude_code_integration/mcp_servers/comfyui_mcp.py`](hermes-agent/claude_code_integration/mcp_servers/comfyui_mcp.py) — local MCP, thin wrapper around ComfyUI's HTTP API
- [`hermes-agent/claude_code_integration/mcp_servers/sora_mcp.py`](hermes-agent/claude_code_integration/mcp_servers/sora_mcp.py) — cloud MCP, thin wrapper around `openai.videos`
- [`docs/AI_VIDEO_SETUP.md`](docs/AI_VIDEO_SETUP.md) — guide + history

Per-machine artifacts (ComfyUI clone, venv, models, generated `.bat`, API key file) are all gitignored — nothing under `ai_video/comfyui/`, `ai_video/models/`, or `*.openai_api_key` is committed.

### 11. Learning data layer (prerequisite for a future learned predictor)

Pure logging, no ML, no extra dependencies, append-only, reversible. The point (per the FabricPC PCN evaluation) is that the unlock for any learned component is *data first, algorithm later* — so three deterministic streams accumulate `X -> Y`-style records that a future predictor (PCN, linear, gradient-boosting, whatever) can be evaluated against honestly:

| Stream | Written by | File | Captures |
|---|---|---|---|
| Router | `smart_router_prompt_hook.py` (`_log_eval_row`) | `~/.claude/.smart_router_eval.jsonl` | prompt features -> rule suggestion vs. actually-invoked skill |
| qRev verdict | `qrev_mark_done.py` (`append_verdict_log`) | `~/.claude/.qrev_verdict_log.jsonl` | review kind -> P0/P1/P2/P3 + fix/skip counts |
| Decision | `decision_log_cli.py` (`append_decision_log`) | `~/.claude/.decision_log.jsonl` | decision + rationale; `revisit_if` + later `outcome` (`held`/`reversed`) is the natural quality label |

The decision stream is fed by the global `CLAUDE.md` "Decision log" convention: when Claude records a non-trivial decision it also pipes the fields as JSON on stdin to `decision_log_cli.py`. Required fields are just `title` + `decision`; `outcome` defaults to `open`. The router and verdict streams already existed; the decision stream (`decision_log_cli.py` + `test_decision_log_cli.py`) completes the trio. None of these train anything today — they only collect, so the option stays open without committing to a model.

---

## Install

### Prerequisites

1. **Claude Code** installed and logged in:
   ```powershell
   npm install -g @anthropic-ai/claude-code
   claude /login
   ```
   This creates `~/.claude/.credentials.json` (on Windows: `C:\Users\<user>\.claude\.credentials.json`).

2. **Python 3.10+** with `pip` (used for the hook scripts).

3. Optional: **Node.js** if you want the JS statusline (most setups already have it via Claude Code itself).

### Steps

```powershell
# 1. Clone wherever you want it to live permanently
git clone git@github.com:mollyrrose/super_code.git D:\Projects\super_code
cd D:\Projects\super_code

# 2. Install the skill bundle and wire the hooks
python hermes-agent\claude_code_integration\install_into_claude_code.py

# 3. (Optional) Set up the AI video pipeline (~30 GB, RTX-class GPU recommended)
.\scripts\setup_ai_video.ps1
```

The skill installer (step 2):
- copies `claude_skills_backup/*` skills into `~/.claude/skills/hermes-*/`
- wires the `Stop`, `PreCompact`, `UserPromptSubmit`, `PostToolUse`, `SessionEnd` hooks into `~/.claude/settings.json`
- creates the empty queue files (`~/.claude/.hermes_curator_queue.json`, `~/.claude/.hermes_qplan_curator_queue.json`, `~/.claude/.qrev_auto_state.json`)

The AI video installer (step 3, optional) is documented in [`docs/AI_VIDEO_SETUP.md`](docs/AI_VIDEO_SETUP.md). It auto-detects your GPU tier and only fully automates Tier C (8-11 GB VRAM) today; other tiers print guidance.

For manual wiring see the architecture writeup at [`hermes-agent/INTEGRATION_CLAUDE_CODE.md`](hermes-agent/INTEGRATION_CLAUDE_CODE.md).

### Verification

```powershell
claude --version
# Start a Claude session. Try /qRem, any /hermes-* skill, /qRev, etc.
```

After the install, your `~/.claude/settings.json` `hooks` block should look like (paths normalized):

```jsonc
"hooks": {
  "Stop":              [ ... curator_stop_hook.py ... ],
  "PreCompact":        [ ... curator_precompact_hook.py ... ],
  "UserPromptSubmit":  [ ... curator_prompt_hook.py, smart_router_prompt_hook.py, context_budget_gate.py, qrev_auto_inject.py ... ],
  "PostToolUse":       [ { "matcher": "Write|Edit", "hooks": [ ... semgrep_postedit_hook.py, qrev_edit_counter.py ... ] } ],
  "SessionEnd":        [ ... rev_learn_sessionend.py ... ]
}
```

---

## Configuration

The repo stores no secrets. Hooks use the Claude OAuth token (`~/.claude/.credentials.json`) created by `claude /login`. **Never** commit `.credentials.json` or any `.hermes_*.json` / `.qrev_auto_state.json` / `.statusline_baselines.json` state files -- the bundled `.gitignore` already excludes them.

If you use other OpenAI / Anthropic / GitHub keys in custom skills, put them in `~/.claude/settings.json` under the `env` field, NOT in the repo. The hook scripts read env vars at startup so changes take effect on the next `Write/Edit` or prompt submit, no restart needed.

Override defaults for the auto-review tiers in the same `env` block:

```jsonc
"env": {
  "QREV_AUTO_LEVEL":      "3",       // 0=off, 1=static only, 2=+qMin, 3=+qRev
  "QREV_AUTO_QMIN_EDITS": "50",
  "QREV_AUTO_QMIN_LOC":   "5000",
  "QREV_AUTO_QREV_EDITS": "250",
  "QREV_AUTO_QREV_LOC":   "25000"
}
```

---

## AI Radar (`okf/ai-radar/`)

A compounding, agent-maintained knowledge bundle in the **Open Knowledge Format**
(OKF: a directory of markdown files with YAML frontmatter) tracking "what is new /
better in the AI world" — and flagging it where it touches your work. Source of truth
in `okf/ai-radar/`, synced to `~/.claude/okf/ai-radar/`.

- **Intake** (hybrid): `/radar-add <url|note>` (manual) and `/radar-scan [topic]`
  (web + YouTube keyword-search & transcript + arXiv multi-modal sweep, then a lint
  pass). Every interesting GitHub repo is **skillspector-scanned before trust**, and
  entries are graded on a freshness/`supersedes` model.
- **Speak-up** (strict, kill-switched): a `/radar-check` gate wired into `/qRem` and
  `/qRev` surfaces a single high-signal `[radar]` line when the project uses something
  the radar marks superseded — silence by default (honors no-nagging). Disable with
  `AI_RADAR_DISABLE=1`.

## `/pentest` — non-destructive security audit engine

A local application-security auditor for the project you're in. Auto-maps the project,
runs SAST + SCA + secrets + IaC on the code and (optionally) non-destructive DAST
against a locally-launched instance, produces a P0-P3 report, and auto-fixes code-level
findings like `/qRev`. **Hard invariant: "attack" = active DISCOVERY only, never break
anything** — real exploitation / C2 / credential brute / relay / DoS are excluded by
design and enforced by the fail-closed guardrail `scripts/pentest_policy.py`
(+ `pentest_policy_smoketest.py`). Modes: `/pentest static` (code only), `/pentest`
(code + local DAST), `/pentest remote <target>` (authorized VPN target, scope-gated).
Kill switch `PENTEST_DISABLE=1`. The discovery-safe tool matrix lives in the AI Radar
(`okf/ai-radar/devsec-tools/appsec-toolchain.md`); offensive frameworks (HexStrike,
etc.) are recorded there as awareness only.

## License

- Upstream Hermes-derived code (`hermes-agent/claude_code_integration/` and the `claude_skills_backup/hermes-*` skills) stays under the original Apache 2.0 license -- see [`hermes-agent/LICENSE`](hermes-agent/LICENSE).
- The repo-specific additions (this README, the auto-review tier, the custom statusline, the project CLAUDE.md, the q-skills like `qRev`) are released under the same Apache 2.0.

## Upstream

- Hermes Agent: <https://github.com/nousresearch/hermes-agent>
- Claude Code: <https://github.com/anthropics/claude-code>
