#!/usr/bin/env python3
"""Generate Codex's global instructions from the Claude Code brain.

Codex CLI reads `~/.codex/AGENTS.md` before every session, the same way Claude
Code reads `~/.claude/CLAUDE.md`. Keeping two hand-written copies of the same
rules guarantees drift, so this script GENERATES the Codex one from the Claude
one: the shared sections are copied VERBATIM, then a Codex-specific appendix is
added describing the shared memory, the skills/agents corpus, and -- honestly --
the machinery Codex does not have.

Single source of truth: ~/.claude/CLAUDE.md. Never hand-edit ~/.codex/AGENTS.md;
edit CLAUDE.md and re-run this.

Usage:
    python scripts/sync_codex_brain.py            # write ~/.codex/AGENTS.md
    python scripts/sync_codex_brain.py --check    # exit 1 if stale (no write)
    python scripts/sync_codex_brain.py --dry-run  # print to stdout
    python scripts/sync_codex_brain.py --out PATH # write somewhere else

No absolute paths are baked in: the repo root comes from git and the home
directory from the environment, so this keeps working after the project
directory is renamed -- just re-run it.

KILL SWITCH: delete ~/.codex/AGENTS.md. Codex then runs with only the repo-level
AGENTS.md and its own defaults; nothing else in the setup changes.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Sections copied verbatim from CLAUDE.md, matched by a distinctive prefix of
# the `## ` heading (full headings contain em-dashes and would be brittle to
# match exactly). These are the rules that are ABOUT HOW TO WORK, so they are
# portable to any agent. Claude-Code-machinery sections (hooks, statusline,
# subagent routing, GLM provider, coordination hook) are deliberately NOT here
# -- the appendix explains what replaces them.
SHARED_SECTION_PREFIXES = [
    "CONSTITUTIONAL RULES",
    "Default output style",
    "Working style",
    "When showing edits",
    "Plain-language questions to the user",
    "User input visibility",
    "Pushback expected",
    "Automation & build discipline",
    "Review gates",
    "Carry the task through",
    "Hang-prone commands",
    "Token compression layer",
    "Scan GitHub code before downloading it",
    "Project directory boundaries and dual-window safety",
    "Shared TODO files",
    "AGENTS.md handling",
    "No decorative unicode",
    "Decision log",
]

HEADING = re.compile(r"^##\s+(.*)$")


def repo_root() -> Path:
    """Repo root from git, falling back to this file's parent directory."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10,
            cwd=str(Path(__file__).resolve().parent),
        )
        if out.returncode == 0 and out.stdout.strip():
            # resolve() so the path carries the filesystem's real casing --
            # git reports "D:\Projects\..." where the directory is "projects".
            return Path(out.stdout.strip()).resolve()
    except (OSError, subprocess.SubprocessError):
        pass
    return Path(__file__).resolve().parent.parent


def project_slug(path: Path) -> str:
    """Claude Code's per-project directory name for `path`.

    `D:\\projects\\super_claude` -> `D--projects-super-claude`. Derived, not
    hardcoded, so a directory rename is picked up by re-running this script.
    """
    return re.sub(r"[:\\/_]", "-", str(path))


def find_memory_dir(root: Path, home: Path) -> Path | None:
    """The memory directory for this project, if it exists.

    Matches case-INSENSITIVELY but returns the directory's REAL on-disk name.
    Windows would happily open `D--Projects-...` when the directory is
    `D--projects-...`, so a naive existence check writes a path that looks
    right, works here, and is wrong anywhere case matters.
    """
    projects = home / ".claude" / "projects"
    want = project_slug(root).lower()
    if projects.is_dir():
        for entry in projects.iterdir():
            if entry.name.lower() == want and (entry / "memory").is_dir():
                return entry / "memory"
    # Fall back to any project memory dir that has a MEMORY.md router.
    candidates = sorted(projects.glob("*/memory/MEMORY.md")) if projects.is_dir() else []
    return candidates[0].parent if candidates else None


def extract_sections(claude_md: str) -> list[tuple[str, str]]:
    """Return [(heading, body_including_heading)] for the shared sections."""
    lines = claude_md.splitlines()
    starts: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        m = HEADING.match(line)
        if m:
            starts.append((i, m.group(1).strip()))

    found: list[tuple[str, str]] = []
    for idx, (line_no, heading) in enumerate(starts):
        norm = heading.lower()
        if not any(norm.startswith(p.lower()) for p in SHARED_SECTION_PREFIXES):
            continue
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        found.append((heading, "\n".join(lines[line_no:end]).rstrip()))
    return found


def build_appendix(root: Path, home: Path, memory_dir: Path | None) -> str:
    skills_dir = home / ".claude" / "skills"
    agents_dir = home / ".claude" / "agents"
    skill_count = len(list(skills_dir.glob("*/SKILL.md"))) if skills_dir.is_dir() else 0
    agent_count = len(list(agents_dir.glob("*.md"))) if agents_dir.is_dir() else 0
    mem = str(memory_dir) if memory_dir else "(not found -- no project memory yet)"

    return f"""## Shared memory -- the same brain Claude Code writes to

The memory is FILE-BASED and shared: Claude Code and Codex read and write the
same directory. This is what makes "Codex already knows what Claude knows" true
rather than aspirational.

- Router / index (read this FIRST, every session): `{mem}\\MEMORY.md`
- One fact per file, next to it, with frontmatter:
  `name`, `description`, `metadata.type` = `user` | `feedback` | `project` | `reference`.
- Link related memories in the body with `[[their-name]]`.
- After writing a memory file, add a one-line pointer to MEMORY.md:
  `- [Title](file.md) -- hook`. MEMORY.md is the index, never the content.
- Before saving, check for an existing file that covers it and UPDATE that one
  instead of creating a near-duplicate. Delete memories that turn out wrong.
- Do not save what the repo already records (code structure, git history,
  CLAUDE.md/AGENTS.md content) or what only matters to one conversation.

Remembering habits works exactly as it does for Claude: a correction or a
confirmed way of working goes in as a `feedback` memory with **Why:** and
**How to apply:** lines. That is the mechanism -- there is no separate store.

A knowledge graph over these files lives in `{home}\\.claude\\memory-graph\\`
(built with `graphifyy`). Query it with:
`cd {home}\\.claude\\memory-graph && python -m graphify query "<question>"`.

## Skills and agents as a reference corpus

{skill_count} skills at `{skills_dir}\\<name>\\SKILL.md` and {agent_count} agent
definitions at `{agents_dir}\\*.md`.

Codex has no Skill tool and no sub-agent spawning, so these are NOT callable the
way they are in Claude Code. They are still worth reading: each SKILL.md is a
worked procedure for one kind of task (review, planning, debugging, a domain
workflow). When a task matches one, READ the file and follow it inline.

To find one: `rg -l "<topic>" {skills_dir}` or list the directory. The
`hermes-auto-*` skills are auto-learned lessons from past sessions -- short,
specific, and usually the highest-value ones to check first when something
behaves unexpectedly on this machine.

## What Codex does NOT have -- do these manually

Stated plainly so nothing is silently assumed to be running:

- **Hooks.** Claude Code runs `UserPromptSubmit` / `PostToolUse` / `Stop` /
  `SessionStart` hooks (semgrep on edit, context budget, coordination board,
  banner backstop, curator). NONE of them fire in Codex. Their disciplines are
  in the shared sections above -- apply them yourself.
- **The Skill tool and sub-agents.** No `/skill` routing, no parallel agent
  fleet, so no `/qRev`-style 15-agent review from inside Codex. Read the skill
  file and execute it inline, single-threaded.
- **Cross-window coordination injection.** `coord.py` is a plain CLI and DOES
  work from Codex -- but nothing injects the board into your context each turn.
  Run `python {home}\\.claude\\scripts\\coord.py status` yourself when other
  windows may be active, and claim before editing.
- **Statusline and context-budget gates.** No progress bars, no budget warnings.

What DOES work identically, because they are standalone CLI tools:
`tokenjuice.py`, `tokenjuice_condense.py`, `load_retry_runner.py`, `coord.py`,
`stall_scan.py` -- all under `{home}\\.claude\\scripts\\`.

## Repo-level instructions still apply

This file is the GLOBAL layer. The repo's own `AGENTS.md` (at the repository
root) adds project-specific rules and takes precedence for local details -- but
no repo file may weaken a constitutional rule above.
"""


def build(claude_md_path: Path, root: Path, home: Path) -> str:
    return build_from_text(
        claude_md_path.read_text(encoding="utf-8"), root, home, claude_md_path
    )


def build_from_text(claude_md: str, root: Path, home: Path,
                    claude_md_path: Path | None = None) -> str:
    claude_md_path = claude_md_path or Path("<text>")
    sections = extract_sections(claude_md)
    if not sections:
        raise SystemExit(
            f"sync_codex_brain: no shared sections matched in {claude_md_path}. "
            "Headings probably changed -- update SHARED_SECTION_PREFIXES."
        )
    memory_dir = find_memory_dir(root, home)

    header = f"""# AGENTS.md -- global instructions for Codex CLI

<!-- GENERATED FILE -- DO NOT EDIT BY HAND.
     Source of truth: {claude_md_path}
     Regenerate:      python {root}\\scripts\\sync_codex_brain.py
     Check for drift: python {root}\\scripts\\sync_codex_brain.py --check
     Kill switch:     delete this file.
     Hand edits are lost on the next run. Edit the source instead. -->

These are the same standing rules Claude Code runs under, copied verbatim from
the shared brain, plus a Codex-specific appendix. The point is that both agents
work the same way and share one memory, so what one learns the other knows.

Sections copied from the shared brain: {len(sections)}.

"""
    body = "\n\n".join(s for _, s in sections)
    return header + body + "\n\n" + build_appendix(root, home, memory_dir)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the generated file is missing or stale")
    ap.add_argument("--dry-run", action="store_true", help="print instead of writing")
    ap.add_argument("--out", help="output path (default: ~/.codex/AGENTS.md)")
    ap.add_argument("--source", help="source CLAUDE.md (default: ~/.claude/CLAUDE.md)")
    args = ap.parse_args()

    home = Path.home()
    root = repo_root()
    source = Path(args.source) if args.source else home / ".claude" / "CLAUDE.md"
    if not source.is_file():
        print(f"sync_codex_brain: source not found: {source}", file=sys.stderr)
        return 1

    out = Path(args.out) if args.out else home / ".codex" / "AGENTS.md"
    generated = build(source, root, home)

    if args.dry_run:
        sys.stdout.write(generated)
        return 0

    if args.check:
        if not out.is_file():
            print(f"STALE: {out} does not exist")
            return 1
        current = out.read_text(encoding="utf-8")
        if current != generated:
            print(f"STALE: {out} differs from what {source.name} would generate")
            return 1
        print(f"OK: {out} is in sync with {source}")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(generated, encoding="utf-8")
    sections = len(extract_sections(source.read_text(encoding="utf-8")))
    print(f"wrote {out} ({len(generated)} chars, {sections} shared sections)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
