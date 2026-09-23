# Decision log — super_claude

Newest entry on top. One short ADR-style entry per non-trivial / hard-to-reverse
decision. See `~/.claude/CLAUDE.md` "Decision log" for the format.

### 2026-09-23 - Smart-router skill suggestion deleted; eval logging made opt-in
Decision: Delete the smart router's skill-suggestion branch outright
(`classify_prompt`, `format_suggestion`, all `_rule_*` functions, the
`SMART_ROUTER_SUGGEST_INJECT` switch, the `suggested_skill_or_null` log column and
the two test classes covering them). Keep the model-tier + mode/effort hint exactly
as it is. Flip the eval-log writer from always-on to opt-in
(`SMART_ROUTER_EVAL_LOG=1`, default OFF), keeping the writer and its privacy
contract intact behind the switch. Do not build a learned router (Jev or
Model2Vec) now.
Why: Measured, not assumed. Of the joinable eval rows where the router predicted a
skill, the user invoked the predicted skill 0 times -- it had been predicting in a
label space (/hunt, /think, /rev) disjoint from the one actually in use (qRev,
qPlan, hermes-curate), and its injection had already been off since 2026-08-29, so
the code was dead. For the tier half: only 5 rows out of 6577 have both a router
tier prediction and a real tier choice in the same turn, so the live router is
effectively unmeasurable (n=5, not a 40% accuracy problem). And the prompt text
carries no learnable tier signal -- naive Bayes leave-one-out scored 48.1% against
a 56.8% always-"sonnet" majority baseline (n=81), i.e. WORSE than a constant. The
ceiling is low by construction: 84.6% of turns start no subagent at all, so there
is nothing to route. 3.5 months of logging bought 6577 rows / ~2 MB for 81 usable
labels; the stream is not earning its cost.
Rejected alternatives: (a) Build the learned router on Jev -- rejected: the
bottleneck is absence of volume (~40 decisions/day, 34 of them "do not delegate"),
not classifier quality; a faster/cheaper classifier answers a non-existent
bottleneck. (b) Keep the dead skill branch behind its off switch "in case" --
rejected: it is unreachable code whose predictions are provably worthless, and it
kept a stale import contract that broke the whole hook mid-edit. (c) Delete the
tier hint too -- rejected: it is cheap, rule-based, and harmless; unmeasurable is
not the same as harmful. (d) Delete the 6577 historical rows -- rejected:
`hermes_router_baseline.py` and `scripts/brain_query.py` read them, and the file is
the evidence behind this entry.
Revisit if: a genuinely high-volume classification workload appears (hundreds of
files/emails/tickets per batch), in which case Model2Vec is the right choice over
Jev because it is local with no network round-trip; OR delegation rate rises far
above ~15% of turns so there is actually something to route; OR a labelling need
appears that justifies re-arming `SMART_ROUTER_EVAL_LOG=1`.

### 2026-09-08 - Evaluated four GitHub repos for adoption; adopted none
Decision: After a capability-coverage check, adopt NONE of the four repos raised
(`askjo/camofox-browser`, `cathrynlavery/diagram-design`, `affaan-m/ECC`,
`heygen-com/hyperframes`). Instead install two Python packages that fill a real
gap: PySceneDetect + opencv-python, on the system 3.14 interpreter via
`pip install --user`.
Why: The adoption bar was explicit - only take a repo if our setup cannot already
do it. `affaan-m/ECC` IS the already-installed `ecc` plugin (v2.1.0, marketplace
`affaan-m/everything-claude-code`), so there is nothing to add. `diagram-design`
duplicates an existing layer that already does layout optimisation and a vision
self-check (`drawio-skill` autolayout/validate, `dataviz`, `data-visualization`).
`hyperframes` most likely duplicates Remotion (both render deterministic
frame-exact MP4; they differ in authoring language, HTML/GSAP vs React) - not
verified head-to-head, so it stays open pending that comparison. `camofox-browser`
does NOT exist at the given path (`askjo` is an npm scope; the repo is
`jo-inc/camofox-browser`) and, while it would fill a genuine gap (we have no
fingerprint spoofing, only a webdriver-flag hide), its profile is a ~300 MB
postinstall binary download, telemetry on by default, binding to all interfaces,
and a purpose that is ToS circumvention - a risk decision, not a capability one.
By contrast a grep of the whole setup found no PySceneDetect, no cv2, no
Laplacian/blur scoring and no optical flow anywhere: per-frame sharpness and
motion analysis are genuinely absent.
Rejected alternatives: (a) adopt diagram-design anyway for its 38 editorial
diagram types - rejected: style preference, not capability, and it adds a plugin
maintenance surface. (b) adopt camofox now - rejected: the question is not "can we
already do it" (we cannot) but "do we want that risk", which is a separate,
user-owned decision. (c) install the CV packages into `ai_video/comfyui/.venv` -
rejected: that venv already ships cv2 5.0.0, runs a long-lived server, and the
`hermes-auto-shared-venv-server-install-conflict` skill names opencv-python as the
exact Windows file-lock hazard.
Revisit if: a head-to-head shows hyperframes does something Remotion cannot (Lottie
import, GSAP timelines), OR the stealth-scraping need becomes concrete enough to
justify camofox's risk profile, OR the ECC plugin diverges from the upstream repo.

### 2026-09-08 - K2-Horizon-MoVA-36B-A4B evaluated for speed; not adopted
Decision: Do not adopt IFM's K2-Horizon-MoVA-36B-A4B anywhere in this setup.
Record the evaluation as `okf/ai-radar/models/k2-horizon-mova-36b-a4b.md` with
`adoption: EVALUATED-not-adopted` so it is not re-derived.
Why: The question was specifically whether its SPEED (not its knowledge) is useful
here. It is not. (1) No published throughput/latency measurement exists for this
model; "faster" is inferred from active-parameter count, and even that is
contradictory (card 36B/4B vs vLLM recipe 37.44B/5.95B). (2) It is reachable only
where speed is irrelevant - the qPlan OpenAI-compatible critic slots
(`subq_critic.py`, `glm_critic.py`) take BASE_URL/MODEL/API_KEY overrides today,
but that role wants a strong different-family model. (3) It is unreachable where
speed would matter: the latency-dominated fleets (qRev 15x3, focus-group 215
personas) are Task calls bound to the session provider, with no per-agent endpoint.
(4) Even behind a translating proxy it would be slower - weak multi-turn tool use
(tau3-Banking 26.8/100) trips qRev's own "0-1 tool uses = failed dispatch,
re-dispatch" tripwire. (5) And costlier: the fleet is subscription-covered;
swapping a flat rate for a metered API to buy wall-clock is a net loss.
Rejected alternatives: (a) wire it into the qPlan critic panel - rejected: that is
a diversity slot, not a speed slot, and answers a different question. (b) run it
locally - rejected: BF16 only, 74.9 GB, no official quantization, 2x H200
recommended. (c) build an OpenAI->Anthropic proxy to reach the fleets - rejected
per (4) and (5).
Revisit if: measured throughput is published, OR official quantization ships, OR
Claude Code gains per-subagent endpoint selection. Filter for any future test:
establish whether observed speed is the model or the host (Cerebras) - if the host,
the whole MoVA/A4B argument is irrelevant.

### 2026-07-10 - Adopt Crush as a secondary multi-model/LSP tool; Claude Code stays primary
Decision: Install Crush (charmbracelet/crush, via `npm i -g @charmland/crush`) as a
SECONDARY coding tool wired to the local llama.cpp ("Ornith") server by default,
with GLM/Anthropic-API providers dormant. Claude Code remains primary. Also prepped
Claude Code for free-tier Base44 code handoff (base44 CLI + official base44 skills +
documented docs-MCP/login steps).
Why: Crush's real value is multi-model + LSP-as-agent-tools + native Windows, useful
for running tasks on a free local model or GLM. But the pasted "Crush beats Claude"
comparison was mostly fabricated, Crush removed Anthropic OAuth (cannot use the
Claude subscription), and none of the super_claude harness (hooks/coord/q*/statusline)
carries over - so it supplements Claude Code, it cannot replace it.
Rejected alternatives: (a) migrate to Crush as primary - rejected: abandons the whole
hook/skill/coord ecosystem and forces per-token API or local-only. (b) analysis-only,
no install - rejected: user chose a full hands-on trial. (c) paid Base44 Builder
workflow - rejected: user chose the free path.
Revisit if: Crush restores Anthropic subscription auth, OR a GLM key arrives (then
Crush-on-GLM becomes a first-class cheap tier), OR Base44 free-tier limits block the
intended app work (then reconsider Builder).

### 2026-06-17 - Retire /qPlan auto; split brain (qPlan) from hands (qGoal)
Decision: Remove the `/qPlan auto` execution mode and move ALL execution +
optimization into a new standalone `/qGoal` skill. qPlan becomes strictly
plan-only again (the "brain", incl. the OpenAI cross-model panel); qGoal is the
only q-command that touches code (the "hands"). qGoal: plans via qPlan, runs a
single path OR multiple variants as the task warrants (qPlan decides the variant
count at planning time — optimization/competing-approach -> multi; deterministic
build like a webpage -> single), consults qPlan at every decision point (with the
OpenAI lens while `OPENAI_API_KEY` budget lasts, degrading to qPlan-without-OpenAI
otherwise, never aborting), then runs `/qRev` and fixes per its P0/P1 findings
before closeout. The Arbor fusion layer `qPlan/references/auto-mode.md` was deleted
and its content relocated/adapted to `qGoal/references/engine.md`.
Why: A planner executing code was a logical wart — qPlan's own MUST NOT-execute
rule contradicted its `auto` mode. Separating concerns (plan vs do) makes both
cleaner, lets qGoal reuse qPlan's judgment (and OpenAI) at forks, and removes the
"needs a metric" limitation: qGoal also handles metric-less tasks with a runnable
check or a qualitative qPlan/OpenAI verdict.
Rejected alternatives: (a) add a metric-less mode to `/qPlan auto` and keep
execution in qPlan — rejected: keeps the planner-executes wart. (b) make qGoal a
`/qPlan do` sub-mode — rejected: "qPlan" names planning; overloading it further
muddies it. (c) keep `/qPlan auto` alongside qGoal — rejected: two execution
entrypoints, redundant; user chose full removal with a redirect.
Revisit if: a third autonomous mode appears (then factor the shared house rules
out of `qGoal/references/engine.md` into a common reference); OR the qGoal->qPlan
decision-call cost proves too high in practice (then narrow what counts as a
"decision point" / reduce the panel weight for in-loop calls).
Supersedes the "Adopt Arbor as the engine behind /qPlan auto" entry below (the
engine stays; only its entrypoint moved from /qPlan auto to /qGoal).

### 2026-06-17 - skillspector pre-download gate + ponytail/improve/drawio skills
Decision: Install NVIDIA skillspector as an always-on pre-download security gate
(scan any GitHub repo/skill before cloning/installing; block on high risk) via a
`skillspector-gate` skill + a global CLAUDE.md rule. Install three reviewed skills
despite CRITICAL scores: ponytail (minimal-code lens) into qMin/qRev/qPlan,
shadcn/improve (audit -> plan-for-cheaper-model) into qRev/qPlan, Agents365-ai
drawio-skill into qUpd (every project keeps exclude/SYSTEM_STRATEGIES/
SYSTEM_STATUS.md + system_map.drawio, kept in sync).
Why: The gate is cheap insurance (research cited: 26% of skills have vulns, 5%
malicious). skillspector flagged all four candidates (incl. already-installed
Arbor) DO_NOT_INSTALL, but line-by-line review showed the scores are inflated by
auxiliary code, inherent agent behavior, and literal false positives (XML
comments, an anti-injection rule, the phrase "flood context"); no real malice in
any runtime path. ponytail/improve directly reinforce existing principles
(minimal scope, tiered execution).
Rejected alternatives: (a) trust scores blindly and skip all four — rejected:
they are false-positive-heavy and the skills are genuinely useful. (b) a hook
instead of a skill for the gate — rejected: a hook can't cleanly intercept "about
to git clone"; a CLAUDE.md rule + skill is the right altitude. (c) vendor whole
repos — rejected: only skill dirs vendored (benchmarks/tests/src excluded), which
also removes most of the scanner noise.
Revisit if: skillspector ships an allowlist/baseline so agent-skill false
positives drop; OR any of these skills later shows real malice on a deeper LLM
scan; OR the override pattern is abused (treat CRITICAL as auto-ignore).
Override-logged in ~/.claude/.skillspector_log.jsonl.

### 2026-06-17 - Adopt Arbor as the engine behind /qPlan auto
Decision: Vendor the full RUC-NLPIR/Arbor skill suite (11 `arbor-*` skills,
Apache-2.0) verbatim as the autonomous-optimization engine, and reach it through
a new `/qPlan auto` mode whose fusion layer (`qPlan/references/auto-mode.md`)
applies our conventions: model tiering + GLM caveat, `.worktrees/` convention,
B_dev/B_test held-out discipline, decision-log on merges/prunes, qPlan-style
progress-based termination, context-budget/resume handling, no-decorative-unicode,
and safety gates.
Why: Arbor's measured wins are mostly the iterative loop (Idea Tree, held-out
split, worktree-isolated experiments), not the base model — and that loop is
genuinely useful for metric-driven optimization we can't get from interactive
qPlan. Keeping the engine unmodified makes it updatable from upstream; putting
our knowledge in a separate fusion layer makes the combination smarter without
forking their content.
Rejected alternatives: (a) penso/arbor desktop app — rejected: it runs its own
agent loop instead of the Claude Code CLI, so our hooks/skills/statusline/curator
would not apply (replaces, not complements). (b) Cherry-pick 1-2 arbor skills —
rejected: the suite is a coupled pipeline (entrypoint -> orchestrator -> phases),
not standalone utilities. (c) Re-implement the loop ourselves inside qPlan —
rejected: more work, loses upstream updates.
Revisit if: Arbor's self-reported benchmark (arxiv 2606.11926) turns out to use
an unfair iteration/compute budget vs the Claude Code baseline; OR the 11 extra
skills cause real index/routing clutter; OR penso/arbor gains a "Claude Code CLI
as backend" mode (then reconsider it as the front-end).
