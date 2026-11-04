---
name: radar-scan
description: Weekly sweep that learns what is new/better in AI into the AI Radar OKF bundle AND acts on it — sweep, refresh stale entries, adopt findings as real repo changes, self-tune its own runbook. Follows okf/ai-radar/ROUTINE.md (shared with the cloud routine). Invoked via /radar-scan [topic] (case-insensitive).
---

# radar-scan — sweep, refresh, adopt, self-tune

The AUTO half of the hybrid intake (manual half = `/radar-add`). Bundle source
of truth: `D:\Projects\super_code\okf\ai-radar\`; live mirror
`~/.claude/okf/ai-radar/`.

## The runbook is a file, not this skill

Read `okf/ai-radar/ROUTINE.md` first and follow its steps 1-5 (sweep, refresh,
adopt, self-tune, report). Seeds, freshness windows and lessons live there in
the TUNABLE sections, so both this skill and the weekly cloud routine
(`trig_01SfqhMbYrnRqQwbk4XSQKHp`) pick up every improvement. The LOCKED
guardrails section in that file applies here too.

`/radar-scan <topic>` limits step 1 to one topic from the Seeds table.

## Local-only differences

- **Extra search angles** the cloud sandbox lacks:
  ```bash
  yt-dlp "ytsearch8:<seed phrase>" --flat-playlist \
    --print "%(title)s | %(id)s | %(upload_date)s | %(channel)s"
  python "$HOME/.claude/skills/hermes-youtube-content/scripts/fetch_transcript.py" "https://youtube.com/watch?v=<id>"
  ```
  arXiv via `hermes-arxiv` for knowledge / cognition / agent-tooling.
- **Scan-before-trust** via the `skillspector-gate` skill (local install at
  `~/.claude/tools/skillspector`).
- **Adopt step** works on local branches `radar/adopt-<date>-<slug>` and does
  NOT push. Class A/B items can also be checked against the local machine
  (installed versions, `~/.claude/settings.json`), which the cloud cannot see —
  prefer resolving class C queue items here.
- **Project matching (local only).** Read `~/.ai-radar/projects/*.md` (private
  per-project inventories: components, versions, upgrade paths, feature log).
  For every new finding and every watchlist check, decide which project
  components it touches and how to upgrade them. Write those per-project notes
  ONLY into the matching `~/.ai-radar/projects/<project>.md` under a
  `# Radar notes` heading (newest first), never into `okf/` (public repo,
  ROUTINE.md guardrail 8). Also run the step 1c upgrade check for the packages
  that are deliberately NOT in the public `watchlist.md` (listed in the private
  inventories only). Material hits -> a class C item in `adoption-queue.md`
  worded without project names, plus the detail in the private file.
- **No commit / push** from this skill: disk only; committing is a separate
  gated step. Sync changed files to `~/.claude/okf/ai-radar/` at the end.
- **Routine health:** run `python ~/.claude/scripts/radar_health.py --verbose`
  first; a stale line means the cloud routine is not landing (see the 403
  lesson in ROUTINE.md). qRem runs the same check silently every session.

## Kill switches

- `self_improve: off` in ROUTINE.md frontmatter -> sweep + lint only.
- `AI_RADAR_DISABLE=1` silences the downstream gate "speak up".
- Disable the cloud trigger (`enabled: false`) to stop the weekly run; deleting
  `okf/` removes the capability.
