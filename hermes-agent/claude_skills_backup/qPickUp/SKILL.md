---
name: qPickUp
description: "Resume another Claude Code or Codex window's work after it froze/crashed on this repo, or sync task division with a still-live sibling window -- with NO required explanatory prose. Invoke as /qPickUp [<window-count>] [<pasted fragment>] -- both arguments are optional and their SHAPE decides the mode: pasted text (code, chat, error, TODO snippet -- any shape) means PICKUP (reconstruct where the frozen window left off from disk forensics -- the coord.py board, session transcripts, git state -- then resume it); a bare number with no pasted text means SYNC (find the other live window(s), read TODO.md/roadmap, and negotiate who does what so work doesn't collide); no arguments at all means infer from conversation context. Never requires the user to narrate 'a window froze, here is where it stopped, continue from here' -- the skill does that reconstruction itself. Invoked via /qPickUp (canonical) OR any case variant -- /qpickup, /Qpickup, /QPickUp, /QPICKUP, /qpu all map to this same skill."
---

# qPickUp — resume a frozen window, or sync with a live one

`/qClose` is the GRACEFUL handoff: a window that's about to close writes its
own resume file. `/qPickUp` is the DISASTER-RECOVERY counterpart: a window
that never got to run `/qClose` — it froze, crashed, or got closed by
accident — and all the user has is whatever they managed to copy out of it,
or sometimes not even that, just a headcount. `/qPickUp` reconstructs the
rest from disk: the cross-window coordination board, the frozen window's own
session transcript (still on disk even though the window is gone), git state,
and the project's TODO/roadmap.

**The point of this skill is that the user never has to write the
explanation.** "There was a Claude/Codex window, it froze, here's where it
stopped, continue from there" — that whole sentence is what THIS skill
supplies automatically. The user just runs `/qPickUp` with whatever fragment
they happened to copy (or nothing at all), and the skill does the detective
work.

## Mode is decided by argument SHAPE, not by a flag

Parse `$ARGUMENTS` (everything typed after `/qPickUp`) like this, in order:

1. Trim whitespace. If a leading token is a bare integer followed by
   whitespace or end-of-string, peel it off as `window_count_hint` (the
   user's claim of how many windows are running on this repo right now — a
   cross-check, never authoritative; ground truth always comes from
   `coord.py context` in step 1 of whichever mode runs).
2. What's left after peeling the optional number decides the mode:
   - **Non-empty remainder** (anything — a code block, a pasted chat
     fragment, an error message, a TODO line, a single sentence) -> **Mode
     A (PICKUP)**.
   - **Nothing left** (the whole input was just the number, or there was no
     input at all) -> **Mode B (SYNC)**.
3. If `$ARGUMENTS` was completely empty (bare `/qPickUp`, no number
   either): before defaulting to Mode B, check the last few messages in the
   CURRENT conversation for something that already reads like a
   frozen-window fragment the user pasted just before or after invoking the
   command (this happens often — the user pastes first, then remembers to
   type the command, or types prose like "itt fagyott le az ablak: ..."
   instead of formally routing it through `/qPickUp`). If found, treat that
   as the Mode A input. Only fall through to Mode B with an empty hint if
   truly nothing resembling a fragment exists anywhere nearby.

Examples the grammar must handle correctly:
- `/qPickUp 3 <pasted code>` -> Mode A, count hint 3.
- `/qPickUp <pasted code>` -> Mode A, no count hint.
- `/qPickUp 3` (just the digit, nothing else) -> Mode B, count hint 3.
- `/qPickUp` (nothing at all) -> infer per step 3 above.

Never ask the user "which mode do you want?" — the shape already answers it.

---

## Mode A — PICKUP (reconstruct and resume a frozen window)

### Step 1 — orientation

Run the equivalent of `/qRem` first (invoke the `qRem` skill via the Skill
tool if available; otherwise do it inline: read `exclude/SYSTEM_STRATEGIES/TODO.md`
or `TODO.md`, `INDEX.md`, and `git log -5 --oneline`). This is baseline
context, not the task — the frozen window's own state (steps 2-3 below) is
the source of truth for what to actually resume.

### Step 2 — read the coordination board (ground truth on who's alive)

```
python ~/.claude/scripts/coord.py context
python ~/.claude/scripts/coord.py status
```

`context` gives compact JSON: `others[]` (session, branch, note, claims —
only genuinely LIVE windows appear here, staleness-filtered already),
`blocked_paths`, `requests_for_me`, `answers_for_me`. `status` gives the
human-readable `work.md`, including a **"Recent activity" log** — this is
the key forensic artifact: a frozen window's last acts are still recorded
there (`[<short-id>] claimed <paths>`, `[<short-id>] beat: <note>`) even
though it no longer appears in the live-windows list. A `claimed` entry with
no matching `released`/`done` from the same short-id is exactly what a
window mid-edit-when-it-died looks like.

If `window_count_hint` was given and doesn't match the number of live
windows `context` reports, note the mismatch in one line later — never block
on it; the board is ground truth, the hint is just a cross-check.

### Step 3 — reconstruct what the frozen window was doing

Combine whatever signals are available — don't require all of them:

**a) The pasted fragment itself.** Read it for file paths, function/skill
names, error text, a task description, anything identifying. This is
usually enough to know the SUBJECT even before finding the transcript.

**b) Coord board correlation (strongest signal, if coord was in use).** From
Step 2's "Recent activity" log, find the most recent `claimed`/`beat` entry
whose short-id (6 hex chars, e.g. `[086331]`) is NOT in the current
`context` output's `others[]` — that's a candidate dead window. Its claimed
paths are exactly the files it was mid-edit on.

**c) Session-transcript correlation (richest signal — full context, not just
the fragment).** Claude Code session transcripts live at
`~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`. Compute
`<encoded-cwd>` from the repo's absolute path (from
`git rev-parse --show-toplevel`): replace the first `:\` with `--`, then
every remaining `\` or `/` with `-` (e.g. `D:\Projects\super_code` ->
`D--Projects-super-code` — verified against this machine's actual
directory names, not assumed). If that exact directory doesn't exist, list
`~/.claude/projects/` and pick the entry whose name ends in the repo's own
folder name.
  - If Step 3b found a short-id: glob `<that-dir>/<short-id>*.jsonl` — the
    short id is literally `session_id[:6]`, so this resolves to the exact
    transcript directly.
  - Otherwise, list `*.jsonl` in that directory sorted by mtime (newest
    first) and grep each for a distinctive substring from the pasted
    fragment (8+ contiguous characters, avoid generic words) until one
    matches. Read that transcript's tail (last ~150-300 lines is usually
    enough) — the last assistant message, the last few tool calls/results,
    and any TODO/plan state — to reconstruct the FULL context, not just what
    the user happened to copy.
  - If running under Codex instead: the equivalent lives at
    `~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-<timestamp>-<uuid>.jsonl`
    (verified format). Each file's first line (`type: "session_meta"`) has a
    `payload.cwd` field — filter to files whose `cwd` matches this repo, then
    apply the same mtime/grep matching as above.
  - If neither the exact directory nor a matching transcript is found: say
    so in one line and continue with (a) + (d) alone. This is a genuine,
    expected degradation, not a failure to fix.

**d) Git state.** `git status --porcelain`, `git diff --stat`, and
`git log -5 --oneline` — uncommitted changes matching files/topics from (a)
or (c) confirm exactly how far the frozen window got. If it committed before
dying, the commit message + diff may be enough on their own.

**e) Ambiguity.** If more than one plausible frozen session/target exists and
the signals disagree, pick the best match by recency + distinctiveness of
the match, state which one was picked and why in one line, and proceed —
don't stall on it. The user can correct you if it's wrong; that costs one
turn, not a blocked one.

### Step 4 — liveness check before touching anything (no silent takeover)

For every file/path identified in Step 3, check whether it's in the CURRENT
`context` output's `others[].claims` (i.e., some window that's still alive
right now, not just previously, holds it):

- **Not claimed by any live window** -> safe. Claim it:
  `python ~/.claude/scripts/coord.py claim <path> [<path> ...]`
- **Claimed by a live window** -> this is NOT actually a frozen-window
  situation for that file — someone is still working it. Do not take it
  over. Post instead:
  `python ~/.claude/scripts/coord.py request --to <short-id> --note "..."`
  explaining what you found and asking whether it's still in progress, and
  surface this to the user in one line rather than silently proceeding on
  that file. Continue picking up whatever OTHER identified files are free.

### Step 5 — post a status note, then resume immediately

```
python ~/.claude/scripts/coord.py beat --note "picking up <short-id or 'frozen window'>'s work: <one-line what>"
```

Then **just continue the work** — same discipline as `/qClose`'s resume
contract: no "should I continue?" question, no confirmation banner just to
ask permission to resume. State in one short line what's being picked up and
why (which session/claim/diff it was reconstructed from), then act. The only
allowed stops are the global decision-gate (push/merge/rebase onto shared
branches/delete — ask first) and a genuine blocker where the reconstructed
signals actively conflict (e.g. the pasted fragment and the git diff
describe two different tasks) — in that narrow case, ask ONE targeted
question naming the conflict, not a generic "what should I do?".

### Step 6 — when the picked-up work concludes

Release what you claimed (`coord.py release` for the specific paths, or bare
`coord.py release` to drop everything you hold), and post a final `beat`
note summarizing the outcome so the board reflects reality for the next
window that looks.

---

## Mode B — SYNC (no fragment, just a headcount — divide open work)

This is what runs for `/qPickUp 3` (just the digit) or a truly empty
`/qPickUp` with nothing to infer from Mode A step 3. There is nothing to
"resume" here — the point is to get this window productively aligned with
its sibling(s) instead of guessing or duplicating work.

### Step 1 — find the other live window(s)

```
python ~/.claude/scripts/coord.py context
```

Read `others[]`: each entry's `session` (short id), `branch`, `note` (what
it says it's doing), and `claims` (files it currently holds). If
`window_count_hint` was given and doesn't match `len(others) + 1`, note the
mismatch once and proceed on the board's actual count — it's ground truth.

If `others` is empty: there is no live sibling to sync with right now
(the user's premise that "there's another window" doesn't hold at this
moment — it may have closed, or gone stale). Say so in one line, and fall
back to ordinary orientation (`/qRem`) instead of stalling.

### Step 2 — read the open-task source

Look for, in this order, the first that exists: `exclude/SYSTEM_STRATEGIES/TODO.md`
(canonical), `exclude/TODO.md`, `TODO.md`, `ROADMAP.md` / `roadmap.md`. Parse
out the open/pending items (per the project's per-window TODO protocol, each
line may already carry a `[w-<code>]` owner tag — items tagged for a LIVE
window's code are already spoken for; untagged items or items tagged for a
window that's no longer live are up for grabs).

If none of these files exist: say so in one line, then ask the sibling
directly instead of guessing — post a `coord.py request` (Step 3) asking
what it's working on and what's left, rather than inventing a task list.

### Step 3 — propose a split, don't just wait for a reply

Cross-reference the open items against each live sibling's current `note` +
`claims` from Step 1 — anything that overlaps with what a sibling already
reports doing is theirs; the rest is unclaimed. Pick the largest coherent
unclaimed piece for THIS window, and post the proposal so the sibling sees
it on its next turn:

```
python ~/.claude/scripts/coord.py request --to <short-id-or-*> --note "javaslat: te folytasd <X>-et (már azon vagy), én <Y>-t kezdem — szólj ha ütközik"
```

Coordination here is PULL-based — the sibling only sees this on ITS next
turn, not instantly. **Do not sit idle waiting for a reply.** Immediately
claim the piece you proposed for yourself and start on it:

```
python ~/.claude/scripts/coord.py claim <path> [<path> ...]
python ~/.claude/scripts/coord.py beat --note "syncing with <short-id>: working <Y> per open TODO/roadmap items"
```

State in one line what was proposed, to whom, and what you're starting on
regardless of reply — then begin the work. If a reply arrives later that
conflicts (the sibling was already on the same item despite what its `note`
said), stop that specific item, `coord.py release` it, and re-pick from the
remaining unclaimed list.

### Step 4 — no open items left unclaimed

If everything in the TODO/roadmap is already covered by live siblings'
claims/notes, say so plainly and ask the user for direction (this is a
genuine fork only they can resolve — there's no more free work to grab
without either duplicating a sibling or inventing a task that isn't
written down anywhere).

---

## Edge-case matrix

| Situation | Behaviour |
|---|---|
| Not a git repo | Mode A/B both degrade: skip git-state signals, still attempt coord board + transcript correlation |
| `coord.py` unavailable / `COORD_DISABLE=1` | Say so once; Mode A falls back to fragment + git state + transcript search alone; Mode B cannot run (no board to sync against) — say so and stop there, don't fabricate a sibling |
| No session-transcript match found (Mode A) | Proceed on the pasted fragment + git state alone; note the gap once, don't block |
| `window_count_hint` mismatches the board's actual live count | Note once, trust the board, keep going |
| Multiple plausible frozen sessions (Mode A) | Pick best match by recency + match distinctiveness, state the pick and why, proceed |
| A file Mode A wants is claimed by a LIVE (not stale) window | Do not take it; `coord.py request` to that window, tell the user, keep picking up the rest |
| No TODO/roadmap file exists (Mode B) | Ask the sibling directly what it's doing instead of guessing a task list |
| `others[]` empty (Mode B) | No sibling to sync with right now; fall back to `/qRem`-style orientation |
| Reconstructed signals actively disagree (Mode A) | The one allowed non-gate stop: ask ONE question naming the specific conflict |
| Next step is push / merge / rebase onto a shared branch / delete | Global decision-gate applies — stop, propose the exact command, wait for the user |

## What `/qPickUp` deliberately does NOT do

- Does NOT require the user to explain that a window froze, where it
  stopped, or to say "continue from here" — that reconstruction is the
  whole point of this skill.
- Does NOT silently take over a file another LIVE window currently holds.
- Does NOT invent a task list when no TODO/roadmap file exists (Mode B) —
  it asks the sibling instead.
- Does NOT wait idle for a sync proposal's reply before starting work —
  it claims the unclaimed piece and begins immediately (PULL-based
  coordination means waiting idle wastes the turn).
- Does NOT skip the global decision-gate — push/merge/rebase/delete still
  require explicit user approval regardless of how the resumed work reads.
- Does NOT treat the `window_count_hint` number as authoritative — the
  coordination board is always ground truth; the number is a cross-check.
