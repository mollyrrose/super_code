# /qpickup — resume a frozen sibling window, or sync task division

This is the Codex-native counterpart of Claude Code's `/qPickUp` skill. Same
repo, same coordination board, same two modes — adapted for running under
`codex` instead of `claude`. If this file's `$ARGUMENTS` placeholder below
did not get substituted for you (you see the literal text `$ARGUMENTS`),
treat EVERYTHING the user typed after `/qpickup` in their message as the
argument text instead — do not ask them to retype it.

Argument text: `$ARGUMENTS`

## Why this exists

A Claude Code or Codex window on this repo can freeze, crash, or get closed
by accident before it finishes its work or gets a chance to hand off
gracefully. The user is left with, at best, a copied fragment of what that
window was doing — a chunk of code, an error, a half-written plan — and
often just a headcount of how many windows are currently open on the repo.
**You must never require the user to narrate "a window froze, here's where
it stopped, continue from there."** That reconstruction is your job, done
from disk: the cross-window coordination board (`coord.py`, works
identically regardless of which CLI is running it — it's a plain Python
script), the frozen window's own session transcript (still on disk even
though the window is gone), git state, and the project's TODO/roadmap.

## Mode is decided by the SHAPE of the argument text, not a flag

1. Trim the argument text. If it starts with a bare integer followed by
   whitespace or nothing else, peel that off as `window_count_hint` — a
   cross-check only, never authoritative (ground truth is always the live
   coordination board, read in step 1 of whichever mode runs below).
2. What remains after peeling the optional number decides the mode:
   - **Non-empty remainder** (a code block, a pasted chat fragment, an
     error message, a TODO line, one sentence — any shape) -> **Mode A
     (PICKUP)**.
   - **Nothing left** (the whole input was just the number, or there was no
     input at all) -> **Mode B (SYNC)**.
3. If the argument text was completely empty and there's no number either:
   check whether the user's actual chat message (the one invoking this
   prompt) contains something nearby that already reads like a
   frozen-window fragment they pasted instead of formally routing it
   through the command. If so, use that as Mode A's input. Only fall
   through to Mode B with no hint if truly nothing resembling a fragment
   exists.

Examples:
- `/qpickup 3 <pasted code>` -> Mode A, count hint 3.
- `/qpickup <pasted code>` -> Mode A, no count hint.
- `/qpickup 3` (just the digit) -> Mode B, count hint 3.
- `/qpickup` (nothing) -> infer per step 3.

Never ask "which mode?" — the shape already answers it.

## Repo-local rules you must load yourself (Codex has no auto-injected CLAUDE.md)

Before doing anything else: if the repo has a root `CLAUDE.md` and/or
`AGENTS.md`, read it — those carry the project's actual coordination and
git-safety rules (this prompt embeds only what's load-bearing for pickup
itself, below; the repo file is the source of truth if the two ever
disagree). If neither exists, proceed on the embedded rules alone.

**Embedded invariants (do not skip these even if the repo docs are silent):**
- Coordination is PULL-based: a message posted to another window is only
  seen on ITS next turn, never instantly. Don't sit idle waiting for a
  reply — claim your piece and start working it.
- Never run `git push`, a merge/rebase onto a shared or live branch, a
  force-update, or any delete without stopping and getting explicit
  approval from the user first. Everything else (reading, editing the
  working tree, local commits, running tests) needs no such gate.
- Claim a file via the board before editing it if any other window might
  also be touching this repo; never silently take over a file a currently
  LIVE window holds.

---

## Mode A — PICKUP (reconstruct and resume a frozen window)

### Step 1 — quick orientation (Codex has no /qRem to delegate to)

Read whichever of these exist at the repo root: `INDEX.md`, `README.md`,
`exclude/SYSTEM_STRATEGIES/TODO.md` (or `TODO.md`), and run
`git log -5 --oneline`. This is baseline context only — the frozen window's
own state (steps 2-3) is the actual source of truth for what to resume.

### Step 2 — read the coordination board

```
python ~/.claude/scripts/coord.py context
python ~/.claude/scripts/coord.py status
```

(If `~/.claude/scripts/coord.py` isn't reachable from this machine/path, try
the repo-local copy at `<repo-root>/scripts/coord.py` instead — same tool,
either path works since it locates its own journal via
`git rev-parse --git-common-dir`.)

`context` returns compact JSON: `others[]` (session short-id, branch, note,
claims — only genuinely LIVE windows appear here), `blocked_paths`,
`requests_for_me`, `answers_for_me`. `status` prints the human-readable
`work.md`, including a **"Recent activity" log** — a frozen window's last
acts (`[<short-id>] claimed <paths>`, `[<short-id>] beat: <note>`) are still
recorded there even though it no longer shows as live. A `claimed` entry
with no matching `released`/`done` from the same short-id is exactly what a
window mid-edit-when-it-died looks like.

If `window_count_hint` doesn't match the live count `context` reports, note
it once later — never block on it.

### Step 3 — reconstruct what the frozen window was doing

Use whichever of these signals are available:

**a) The pasted fragment itself** — file paths, function/skill names, error
text, a task description. Usually enough to know the SUBJECT.

**b) Coord board correlation.** From the Recent Activity log, find the most
recent `claimed`/`beat` entry whose short-id (6 hex chars) is NOT in the
current `context` output's `others[]` — a candidate dead window; its claimed
paths are exactly the files it was mid-edit on.

**c) Session-transcript correlation (richest signal).** Codex session
transcripts live at
`~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-<timestamp>-<uuid>.jsonl`
(confirmed format: JSONL, each line `{timestamp, ordinal, type, payload}`).
The FIRST line of each file has `type: "session_meta"` with a
`payload.cwd` field — filter to files whose `cwd` matches this repo's
absolute path. Among matches, if Step 3b found a short-id, correlate by
timestamp proximity (the coord short-id is a Claude-session id and won't
literally appear in a Codex rollout filename — use the claim's timestamp to
find the Codex rollout active at that moment, if the frozen window was
itself a Codex window). Otherwise sort candidate rollouts by mtime (newest
first) and grep each for a distinctive 8+ character substring from the
pasted fragment until one matches. Read that file's tail (last ~150-300
lines) for the fuller context: the last assistant message, the last tool
calls/results, and any plan/TODO state.
  - If the frozen window was a CLAUDE CODE window instead, its transcripts
    live at `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`, where
    `<encoded-cwd>` is the repo's absolute path with the first `:\` replaced
    by `--` and every remaining `\` or `/` replaced by `-` (e.g.
    `D:\Projects\super_code` -> `D--Projects-super-code`). Apply the same
    mtime/grep matching there if the fragment or context suggests a Claude
    window, not a Codex one.
  - If no transcript directory or matching file is found: say so once and
    continue with (a) + (d) alone — this is expected degradation, not a
    failure to fix.

**d) Git state.** `git status --porcelain`, `git diff --stat`,
`git log -5 --oneline` — uncommitted changes matching (a)/(c) confirm how
far the frozen window got.

**e) Ambiguity.** If multiple plausible targets exist and signals disagree,
pick the best match by recency + distinctiveness, state the pick and why in
one line, and proceed. The user can correct you — that costs one turn, not a
blocked one.

### Step 4 — liveness check before touching anything

For every file/path identified in Step 3, check it against the CURRENT
`context` output's `others[].claims`:

- **Not claimed by any live window** -> safe: claim it —
  `python <coord.py path> claim <path> [<path> ...]`
- **Claimed by a live window** -> someone is still working it; do not take
  it over. Post `python <coord.py path> request --to <short-id> --note "..."`
  asking whether it's still in progress, tell the user in one line, and
  continue picking up whatever OTHER identified files are free.

### Step 5 — post a status note, then resume immediately

```
python <coord.py path> beat --note "picking up <short-id or 'frozen window'>'s work: <one-line what>"
```

Then continue the work immediately. State in one short line what's being
picked up and from which signal it was reconstructed, then act — do not stop
to ask "should I continue?". The only allowed stops: the decision-gate
(push/merge/rebase onto shared branches/delete) and a genuine blocker where
the reconstructed signals actively conflict — in that case, ask ONE targeted
question naming the specific conflict.

### Step 6 — when the picked-up work concludes

`python <coord.py path> release` (bare, or with specific paths) to free what
you claimed, and post a final `beat` note summarizing the outcome.

---

## Mode B — SYNC (no fragment, just a headcount — divide open work)

Runs for `/qpickup 3` (just the digit) or an empty `/qpickup` with nothing to
infer. There is nothing to "resume" — the goal is to align this window with
its sibling(s) instead of guessing or duplicating work.

### Step 1 — find the other live window(s)

```
python <coord.py path> context
```

Read `others[]`: `session` (short id), `branch`, `note`, `claims`. If
`window_count_hint` doesn't match `len(others) + 1`, note it once and trust
the board.

If `others` is empty: no live sibling right now. Say so in one line and fall
back to ordinary orientation (Mode A Step 1) instead of stalling.

### Step 2 — read the open-task source

Look for, in order: `exclude/SYSTEM_STRATEGIES/TODO.md`, `exclude/TODO.md`,
`TODO.md`, `ROADMAP.md` / `roadmap.md`. Parse the open/pending items — a
line already tagged `[w-<code>]` for a LIVE window's code is spoken for;
untagged items or items tagged for a window no longer live are up for grabs.

If none of these files exist: say so, then ask the sibling directly (Step 3)
instead of inventing a task list.

### Step 3 — propose a split, don't wait idle for a reply

Cross-reference open items against each sibling's current `note` + `claims`
— anything overlapping what a sibling already reports doing is theirs; the
rest is unclaimed. Pick the largest coherent unclaimed piece for this
window, post the proposal:

```
python <coord.py path> request --to <short-id-or-*> --note "proposal: you continue <X> (already on it), I'll start <Y> -- shout if it collides"
```

Coordination is PULL-based — the sibling sees this only on its next turn.
**Do not wait idle.** Immediately claim the piece proposed for yourself and
start on it:

```
python <coord.py path> claim <path> [<path> ...]
python <coord.py path> beat --note "syncing with <short-id>: working <Y> per open TODO/roadmap items"
```

State what was proposed, to whom, and what you're starting regardless of
reply — then begin. If a later reply reveals a real conflict, stop that
item, `release` it, and re-pick from the remaining unclaimed list.

### Step 4 — nothing left unclaimed

If everything in the TODO/roadmap is already covered by live siblings,
say so and ask the user for direction — a genuine fork only they can
resolve.

---

## Edge-case matrix

| Situation | Behaviour |
|---|---|
| Not a git repo | Both modes degrade: skip git-state signals, still attempt coord board + transcript correlation |
| `coord.py` unreachable from either path | Say so once; Mode A falls back to fragment + git state + transcript search; Mode B cannot run — say so and stop, don't fabricate a sibling |
| No transcript match found (Mode A) | Proceed on fragment + git state alone; note the gap once |
| `window_count_hint` mismatches the board | Note once, trust the board |
| Multiple plausible frozen sessions | Pick best match, state why, proceed |
| A file Mode A wants is held by a LIVE window | Don't take it; `request` instead, tell the user, keep picking up the rest |
| No TODO/roadmap file (Mode B) | Ask the sibling directly instead of guessing |
| `others[]` empty (Mode B) | No sibling right now; fall back to orientation |
| Reconstructed signals actively disagree | The one allowed non-gate stop: ask ONE question naming the conflict |
| Next step is push/merge/rebase onto shared branch/delete | Decision-gate: stop, propose the exact command, wait |

## What this deliberately does NOT do

- Does NOT require the user to explain that a window froze or where it
  stopped — that's this prompt's job.
- Does NOT silently take over a file a LIVE window currently holds.
- Does NOT invent a task list when no TODO/roadmap exists (Mode B) — asks
  the sibling instead.
- Does NOT wait idle for a sync reply before starting work.
- Does NOT skip the push/merge/rebase/delete decision-gate regardless of how
  the resumed work reads.
- Does NOT treat the leading number as authoritative — the coordination
  board is always ground truth.
