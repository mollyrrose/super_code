# INDEX — super_code

Orientation map for a fresh session. For the full feature catalog see `README.md`.

## Token discipline (STANDING — every session, both tools always in use)

Every session, from the first turn, the model applies the token compressors by
default as a reflex — this is a standing rule, loaded here + in `CLAUDE.md`, so a
fresh clone of super_code gets it automatically. There is nothing to "start"
(they are on-demand scripts, not daemons); "always on" means the model reaches
for them continuously without being asked:

1. Delegate multi-file reads to subagents that return conclusions, not dumps.
2. Pipe KNOWN-noisy shell commands through tokenjuice:
   `python ~/.claude/scripts/tokenjuice.py -- <command>`.
3. Condense BIG structured/prose blobs before reading whole or handing to an
   agent: `python ~/.claude/scripts/tokenjuice_condense.py --file <path>` (or
   `tokenjuice --condense -- <command>`). Measured 37-69% on JSON/code/prose.

It cannot be a silent auto-interceptor (a hook cannot rewrite a Read/Grep/MCP
tool result before the model sees it, and auto-wrapping every Bash command would
break exact-output/interactive commands), so it is realized as this
model-discipline rule, not a daemon. Full rule + rationale: `CLAUDE.md` "Token
compression layer (tokenjuice)" and the global `~/.claude/CLAUDE.md` STANDING
TOKEN DISCIPLINE block.

## What this is

`super_code` is the personal Claude Code setup: hook scripts, the curator /
skill-lifecycle Python, a backup of the installed skills, and the project-level
rules in `CLAUDE.md`. Editing here changes how every Claude Code session behaves.

## Key entry points

- `CLAUDE.md` — project rules (extends the global `~/.claude/CLAUDE.md`).
- `~/.claude/settings.json` — the live hook chain (not in this repo). Hooks point
  at `~/.claude/scripts/*` and `hermes-agent/claude_code_integration/*`.
- `scripts/` — tracked copies of hook/runtime scripts, installed to
  `~/.claude/scripts/`. Notably `context_budget_gate.py` (+ smoketest),
  `statusline_with_weekly.js`, and `claude-glm.ps1` (GLM/z.ai launcher).
- `hermes-agent/claude_code_integration/` — curator, `smart_router_*`,
  `decision_log_cli.py`, `mark_drained_cli.py`.
- `hermes-agent/claude_skills_backup/` — backup of installed skills, including the
  `q*` commands (qPlan/qRev/qMin/qClose/qRem/qUpd/qDo/qContent), the vendored
  `arbor-*` engine, `ponytail*`, `improve`, `drawio-skill`, `skillspector-gate`,
  and an 11-skill subset vendored from `K-Dense-AI/scientific-agent-skills` (MIT):
  `statistical-analysis`, `statistical-power`, `experimental-design`,
  `exploratory-data-analysis`, `uncertainty-and-units`, `scientific-critical-thinking`,
  `peer-review`, `polars`, `networkx`, `markdown-mermaid-writing`,
  `citation-management`. Domain-agnostic only — the other 152 skills in that repo
  are bio/chem/lab specific and were deliberately left out to keep the always-on
  skill index small. Each vendored copy has the upstream "Citing Scientific Agent
  Skills" block removed (it instructed the agent to insert K-Dense's arXiv paper
  into the user's own deliverables). Plus the three Anthropic document skills
  `pdf`, `docx`, `xlsx` (Anthropic license, `LICENSE.txt` kept in each). `pdf`
  comes from `anthropics/skills` upstream; `docx` and `xlsx` deliberately come
  from the K-Dense vendored copy instead, because upstream
  `scripts/office/soffice.py` still writes its LD_PRELOAD shim to the fixed path
  `tempfile.gettempdir()/lo_socket_shim.so` and reuses whatever already sits
  there without an owner or permission check. The K-Dense copy creates the shim
  in a per-process `tempfile.mkdtemp()` directory. Inert on Windows (per-user
  temp, LD_PRELOAD is Linux-only) but it matters under WSL or in a container.
- `~/.claude/tools/skillspector/` — the security scanner (not in this repo).
  Reinstall with `uv venv .venv --python 3.12` + `uv pip install "skillspector @
  git+https://github.com/NVIDIA/skillspector.git"` in that directory. Python 3.12,
  not 3.14: `yara-python` has no 3.14 wheel and would need MSVC build tools.
- `home_dotclaude/` — sanitized mirror of the live `~/.claude/` config that is
  worth version-tracking: `CLAUDE.md` and `settings.json`. The live files stay
  outside the repo; these are copies kept in sync by hand when the config
  changes.
- `docs/decisions/log.md` — decision log (ADR-style).
- `docs/crush-vs-claude-code.md` — honest Crush (charmbracelet/crush) analysis +
  how it's wired here (secondary tool on the local llama.cpp model; `crush.json`
  gitignored, template `crush.json.example`, notes in `CRUSH.md`).
- `docs/base44-handoff.md` — free-path runbook for editing Base44 apps as code
  from Claude Code (base44 CLI + official `base44-*` skills; `base44 login` + docs
  MCP are user-run steps).

## Username placeholder convention (`[USER]`)

Tracked files must NOT contain the real Windows username. Anywhere a real home
path appears in a *committed* file, the user segment is written as the literal
placeholder `[USER]` — i.e. `C:/Users/[USER]/...` (or `C:\Users\[USER]\...`) —
so the repo is machine-agnostic and the username is never published.

- This applies to docs/skill backups and the `home_dotclaude/` mirror, e.g.
  `home_dotclaude/settings.json`, `hermes-agent/claude_skills_backup/*/SKILL.md`.
- The LIVE files under `~/.claude/` keep the REAL path — never sanitize those,
  or the hooks/scripts that run from absolute paths break. Sanitization is a
  repo-only transform applied when mirroring/committing.
- When copying a live config or script into the repo, replace the real Windows
  user-name segment (whatever `C:\Users\<name>\` resolves to on the authoring
  machine) with `[USER]` before committing. A consumer on another machine
  substitutes their own username back in. (This doc deliberately does not spell
  out the real name — that would re-leak it.)
- Note: other machine-specific roots that are NOT the username (e.g.
  `C:\Python313`, `D:\Projects\super_code`) are left as-is — only the user
  segment is placeholdered.
- SECRETS: the live `settings.json` carries real API keys in `env`
  (`OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, and any future provider key). The
  mirror MUST redact every key value to `[REDACTED — ...]` before committing.
  GitHub push-protection will (correctly) block a push that contains a real
  key, so redacting is mandatory, not optional. When re-syncing the mirror,
  re-run the redaction every time.

## How to run / test

- Hooks run automatically via `~/.claude/settings.json`; changing a hook means
  editing the tracked copy in `scripts/` and copying it to `~/.claude/scripts/`.
- Smoke tests live next to their scripts, e.g.
  `python scripts/context_budget_gate_smoketest.py` (6 cases).
- `/qGoal <goal>` is the autonomous executor (the only q-command that touches
  code): it plans via `/qPlan`, runs a single path or multiple variants as the
  task warrants (Arbor backend `arbor-agent-tools/scripts/arbor_state.py`,
  stdlib-only), consults `/qPlan` at decision points, and runs `/qRev` + fixes at
  the end. `/qPlan` stays plan-only (the brain). `/qPlan auto` is retired -> `/qGoal`.
- Before installing any external GitHub skill, the `skillspector-gate` rule scans
  it first.

## Local-only state (gitignored)

All per-project working state lives under `exclude/SYSTEM_STRATEGIES/` (the
whole `exclude/` tree is gitignored, mandatory):
- `exclude/SYSTEM_STRATEGIES/TODO.md` — canonical task list,
- `exclude/SYSTEM_STRATEGIES/SYSTEM_STATUS.md` — system snapshot,
- `exclude/SYSTEM_STRATEGIES/system_map.drawio` — architecture diagram.

Plus run/scratch state: `.arbor/`, `.qplan/`, `.scratch/`. See `.gitignore`.
