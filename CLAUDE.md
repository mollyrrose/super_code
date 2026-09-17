# CLAUDE.md — super_code project

This file extends the global `~/.claude/CLAUDE.md` with rules specific to this repo.

## Project shape

`super_code` is the personal Claude Code setup: hook scripts in `~/.claude/scripts/`, the curator and skill-lifecycle Python modules under `hermes-agent/claude_code_integration/`, and a `claude_skills_backup/` of ~165 skills that get installed into `~/.claude/skills/`. See `README.md` for the full feature catalog.

## Preflight checklist before implementation (pre-code, not a substitute for /qRev)

Before starting non-trivial coding work in this repo, check for known constraints on the area being touched instead of only finding out from `/qRev` after the diff exists:

- Check `CODING_STANDARDS.md` (if present) and any Cursor MDC rules (`.cursor/rules/**/*.mdc`) that apply to the touched path.
- Check `<repo>/.claude/review-log/findings.jsonl` for recurring past findings (source: `semgrep` / `rev-standards` / agent fleet) already logged against the same file or area.
- If a recurring pattern applies, state it in the plan before writing the code, not after.

This is a lightweight, static preflight, not a lighter `/qRev`. It cannot review code that doesn't exist yet, so it only surfaces already-known standards/recurring issues — it does not catch new implementation-level bugs, which still need the post-diff agent fleet. Full review still runs per "Review gates: run the review, don't ask" (global `~/.claude/CLAUDE.md`) — this checklist only moves *known, already-logged* lessons earlier, it does not remove the need for `/qRev` on the actual diff.

## Questions to the user — always pair with a plain-logic restatement

This MIRRORS the global "Plain-language questions to the user" rule (now the dual-layer form) and is restated here so it's visible inside the project too. Every time you ask the user anything (clarifying question, A/B/C choice, yes/no, approval gate, "which option"), do not just rewrite the question into plain language — keep the normal (possibly technical) question AND add a simplified-logic restatement directly **underneath** it.

Format for every question:
1. Ask the normal question first (technical wording is fine here).
2. Immediately under it, restate the same question with **simplified logic** — the reasoning broken down the way you'd explain it to a sharp 17-year-old who has no prior context: short sentences, one idea per sentence, concrete examples instead of abstract trade-offs, plain cause-and-effect ("if you pick A, then X happens; if you pick B, then Y happens").

Hard constraints:
- The point is **simplified logic, NOT slang.** Do not use slang, memes, or cultural shorthand. Plain, simple, correct reasoning — just unpacked into smaller steps.
- The simplified version must ask the SAME question, not a watered-down or different one. It re-explains; it does not change what is being decided.
- Match the user's language (if the conversation is Hungarian, both layers are Hungarian).
- For `AskUserQuestion` tool calls, the plain-logic restatement goes in the assistant text that accompanies the tool call (and/or the option descriptions), since the tool's own fields are short.
- This is additive to the global rules, including the `USER INPUT REQUIRED` banner requirement — still emit that banner when the turn ends waiting on the user.

This applies only to questions I ASK the user. It does NOT mean dumbing down code, reviews, commit messages, or my normal technical explanations.

## No decorative unicode

This rule mirrors the global rule and is restated here so it's visible inside the project too.

Don't put characters like the rightward arrow (U+2192), check marks (U+2713/U+2714/U+2705/U+2611/U+1F5F8/U+1F5F9), crosses or X marks (U+2715/U+2716/U+2717/U+2718/U+274C/U+274E/U+2612/U+1F5D9/U+1F5F4/U+1F5F5/U+1F5F7), info source (U+2139/U+1F6C8), bullets (U+2022/U+25CF/U+25E6), stars (U+2605/U+2606) or pointing triangles (U+25B6/U+25BC) into **executable / runnable code** — string and other literals, identifiers, and any value the program actually runs or prints — or into **shell commands, regex patterns, or any other tool input** that gets parsed or executed.

**Where the ban applies — code vs. comments.** The ban is absolute for anything that executes or is parsed as input: source-code literals and identifiers, shell commands, regex patterns, and any other tool input. **Code comments and note / documentation prose are exempt** — you MAY use these characters and emoji there (including the "direct hit" / target emoji `🎯`, U+1F3AF), because a comment or note is read by a human and is never executed or printed by the program. The single line to hold: **never in runnable code; allowed in comments and notes.** Commit messages and PR bodies still lean ASCII (they feed `git log` and grep on cp1252 consoles), but that is a preference, not the hard ban.

The same rule covers **emoji-style** decorative glyphs and any visually similar character. Forbidden emoji (non-exhaustive — the principle covers anything in the same family):
- check / OK / pipa (all colors, weights, and box variants): U+2713, U+2714, U+2714 U+FE0F, U+2705, U+2611, U+1F5F8, U+1F5F9
- fail / wrong / X mark (all colors, weights, and box variants): U+2715, U+2716, U+2717, U+2718, U+274C, U+274E, U+2612, U+1F5D9, U+1F5F4, U+1F5F5, U+1F5F7
- info source: U+2139, U+1F6C8
- warning / alert: warning sign `⚠️` (U+26A0, with or without the U+FE0F variation selector — bans both `⚠` and `⚠️`), no entry `⛔` (U+26D4), police light `🚨` (U+1F6A8), shield `🛡️` (U+1F6E1), broom `🧹` (U+1F9F9)
- status dots: `🟢🔴🟡🔵` (U+1F7E2..U+1F7E6) and the larger circle family
- thumbs / pointing hands: `👍👎` (U+1F44D/U+1F44E), `👉👈👆👇`
- decoration: `✨` (U+2728), `⭐🌟`, `🔥` (U+1F525), `🚀` (U+1F680), `🎉🎊`, `💯`, target `🎯` (U+1F3AF)
- notes / ideas: `💡` (U+1F4A1), `📝` (U+1F4DD), `📌` (U+1F4CC), `📚`, `📋`

Even when filtering output that contains these glyphs (e.g. `grep` over a `node:test` reporter stream that emits check variants `✓ ✔ ✅ ☑ 🗸 🗹` (U+2713 / U+2714 / U+2705 / U+2611 / U+1F5F8 / U+1F5F9), X variants `✕ ✖ ✗ ✘ ❌ ❎ ☒ 🗙 🗴 🗵 🗷` (U+2715 / U+2716 / U+2717 / U+2718 / U+274C / U+274E / U+2612 / U+1F5D9 / U+1F5F4 / U+1F5F5 / U+1F5F7), or info-source variants `ℹ 🛈` (U+2139 / U+1F6C8)), write the filter using ASCII keywords like `fail|error|pass` — **never quote the glyph itself** in a pattern. The reporter also emits ASCII status words alongside the glyphs (`fail 0`, `pass 12`); match those.

Rule of thumb: if a character is outside Basic Latin / Latin-1 and isn't on the functional allowlist below, treat it as decoration and drop it **from code and tool input**. (Comments and notes are exempt — see "Where the ban applies" above.)

Reasons:
- Windows cp1252 console crashes on emit (`UnicodeEncodeError`); test smoke scripts have already hit this.
- ripgrep / grep with default ASCII expectations miss them.
- They render differently across terminals, editors, and chat tools.
- Emoji especially blow up log files, JSONL session captures, and any tool that assumes single-byte text.
- They add no information vs plain ASCII (`[ok]`, `[fail]`, `[warn]`, `note:` carry the same meaning and grep cleanly).

ASCII equivalents:
- arrow: `->`
- pass: `[ok]` or `(ok)` or just write "pass"
- fail: `[fail]` or `(bad)`
- warn: `[warn]` or `(warn)`
- bullets: `-` or `*`
- note: `[i]` or `note:`

Exceptions that ARE allowed because they're functional, not decorative:
- statusline progress-bar glyphs `U+2588 U+2591` and pace arrows `U+25B2 U+25BC` in `scripts/statusline_with_weekly.js` (installed to `~/.claude/scripts/statusline_with_weekly.js`) — that's a UI surface, the chars carry visual state with no plain-text substitute.
- the `USER INPUT REQUIRED` banner's green-dot emoji (`🟢`, U+1F7E2), approved 2026-06-21 — a user-facing attention signal emitted as `🟢🟢🟢 USER INPUT REQUIRED 🟢🟢🟢` on its own line (NOT fenced) so the idle terminal is noticed in color. The ASCII text `USER INPUT REQUIRED` stays verbatim inside it — `banner_stop_hook.py` detects the banner by that substring, so the dots are cosmetic, never load-bearing. (The old all-asterisk box was dropped because a line of `*` renders as a markdown horizontal rule, making the rows vanish.)
- em-dash `U+2014` in prose, because plain `--` collides with CLI flag syntax.

When in doubt: if removing the character wouldn't reduce the meaning a plain-text reader picks up, the character is decoration and shouldn't be there.

## Hooks (don't break them)

`~/.claude/settings.json` runs these hooks. The two HOT-PATH events
(`UserPromptSubmit`, `PostToolUse`) are now consolidated behind a single
dispatcher, `scripts/hook_dispatch.py` (installed to
`~/.claude/scripts/hook_dispatch.py`): instead of N separate `python.exe`
processes per event, settings.json invokes the dispatcher once with the event
name as `argv[1]`, and it imports + runs each underlying hook's `main()`
in-process. Rationale: a cold Windows interpreter spawn costs ~1.2-1.6s, so
running 4 prompt hooks (and 2 edit hooks) as separate processes added seconds of
latency per turn; one interpreter start instead of 4/2 cuts that ~3-4x (cleanly
4x on PostToolUse, ~468 ms saved per edit). The individual hook files are
UNCHANGED -- they still run standalone and their `*_smoketest.py` still pass.

- `PostToolUse(Write|Edit)` -> `hook_dispatch.py PostToolUse`, which runs
  `semgrep_postedit_hook.py` then `qrev_edit_counter.py`. A hook exiting 2 (with
  a stderr message) propagates: the dispatcher re-emits that stderr and exits 2.
- `UserPromptSubmit` -> `hook_dispatch.py UserPromptSubmit`, which runs
  `curator_prompt_hook.py`, `smart_router_prompt_hook.py`, `context_budget_gate.py`,
  `qrev_auto_inject.py`, `coord_prompt_hook.py`, `memgraph_prompt_hook.py` (in that
  order). Each hook emits a
  `hookSpecificOutput.additionalContext` JSON (or nothing); the dispatcher
  extracts every hook's `additionalContext` and emits ONE merged JSON object
  (blank-line-joined, original order preserved) -- equivalent to how Claude Code
  concatenates context across separately-registered hooks.
  - `smart_router_prompt_hook.py` (rules in `smart_router_rules.py`) emits both a skill suggestion and a `[model-router hint]` for subagent model tiering (haiku/sonnet/opus). The tiering policy Claude follows lives in the global `~/.claude/CLAUDE.md` under "Subagent model routing (tiering)". `context_budget_gate.py` is now tracked in this repo at `scripts/` and budgets the window per prompt from, in order: the statusline bridge (`~/.claude/.statusline_baselines.json` `remaining` -- the harness's own remaining-%, ground truth), then the model id (1M families `opus-4`/`opus-5`/`sonnet-5`/`fable`; GLM/z.ai -> 200K via `CC_GLM_CONTEXT_LIMIT`; else 200K), plus a self-correction backstop: if the transcript's live token count exceeds the guessed window, the guess is provably wrong and snaps to 1M (this is what catches the NEXT unlisted 1M model -- the sonnet-5 miss on 2026-08-05 fired false NEAR-FULL warnings at ~30% real usage). A `/model` switch (or running on GLM) re-budgets context. The GLM (z.ai) alternate-provider groundwork and its launcher (`scripts/claude-glm.ps1`) are documented in the global `~/.claude/CLAUDE.md` under "GLM (z.ai)". `context_budget_gate.py` runs three escalating tiers as the window fills: a SOFT "proceed despite tight budget?" gate at ~25% remaining, a near-full tier at ~18% that tells the user in ONE line that `/qClose` is available and then CONTINUES the work (NON-BLOCKING by design -- the old stop-and-banner wording deadlocked against loop/until Stop-condition hooks into the harness's "hook blocked the turn from ending 9 consecutive times" error), and -- highest, fired first with headroom -- a **pre-compact qUpd flush tier** at ~35% remaining (`CC_BUDGET_QUPD_PCT`) that proactively instructs Claude to run `/qUpd`'s doc refreshes (INDEX/TODO/SYSTEM_STATUS/drawio) so the durable tracking docs are on disk BEFORE compaction summarises the session. The flush is **disk-write only -- it must NOT commit or push** (files persist on disk through compaction; committing is a separate later step). ALL THREE tiers are fire-once per session (shared state in `~/.claude/.context_qupd_flush_state.json`, override via `CC_BUDGET_QUPD_STATE`), re-firing only after more percent is consumed: `CC_BUDGET_QUPD_REDO_DELTA` (default 15) for the flush, `CC_BUDGET_QCLOSE_REDO_DELTA` / `CC_BUDGET_SOFT_REDO_DELTA` (default 10) for near-full/soft. Kill switches: `CC_BUDGET_QUPD_DISABLE=1` (flush tier), `CC_BUDGET_GATE_DISABLE=1` (whole gate).
- `Stop`: `curator_stop_hook.py` then `banner_stop_hook.py` (two hooks; Stop is
  NOT a hot path, so they stay as separate commands — not dispatched/consolidated).
  `banner_stop_hook.py` (in `scripts/`, installed to `~/.claude/scripts/`) is the
  USER INPUT REQUIRED banner backstop: if the final message looks like it awaits
  input but lacks the banner, it returns a Stop "block" so the turn continues and
  the banner is added. Conservative + loop-guarded (max 2 blocks/session).
  Kill switch: `BANNER_HOOK_DISABLE=1` or remove its command from `settings.json`
  Stop (backup at `~/.claude/settings.json.bak.pre-banner-hook`).
- `PreCompact`: `curator_precompact_hook.py` (single hook, not dispatched)
- `SessionStart`: `coord_sessionstart_hook.py` (single hook, not dispatched) —
  registers this window on the cross-window coordination board and injects the
  standing protocol at startup (see "Cross-window coordination" below). Backup at
  `~/.claude/settings.json.bak.pre-coord-sessionstart`.
- `SessionEnd`: `rev_learn_sessionend.py` then `memgraph_sessionend.py` (both
  async, separate commands — SessionEnd is not a hot path). `memgraph_sessionend.py`
  queues the session for level-5 memory ingestion (see "Level-5 memory layer"
  below); backup at `~/.claude/settings.json.bak.pre-memgraph`.

Kill switch for the dispatcher: revert the `UserPromptSubmit`/`PostToolUse`
arrays in `settings.json` to the per-hook command list (a backup is at
`~/.claude/settings.json.bak.pre-hook-dispatch`), or set
`CC_HOOK_DISPATCH_DISABLE=1` to make the dispatcher a pass-through no-op without
editing settings.

### ECC plugin hooks disabled on this setup (ECC_DISABLED_HOOKS)

The ECC plugin registers its own hooks on top of ours; several are disabled via
the `ECC_DISABLED_HOOKS` env in `settings.json` (comma-separated hook ids,
checked inside the plugin's `run-with-flags.js`) because on this Windows setup
they produced errors or pure waste (observed 2026-08-06 in the hc windows):

- `pre:observe` / `pre:observe:continuous-learning` -- spawned node + bash.exe on
  EVERY tool call; 779 `spawnSync bash.exe ETIMEDOUT` failures in one session.
- `stop:check-console-log` and the async `stop:session-end` /
  `stop:evaluate-session` / `stop:cost-tracker` -- each Stop re-parsed the
  multi-MB session transcript; under load the inner 30s spawnSync limit tripped,
  surfacing as "Stop hook error ... spawnSync node.exe ETIMEDOUT". Their data
  fed ECC's own learning/metrics, which this setup duplicates with
  hermes-curate / rev-learn / the statusline bridge.
- `stop:desktop-notify` -- macOS/WSL only, no-op cost on native Windows.
- `stop:format-typecheck`, `pre:edit-write:suggest-compact` -- disabled earlier
  (batch typecheck unwanted; interval-based /compact nagging).

Two layers (both applied 2026-08-06):
1. `ECC_DISABLED_HOOKS` env (above) -- the plugin's `run-with-flags.js` skips the
   hook's work one process deep. Removes the errors/heavy work, but the outer
   `node -e` wrapper still spawns per hook per event.
2. Cache trim -- the same 8 hook entries are REMOVED from the installed plugin's
   `~/.claude/plugins/cache/ecc/ecc/<version>/hooks/hooks.json` (backup:
   `hooks.json.bak.pre-trim` next to it), which removes the wrapper spawns too.
   The Stop event dropped from 9 registered hooks to 3 (2 ours + 1 ruflo).
   ROT WARNING: an ecc plugin UPDATE re-materialises the cache and restores the
   hooks -- re-apply the trim after updates (the env layer keeps their inner
   work off in the meantime, so nothing breaks loudly).

Kill switches: restore the `.bak.pre-trim` backup to undo the trim; remove an id
from `ECC_DISABLED_HOOKS` to re-enable a hook (running windows only pick env
changes up on restart).

### Ruflo plugin hook shim patched (cmd.exe arg quoting)

The ruflo plugin's hook shim
(`~/.claude/plugins/cache/ruflo/ruflo-core/0.2.6/scripts/ruflo-hook.cjs`) spawns
the ruflo/claude-flow CLI with `shell:true` on Windows and passed the raw Bash
command as an UNQUOTED `-c` argument. cmd.exe re-tokenizes that string, so any
command text containing `>NNN` (e.g. `awk 'NR>=185 ...'` -- single quotes are
not quotes in cmd, and `=` is a cmd token delimiter) became a real redirect:
a stray file named `185` appeared in the PROJECT ROOT, filled with the hook's
stdin JSON payload. Observed 2026-08-06 in d:/projects/qai as stray files
`185/45/88/92/95`, each matching the first `NR>=NNN` of an awk command run by a
session agent; reproduced 1:1, then fixed.

Fix (applied 2026-08-06): `invokeHook()` in the shim now cmd-quotes every arg
when the `shell:true` path is taken (wrap in `"..."`, double embedded quotes,
fold raw newlines to spaces). Verified: the repro no longer creates the stray
file, and the CLI records the full command text verbatim (previously it was
silently truncated at the first metacharacter). Backup:
`ruflo-hook.cjs.bak.pre-cmdquote` next to the file. ROT WARNING: a ruflo plugin
update re-materializes the cache and reverts the patch -- if number-named stray
files with hook-JSON content ever reappear in a repo root, this patch has been
rolled back by an update; re-apply it. Kill switch: restore the `.bak` backup;
`RUFLO_HOOK_SKIP_NPX=1` additionally makes all ruflo hooks a no-op while no
`ruflo`/`claude-flow` binary is installed (everything currently runs via the
`npx ruflo@latest` fallback).

Changes to these scripts should:
1. Always preserve the `silent no-op on missing / malformed stdin` pattern (see `semgrep_postedit_hook.py:42-50`). A hook that crashes on a bad payload would block every Write/Edit. The dispatcher follows the same rule: any hook that raises / fails to import is isolated as a no-op, and the dispatcher itself exits 0 (UserPromptSubmit) on any internal error.
2. Exit 0 by default; reserve non-zero for genuinely blocking conditions.
3. Be tested with the matching `_smoketest.py` next door before wiring (the dispatcher has `scripts/hook_dispatch_smoketest.py`). When adding/removing/reordering a hot-path hook, update `REGISTRY` in `hook_dispatch.py` AND the matching `settings.json` entry stays a single dispatcher call.
4. Remember hooks run from two homes: most from `~/.claude/scripts/` (copied from this repo's `scripts/`), and the `curator_*`/`smart_router_*` ones directly from `hermes-agent/claude_code_integration/`. After editing a `scripts/` hook, copy it to `~/.claude/scripts/` for it to take effect.

## Multi-window safety and project boundaries

The generic rules — `.worktrees/<branch>/` dual-window workflow, no sibling-copies of the project folder, no directories outside the project root, and the per-window TODO ownership / liveness / takeover protocol — live in the global `~/.claude/CLAUDE.md` under "Project directory boundaries and dual-window safety". They apply here unchanged.

Super_code-specific notes:
- `.worktrees/` is already listed in this repo's `.gitignore`.
- The canonical worktree path here is `D:\Projects\super_code\.worktrees\<branch>\`.

## Level-5 memory layer (memgraph + graphify)

The file-based memory (`~/.claude/projects/D--projects-super-claude/memory/`)
is "level 5" of the 5-level second-brain model (router -> wiki/index ->
semantic search -> knowledge graph -> always-on): a knowledge graph is built
over the memory files and refreshed automatically from session transcripts.
Full briefing: `exclude/SYSTEM_STRATEGIES/memory_levels_briefing.md`.

- **Graph home:** `~/.claude/memory-graph/graphify-out/` (`graph.json`,
  `graph.html` visual, `GRAPH_REPORT.md`). Engine: `graphifyy` (PyPI, 0.8.x)
  on `C:\Python314` — manually audited 2026-07-31 (see
  `~/.claude/.skillspector_log.jsonl`; the skillspector 100/CRITICAL score was
  judged a calibration false positive after hand-audit, user-approved).
- **Query:** `cd ~/.claude/memory-graph && python -m graphify query "<q>"`
  (semantic start-node + BFS relations); `brain_query.py facts <topic>` stays
  the deterministic keyword layer.
- **Always-on loop:** `scripts/memgraph_sessionend.py` (SessionEnd) queues
  sessions -> `scripts/memgraph_prompt_hook.py` (UserPromptSubmit, in the
  dispatcher REGISTRY) nudges when >=2 sessions or >=48h pending -> the
  `memgraph-ingest` skill drains: extracts evergreen facts into memory files,
  updates MEMORY.md, refreshes the graph. Smoketests:
  `memgraph_sessionend_smoketest.py`, `memgraph_prompt_hook_smoketest.py`.
- **Kill switch:** `MEMGRAPH_DISABLE=1` disables queue+nudge+skill; remove the
  REGISTRY entry / SessionEnd command to unwire; delete
  `~/.claude/.memgraph_queue.json` to reset. Same change discipline as the
  other hooks (silent no-op on bad input, smoketest before trusting, copy to
  `~/.claude/scripts/` after edit).

## State files (gitignored, don't commit)

- `~/.claude/.hermes_curator_queue.json`, `.hermes_curator_state.json` — curator queue.
- `~/.claude/.qrev_auto_state.json` — auto-qRev counters.
- `~/.claude/.memgraph_queue.json`, `.memgraph_state.json` — level-5 memory ingestion queue/state; `~/.claude/memory-graph/` — the generated memory knowledge graph.
- `~/.claude/.statusline_baselines.json` — per-session context-bar baselines.
- `~/.claude/.ecc-session-bridge/` — session metrics for the statusline.
- `D:\Projects\super_code\hermes-agent\claude_code_integration\ruvector.db` and the top-level `ruvector.db` — embeddings / skill state.

All of the above are listed in `.gitignore` and must stay there.

## Load-aware retry runner (hang-prone shell commands)

`scripts/load_retry_runner.py` (installed to `~/.claude/scripts/`, smoketest
`load_retry_runner_smoketest.py`) wraps ONE shell command with three guards:

1. a system-load gate -- hold the launch while total CPU% >= cap (default 92) or
   free RAM < floor (default 2 GB), reading psutil or a CIM/`/proc` fallback, and
   surveying other `claude`/`pwsh`/`powershell`/`node` windows for context;
2. a hard per-attempt timeout that kills the whole process tree (`taskkill /T`),
   so a wedged command never hangs forever;
3. variable/jittered backoff retry until the command succeeds or the
   attempt/overall-deadline budget runs out.

Usage:

```
python ~/.claude/scripts/load_retry_runner.py --probe                      # one load snapshot + window survey
python ~/.claude/scripts/load_retry_runner.py --timeout 15 -- git fetch    # gated + retried
python ~/.claude/scripts/load_retry_runner.py --json --quiet -- <command>  # machine-readable
```

SCOPE + HARD LIMIT (state this honestly, do not over-promise): it protects shell
COMMANDS it launches and MONITORS other windows' load, but it CANNOT route or
revive *harness tool calls* (Agent / Skill / Read / Edit / MCP) -- those are not
shell commands and nothing can interpose a wrapper on them. A frozen interactive
Claude window cannot be resumed from outside (the same wall `window_watchdog.py`
documents). To identify WHICH tool froze across ALL tool types, read the session
transcript's last `tool_use` that has no matching `tool_result` -- that data
already exists per call, so no per-tool hook is needed.

Kill switch: `LOAD_RETRY_DISABLE=1` (pass-through single run, no gate/retry), or
just don't call it. No daemon, no hook -- nothing persists when it exits.

## Token compression layer (tokenjuice)

`scripts/tokenjuice.py` (installed to `~/.claude/scripts/`, smoketest
`tokenjuice_smoketest.py`) is a DETERMINISTIC, OPT-IN compressor for noisy tool
output: you pipe a known-verbose command through it and a three-layer JSON rule
overlay (builtin < user `~/.claude/tokenjuice/rules/` < project
`./.tokenjuice/rules/`, later overrides earlier by rule `name`) strips the noise
before it costs context. Strategies: strip_ansi, fold_whitespace, dedup_lines,
drop_regex, keep_regex, truncate, summarize_sections, html_to_markdown,
shorten_urls, condense -- all pure rules, no LLM. Inspired by openhuman's
"TokenJuice"; no code copied.

The `condense` strategy lives in the sibling `scripts/tokenjuice_condense.py`
(installed alongside, smoketest `tokenjuice_condense_smoketest.py`): a
structure-aware condenser for BIG blobs, ported (simplified, stdlib-only,
Apache-2.0 attribution in the module docstring) from the audited
`chopratejas/headroom` compression package -- the headroom package itself stays
do-not-install (see `okf/ai-radar/agent-tooling/headroom.md`); only the audited
pure-text logic was vendored. Auto-detects JSON / code / log / text: JSON keeps
every key + schema + short/ID-like values, code keeps imports + signatures,
logs keep errors/traces/summaries with context, and high-entropy words (API
keys, UUIDs, hashes) always survive squeezing. Measured on a 24K-char JSON API
dump: the command-oriented rules alone saved 0%, condense ~54% with the full
schema intact. Use via `{"type": "condense"}` in a rule, the `--condense` CLI
flag, or standalone: `python ~/.claude/scripts/tokenjuice_condense.py --file
big.json`. Lazy import, silent no-op if the module is missing; same kill
switch (`TOKENJUICE_DISABLE=1`). Full rationale + the harness limit (a hook cannot rewrite a tool
result, so this is opt-in not automatic) and usage are in the global
`~/.claude/CLAUDE.md` under "Token compression layer (tokenjuice)" and mirrored in
`home_dotclaude/CLAUDE.md`.

```
python ~/.claude/scripts/tokenjuice.py -- git status         # run + compress
some-noisy-cmd | python ~/.claude/scripts/tokenjuice.py --for "some-noisy-cmd"
python ~/.claude/scripts/tokenjuice.py --probe --for "cargo build"   # dry-run match
```

Same change discipline as the hooks: keep the silent no-op-on-bad-input pattern
(a malformed rule / strategy is skipped, never fatal), run `tokenjuice_smoketest.py`
before trusting a change, and after editing `scripts/tokenjuice.py` copy it to
`~/.claude/scripts/` for it to take effect. Kill switch: `TOKENJUICE_DISABLE=1`
(or `--raw`) -> pass-through, uncompressed.

## Cross-window coordination (coord.py + work.md)

`scripts/coord.py` (installed to `~/.claude/scripts/`, smoketests
`coord_smoketest.py` + `coord_prompt_hook_smoketest.py` +
`coord_sessionstart_hook_smoketest.py`) lets concurrent Claude
windows on the same repo self-coordinate who edits/commits/merges which files,
and hand work off, with zero user questions. Each window registers in a shared,
UNTRACKED journal at `~/.claude/.coord/<repo-key>/` (`state.json` truth,
`work.md` rendered board, `.lock` cross-process lock); the key is
`git rev-parse --git-common-dir` so all worktrees/branches of one repo share ONE
board. The model never hand-edits `work.md` (two windows Edit-ing one file
clobber) -- it mutates the board only via the lock-safe CLI.

It is automatic at startup: `coord_sessionstart_hook.py` (wired in `settings.json`
SessionStart) registers the window the moment Claude Code opens and injects the
standing protocol -- so the window knows what to do with NO pasted command. The
per-turn driver is `coord_prompt_hook.py`, wired into the
`UserPromptSubmit` dispatcher (REGISTRY in `hook_dispatch.py`): every turn it
refreshes this window's heartbeat, GCs silent windows (their claims free up
after `COORD_STALE_SECONDS`, default 1800s), re-renders `work.md`, and injects a
`[coordination]` block with the other live windows, the files they hold, and any
requests addressed to this window. A solo window injects nothing.

```
python ~/.claude/scripts/coord.py status                         # print work.md
python ~/.claude/scripts/coord.py claim src/foo.py               # lease a file (exit 3 on conflict)
python ~/.claude/scripts/coord.py release src/foo.py             # free it
python ~/.claude/scripts/coord.py request --to <sid|branch|*> --note "merge X into main"
python ~/.claude/scripts/coord.py reply <id> --note "..."        # answer a request (-> back to asker)
python ~/.claude/scripts/coord.py ack <id>                       # close out an answer you read
python ~/.claude/scripts/coord.py inbox                          # compact: requests + answers for me
python ~/.claude/scripts/coord.py resolve <id> --status done     # close a request
python ~/.claude/scripts/coord.py done                           # leave the board (qClose does this)
```

The auto-relay loop + decision-gate (looped windows carry questions/answers
themselves but PAUSE for the user before any irreversible op -- merge to main,
push, rebase of live files) and the same-project scoping (coord is per-repo via
`git-common-dir`, so windows in different projects can NEVER coordinate or
auto-merge across each other) are documented in the global `~/.claude/CLAUDE.md`
under "Auto-relay loop + decision-gate".

The behaviour rule Claude follows (claim before editing, request for
cross-branch handoffs, act on requests addressed to you) and the HARD LIMIT
(coordination is PULL-based: a posted request is acted on by the target window
on ITS next turn, not pushed instantly) live in the global `~/.claude/CLAUDE.md`
under "Cross-window coordination (coord.py + work.md)". Same change discipline as
the hooks: silent no-op on bad input, run both smoketests before trusting a
change, and after editing `scripts/coord.py` / `coord_prompt_hook.py` copy them
to `~/.claude/scripts/` for the change to take effect (the dispatcher loads the
installed copies). Kill switch: `COORD_DISABLE=1` (CLI + hook become no-ops),
remove `coord_prompt_hook` from `hook_dispatch.py` REGISTRY, or delete
`~/.claude/.coord/<key>/`.
