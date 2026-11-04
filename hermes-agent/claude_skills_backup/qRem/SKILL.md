---
name: qRem
description: Refresh project orientation — read INDEX.md, STARTUP.md, exclude/SYSTEM_STRATEGIES/TODO.md and survey the latest 5 git commits — before starting non-trivial work in a project repo.
---

# qRem — Quick Remember

## When to use

Invoke at the start of a session, or before non-trivial work in an unfamiliar project. Skip in tiny one-shot tasks where the context is already obvious from the user's message.

## What to do

1. Check whether the working directory is a git repo (`git rev-parse --is-inside-work-tree`). If not, stop and tell the user — qRem is repo-scoped.
2. Find the task list first: read `exclude/SYSTEM_STRATEGIES/TODO.md` if it exists (the canonical location), else an older `exclude/TODO.md`, else a root `TODO.md`. Then read whichever of these also exist: `INDEX.md`, `STARTUP.md`, `AGENTS.md`, and `exclude/SYSTEM_STRATEGIES/SYSTEM_STATUS.md` (`INDEX.md` is at the project root). Read `README.md` only as a fallback when `INDEX.md` is absent (it is the narrative source of last resort). If any are missing, note it once; do not create them unless the user asks.
3. Run `git log -5 --oneline` (or `--stat` if the user wants more detail) to see the latest five commits.
4. **Remote-drift check (pull hint).** Run `git fetch --quiet` (skip silently if it fails — offline, no remote, or no credentials), then `git status -sb`. If the current branch is BEHIND its upstream, add ONE line to the orientation summary: `[pull] origin/<branch> is N commit(s) ahead — likely a cloud routine (e.g. the AI Radar weekly scan, Tuesdays) or another machine; say "pull" to fast-forward.` Detection only: never pull automatically, stay silent when in sync, and skip entirely when there is no upstream. Then run `python ~/.claude/scripts/radar_health.py` (read-only, silent when healthy, always exit 0): if it prints a `[radar] ... has not landed for N days` line, add that line to the summary verbatim -- the weekly cloud routine is dying silently (as 2026-09-15..11-03 did with a 403).
5. Produce a 4–8 line orientation summary: project purpose (from INDEX/README if available), what's in flight (from TODO, current branch name), what changed recently (from git log), and any immediate concerns or open threads.
6. **Fable legacy (always read in full).** Read `~/.claude/fable-legacy/FABLE5_LEGACY.md` in FULL every qRem orientation, regardless of the active model — the complete distilled intelligence protocol (36 failure-mode names, 12-item pre-send review, 8 character foundations, craft appendices). This is deliberate: the earlier index-only + on-demand chapter approach never actually pulled a chapter in practice (verified 2026-08-29), so the whole doc is loaded every time to guarantee the failure-mode vocabulary and pre-send checklist are active. If `FABLE5_LEGACY.md` is absent, fall back to `~/.claude/fable-legacy/FABLE5_LEGACY_INDEX.md`; if neither exists, skip silently. Kill switch: `FABLE_LEGACY_DISABLE=1`.
7. **Radar gate (optional, strict, kill-switched).** Unless `AI_RADAR_DISABLE=1` or the AI Radar bundle (`~/.claude/okf/ai-radar/`) is absent, run the `/radar-check` gate logic: compare this project's model pins / key deps / named patterns against radar entries marked `status: superseded` or carrying a `supersedes`. Append AT MOST one or two `[radar] ...` lines for material, high-confidence hits ("you use X; Y is now better/safer because Z — resource"). If nothing strongly qualifies, emit nothing. Honor no-nagging: silence is the default; never interrupt, never auto-change anything.
8. **Radar applicability review (only when a radar pull happened).** If a pull during this qRem (step 4, or one the user asked for) touched `okf/ai-radar/`: first sync the repo bundle into the live `~/.claude/okf/ai-radar/` — add/update only, NEVER delete live-only entries, and MERGE index files rather than overwrite (live indexes may list local-only entries). Then read the newest block of `okf/ai-radar/log.md` to see what is new/updated, open those entries, and weigh them against THIS project's `exclude/SYSTEM_STRATEGIES/SYSTEM_STATUS.md` and TODO: what is concretely usable here, where it would plug in, rough effort. Present that shortlist as a PROPOSAL and ask permission (USER INPUT banner) — never adopt anything autonomously. If nothing is materially applicable, say so in one line and move on. No-nagging still applies: propose only material, high-confidence fits.

## Do not

- Do not edit `INDEX.md` / `STARTUP.md` / `exclude/SYSTEM_STRATEGIES/TODO.md` / `TODO.md` automatically. Updates to these files happen only when the user explicitly asks, or when work in this session has materially changed their content and the user has confirmed.
- Do not run this skill repeatedly inside one session unless the user requests a re-orient (e.g. after a branch switch).
- Do not invent these files where they do not exist.
