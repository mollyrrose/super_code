"""Smart-router rules: recommend a subagent model tier for a user prompt.

Pure-Python, stdlib only. No LLM call — the router has to be cheap because
it runs in a UserPromptSubmit hook on every prompt.

The router is intentionally conservative:
  - returns None for short prompts (< 4 words)
  - returns None when the user has already invoked an explicit slash
    command (their choice stands)
  - returns None for anything that doesn't unambiguously match one phase

False positives waste context budget and erode trust in the hint, so the
bar is high. Zero hints for a session is an acceptable outcome.

SCOPE NOTE (2026-09-23) — the skill-suggestion branch was REMOVED.
This module used to also classify prompts into a skill suggestion
(`classify_prompt`, `format_suggestion`, the `_rule_*` functions). It was
deleted after measuring it against the eval log: of the joinable rows where
the router predicted a skill, the user invoked the predicted skill 0 times.
It had been predicting in a label space (/hunt, /think, /rev) disjoint from
the one actually used (qRev, qPlan, hermes-curate). Its injection had
already been off since 2026-08-29; this removed the dead code behind it.
Full evidence + rationale: docs/decisions/log.md.

What remains is the model-tier router below, which is cheap and harmless.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


def _has_slash_command(text: str) -> bool:
    return bool(re.match(r"^\s*/[\w:-]+", text))


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _matches_any(text_lc: str, patterns: list[str]) -> bool:
    return any(re.search(p, text_lc) for p in patterns)


# ── Model-tier routing ─────────────────────────────────────────────────────
#
# Claude Code cannot switch the MAIN session's model from a hook (hard
# architectural limit), and a /model switch is manual. The conversation
# transcript is model-agnostic, so the supported way to run a given phase on a
# different-strength model is to DELEGATE it to a subagent that carries its own
# `model` (Agent/Task `model: fable|opus|sonnet|haiku`). This router classifies
# the prompt's phase and recommends the subagent model to use when delegating;
# the main session keeps the full context regardless of what the subagent runs.
#
# Capability ladder (ascending): haiku < sonnet < opus < fable.
#   haiku  (claude-haiku-4-5)   -- mechanical / near-deterministic.
#   sonnet (claude-sonnet-4-6)  -- standard coding: implementation, refactor,
#                                  tests, bug fixes. Strong + cost-efficient at
#                                  code benchmarks (SWE-bench-class), so it is
#                                  the DEFAULT for build/fix work.
#   opus   (claude-opus-4-8)    -- high-tier judgment: architecture, design,
#                                  audit, deep root-cause, security review,
#                                  research. The workhorse high tier.
#   fable  (claude-fable-5)     -- Mythos-class, ABOVE opus; the most capable
#                                  generally-available model. RESERVED for the
#                                  hardest reasoning where opus is not enough:
#                                  novel/optimal algorithm design, formal
#                                  proofs/derivations, deep multi-constraint
#                                  architecture, adversarial security analysis,
#                                  frontier research synthesis.
#
# Policy is "the ideal model that is still SUFFICIENT for the task, not the
# biggest" (feedback 2026-07-02): pick the LOWEST tier that clears the task and
# break ties UPWARD by one step ("one version higher than needed"). The ceiling
# is now `fable`, but escalation to it requires an explicit hardness signal --
# ordinary design/audit work stays on opus so the top tier is spent only where
# it changes the answer. Fable is NO LONGER an off-ladder "fast line"; it is the
# top of the ladder.
#
# On GLM (z.ai) the aliases resolve to GLM models via the launcher env mapping;
# `fable` maps to the GLM flagship alongside `opus` when no distinct top GLM
# model exists, so the same routing decisions hold unchanged.


@dataclass(frozen=True)
class ModelTier:
    model: str   # subagent model alias: "fable" | "opus" | "sonnet" | "haiku"
    phase: str   # human-readable phase label
    why: str     # one-line rationale surfaced to the model


# Top tier (fable): the hardest reasoning where opus is not sufficient. Gated on
# EXPLICIT hardness signals so the ceiling is spent only where it changes the
# answer -- "ideal yet sufficient" means ordinary design/audit stays on opus.
_TIER_TOP_PATTERNS = [
    r"\b(prove|proof|derive|derivation|formal(?:ly|ise|ize)?)\b",
    r"\b(novel|optimal|hardest|from first principles)\b.{0,30}\b(algorithm|approach|design|proof|solution)\b",
    r"\b(algorithm|complexity)\b.{0,30}\b(design|analysis|optimal|prove|derive)\b",
    r"\b(adversarial|threat[-\s]?model)\b.{0,30}\b(analysis|proof|design)\b",
    r"\bdeep(?:est)? (?:research|synthesis)\b",
    r"\bmost (?:capable|powerful|intelligent)\b",
    r"\b(use|run) (?:the )?(?:strongest|best|top|smartest) model\b",
    r"\bfable\b",
    # Hungarian
    r"\b(bizonyítsd|bizonyítás|vezesd le|levezetés|formális)\b",
    r"\b(legnehezebb|legjobb algoritmus|optimális algoritmus|első elvekből)\b",
    r"\b(legerősebb|legokosabb|legjobb) modell\b",
]

# High tier (opus): planning, design, architecture, deep reasoning, audit,
# research, hard root-cause debugging, security review.
_TIER_HIGH_PATTERNS = [
    r"\b(architect|architecture|system design|design the)\b",
    r"\bplan (?:this|out|the|a)\b",
    r"\bhow should (?:i|we)\b",
    r"\bbest (?:approach|design|architecture|way)\b",
    r"\b(trade[-\s]?offs?|alternatives?)\b",
    r"\broot[-\s]?cause\b",
    r"\b(regression|regressed)\b",
    r"\baudit\b",
    r"\b(security|threat)[-\s]?(?:review|model|audit|analysis)\b",
    r"\b(research|deep[-\s]?dive)\b",
    r"\bhelp me understand\b",
    # Hungarian
    r"\b(tervezd|tervezz|hogyan érdemes|mi a legjobb|megéri)\b",
    r"\bgyökér ?ok\b",
    r"\bbiztonsági (?:átvizsgálás|audit|elemzés)\b",
    r"\b(kutass|mélyebben|értsd meg|tervezés)\b",
]

# Mechanical tier (haiku): low-effort, near-deterministic edits and lookups.
_TIER_MECH_PATTERNS = [
    r"\b(rename|reformat|re[-\s]?indent)\b",
    r"\bformat the\b",
    r"\bfix the (?:indentation|formatting|whitespace|spelling)\b",
    r"\b(typo|misspelling)\b",
    r"\b(list|show me)\b.{0,15}\b(files|functions|imports|occurrences|todos|directories|folders)\b",
    r"\b(grep|search for|find (?:all )?occurrences)\b",
    r"\bbump (?:the )?version\b",
    r"\bwhat files?\b",
    # Hungarian
    r"\b(nevezd át|formázd|elgépel|listázd|keresd meg|melyik fájl)\b",
]

# Implementation tier (sonnet): standard coding, refactors, tests, bug fixes.
_TIER_IMPL_PATTERNS = [
    r"\b(implement|build|add|wire|integrate|write|create)\b.{0,60}\b(feature|component|module|endpoint|function|method|handler|test|tests|class|migration|script|integration|service|pipeline|hook|route|model)\b",
    r"\brefactor (?:the|this|that|it)\b",
    r"\b(fix|patch) (?:the |this )?(?:bug|issue|function|method|test)\b",
    r"\bwrite (?:the )?(?:unit |integration )?tests?\b",
    # Hungarian
    r"\b(implementáld|csináld meg|írd meg|refaktoráld|kösd be|javítsd)\b",
]


def recommend_model_tier(text: str) -> ModelTier | None:
    """Recommend a subagent model for the prompt's phase, or None when unsure.

    Same conservative bar as classify_prompt: no hint for slash commands, very
    short prompts, or anything that doesn't clearly match a phase. Tiers are
    checked TOP-DOWN (fable -> opus -> haiku -> sonnet) so the strongest explicit
    signal wins: "prove the optimal algorithm" routes to fable, a plain "security
    audit of the new module" routes to opus, and standard "implement X" to sonnet.
    """
    if not text or not text.strip():
        return None
    raw = text.strip()
    if _has_slash_command(raw):
        return None
    if _word_count(raw) < 4:
        return None
    lc = raw.lower()
    if _matches_any(lc, _TIER_TOP_PATTERNS):
        return ModelTier(
            "fable",
            "hardest reasoning (proof / novel-or-optimal algorithm / adversarial / frontier)",
            "opus is not enough here -> top of the ladder (fable); spent only on an explicit hardness signal",
        )
    if _matches_any(lc, _TIER_HIGH_PATTERNS):
        return ModelTier(
            "opus",
            "planning / design / deep-reasoning",
            "hard reasoning -> high tier (one step above the bare minimum); escalate to fable only on an explicit hardness signal",
        )
    if _matches_any(lc, _TIER_MECH_PATTERNS):
        return ModelTier(
            "haiku",
            "mechanical / trivial",
            "near-deterministic low-effort work -> the cheapest tier is enough",
        )
    if _matches_any(lc, _TIER_IMPL_PATTERNS):
        return ModelTier(
            "sonnet",
            "implementation / refactor",
            "standard coding -> mid tier (one step above the bare minimum)",
        )
    return None


def format_model_tier(tier: ModelTier) -> str:
    """Format a ModelTier for injection as UserPromptSubmit additionalContext."""
    return (
        f"[model-router hint] This looks like {tier.phase} work. "
        f"If you delegate it, prefer a `{tier.model}` subagent (Agent/Task model: {tier.model}); "
        f"{tier.why}. The main session keeps full context regardless of the subagent's model. "
        f"Suggestion only -- skip it for quick conversational turns or if the user chose otherwise."
    )


# ── Mode/effort routing (additive; pure function of the model tier) ────────
#
# Derives a coarse MODE (MINIMAL / NATIVE / ALGORITHM) and a fine EFFORT band
# (E1..E5) purely from the tier that recommend_model_tier() already computed.
# This keeps {mode, effort, tier} consistent with recommend_model_tier by
# construction -- recommend_model_tier() and classify_prompt() are NEVER
# modified by this addition.


@dataclass(frozen=True)
class ModeEffort:
    mode: str    # "MINIMAL" | "NATIVE" | "ALGORITHM"
    effort: str  # "E1".."E5"
    tier: str    # the model tier this was derived from


# Pure derivation from the model tier -- keeps {mode,effort,tier} consistent
# with recommend_model_tier by construction.
_TIER_MODE_EFFORT: dict[str, tuple[str, str]] = {
    "fable":  ("ALGORITHM", "E5"),
    "opus":   ("NATIVE",    "E4"),
    "sonnet": ("NATIVE",    "E3"),
    "haiku":  ("MINIMAL",   "E1"),
}


def recommend_mode_effort(text: str) -> ModeEffort | None:
    """Derive a (mode, effort) hint from the prompt's model tier.
    Returns None whenever recommend_model_tier returns None (same conservative
    bar: slash command, <4 words, or no clear phase match)."""
    tier = recommend_model_tier(text)
    if tier is None:
        return None
    mode, effort = _TIER_MODE_EFFORT[tier.model]
    return ModeEffort(mode, effort, tier.model)


def format_mode_effort(me: ModeEffort) -> str:
    """Compact suffix appended to the existing model-tier hint line (token-floor
    friendly: no new line, 28-31 chars depending on the mode label). ASCII only."""
    return f" [mode: {me.mode} | effort: {me.effort}]"
