# AGENTS.md -- super_code project

This file extends the global `~/.config/opencode/AGENTS.md` with rules specific to this repo.

## Project shape

`super_code` is a personal Claude Code / OpenCode setup:
- `scripts/` -- hook scripts, tokenjuice, coord, load_retry_runner, etc.
- `hermes-agent/claude_code_integration/` -- curator, smart router, decision log modules
- `claude_skills_backup/` -- ~165 Claude Code skills (markdown)
- `home_dotclaude/` -- global config templates

**For OpenCode use:** the Python scripts in `scripts/` are standalone CLI tools, usable directly:
- `python scripts/tokenjuice.py -- <cmd>` -- compress noisy shell output
- `python scripts/tokenjuice_condense.py --file <path>` -- compress big blobs
- `python scripts/load_retry_runner.py -- <cmd>` -- load-gated + retried command
- `python scripts/coord.py status` -- show cross-window coordination board (Claude Code only)
- `python scripts/stall_scan.py` -- scan transcript for stalled tool calls (Claude Code only)

## No decorative unicode

Never write decorative unicode into executable code or shell commands (see global AGENTS.md for the full list). Use ASCII equivalents: `[ok]`, `[fail]`, `[warn]`, `->`, `-`, `note:`.

## Hooks (Claude Code-specific)

The hook scripts in `scripts/` and `~/.claude/scripts/` run automatically in Claude Code sessions. They are NOT active in OpenCode -- they require Claude Code's hook system (UserPromptSubmit, PostToolUse, Stop, etc.). When working in OpenCode, apply the disciplines they enforce manually:
- Token compression: pipe verbose commands through `tokenjuice.py`
- Context budget: keep responses dense; prefer delegation over dumping files

## Key utilities available to OpenCode

These scripts work without Claude Code and are useful from any terminal or as `bash` tool calls:

```
# Compress noisy command output before reading it
python D:\Projects\super_code\scripts\tokenjuice.py -- git log --oneline -20

# Compress a big file before passing it to the model
python D:\Projects\super_code\scripts\tokenjuice_condense.py --file big_file.json

# Load-gated retry runner for hang-prone commands
python D:\Projects\super_code\scripts\load_retry_runner.py --timeout 30 -- npm test
```

## State files (gitignored, don't commit)

- `~/.claude/.hermes_curator_queue.json` -- Claude Code curator queue
- `~/.claude/.qrev_auto_state.json` -- Claude Code review counters
- `hermes-agent/claude_code_integration/ruvector.db` -- embeddings
- `exclude/` -- gitignored local state (TODO, SYSTEM_STATUS, etc.)
