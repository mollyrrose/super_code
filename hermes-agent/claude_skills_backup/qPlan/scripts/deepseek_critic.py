#!/usr/bin/env python3
"""
qPlan cross-model critic — DeepSeek provider.

Mirror of openai_critic.py for DeepSeek's chat-completions endpoint.

Reads JSON from stdin:
  { "task": "<original task>",
    "plan": "<current plan.md content>",
    "ledger": [ { "text": "...", "status": "...", "tier": "..." }, ... ],
    "model": "<optional model override>" }

Writes JSON to stdout:
  { "verdict": "major issue|minor issue|no material issue",
    "suggestions": [ { "text": "...", "tier_hint": "..." } ],
    "provider": "deepseek",
    "model": "<model used>",
    "chunks_submitted": <int> }

If the caller does NOT pass a `model` key, the script auto-discovers the
best chat model the DEEPSEEK_API_KEY can reach by listing /v1/models and
matching against MODEL_PRIORITY (best-first). The pick is cached in
~/.claude/.qplan_deepseek_model_cache.json for CACHE_TTL_HOURS to avoid
hitting /v1/models every critic round. Force a refresh with the env var
QPLAN_DEEPSEEK_MODEL_REFRESH=1 or by deleting the cache file.

DeepSeek API notes (verified 2026-06-12):
- Endpoint: https://api.deepseek.com/v1/chat/completions (OpenAI-compatible).
- Unlike OpenAI, DeepSeek exposes CONCURRENCY caps rather than strict
  TPM/RPM. As of 2026-06: deepseek-v4-pro 500 concurrent, deepseek-v4-flash
  2500 concurrent. Single-call critic usage rarely hits this — but if a
  call returns HTTP 429 (overload, concurrency excess, or future per-tier
  TPM enforcement), we still chunk the plan defensively. Same pattern as
  the OpenAI critic; see feedback_model_selection_highest.md.
- DeepSeek accepts standard `temperature` on all current models — no
  GPT-5-style 400 trap.

Fails loud (non-zero exit + stderr) on missing DEEPSEEK_API_KEY or chat
errors. Does NOT silently fall back to Claude — provider distinguishability
is the whole point.

Stdlib only.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Shared chunking helpers (see plan_chunker.py — same module imported by
# openai_critic.py so a fix to splitting/merging logic applies to both).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from plan_chunker import (  # noqa: E402
    MAX_CHUNK_DEPTH,
    merge_verdicts,
    split_plan,
)

CRITIC_PROMPT = """You are the DeepSeek critic in a qPlan author<->critic loop.

Read the plan and the ledger of prior suggestions. Produce a JSON verdict
EXACTLY in this shape:

{
  "verdict": "major issue" | "minor issue" | "no material issue",
  "suggestions": [
    { "text": "<one concrete actionable point>",
      "tier_hint": "structural" | "behavioral" | "editorial" }
  ]
}

CRITICAL: `no material issue` with an empty suggestions list is a VALID and
correct outcome. Do not invent a critique if the plan is sound. Convergence
is the point.

Do not repeat points already in the ledger — they will be detected as
semantic duplicates and the round will be wasted. If you find yourself
rephrasing a prior point, omit it.

Output ONLY the JSON. No prose before or after."""


# --- Model auto-discovery -------------------------------------------------

CACHE_PATH = Path.home() / ".claude" / ".qplan_deepseek_model_cache.json"
CACHE_TTL_HOURS = 24.0

# Best-first priority. Order reflects reasoning quality vs cost: pro
# reasoning first, then flash, then earlier families as graceful
# degradation. Update this list when DeepSeek releases new model families
# — that's the only thing that needs editing.
MODEL_PRIORITY = [
    re.compile(r"^deepseek-v4-pro$"),
    re.compile(r"^deepseek-v4-flash$"),
    re.compile(r"^deepseek-v3-pro$"),
    re.compile(r"^deepseek-v3-flash$"),
    re.compile(r"^deepseek-reasoner$"),
    re.compile(r"^deepseek-chat$"),
    re.compile(r"^deepseek-coder$"),
]

# Last-resort if /v1/models is unreachable AND no cache exists.
HARD_FALLBACK_MODEL = "deepseek-chat"


def _list_models(api_key: str) -> list[str]:
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return [m["id"] for m in body.get("data", [])]


def _pick_best(available: list[str]) -> str | None:
    # Same stable-alias preference as openai_critic._pick_best so the two
    # critics stay structurally consistent. DeepSeek's current model names
    # are all undated literals (deepseek-v4-pro, deepseek-v4-flash, etc.),
    # so the dated-snapshot branch is dormant today — but if DeepSeek ever
    # ships a dated variant (deepseek-v4-pro-2026-09-01), this picks the
    # latest one.
    for pattern in MODEL_PRIORITY:
        matches = [m for m in available if pattern.match(m)]
        if not matches:
            continue
        stable = [m for m in matches if not re.search(r"-\d{4}-\d{2}-\d{2}$", m)]
        if stable:
            return stable[0]
        return sorted(matches)[-1]
    return None


def _read_cache(allow_stale: bool = False) -> str | None:
    try:
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    model = cache.get("model")
    fetched_at = cache.get("fetched_at", "")
    if not (model and fetched_at):
        return None
    if allow_stale:
        return model
    try:
        age_h = (
            datetime.now(timezone.utc) - datetime.fromisoformat(fetched_at)
        ).total_seconds() / 3600.0
    except ValueError:
        return None
    return model if age_h < CACHE_TTL_HOURS else None


def _write_cache(model: str, available_count: int) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(
            json.dumps(
                {
                    "model": model,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "available_models_count": available_count,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError as e:
        # Non-fatal but surface on stderr so a full-disk storm leaves a
        # trace. P3 in the qRev pass.
        sys.stderr.write(f"deepseek_critic: cache write failed (non-fatal): {e}\n")


def discover_model(api_key: str) -> str:
    if not os.environ.get("QPLAN_DEEPSEEK_MODEL_REFRESH"):
        fresh = _read_cache(allow_stale=False)
        if fresh:
            return fresh

    try:
        available = _list_models(api_key)
    except urllib.error.HTTPError as e:
        # P2.5: 401/403 = bad key → fail loud. Other HTTPError = transient
        # → accept stale cache.
        if e.code in (401, 403):
            sys.stderr.write(
                f"deepseek_critic: /v1/models returned HTTP {e.code} — bad or "
                f"revoked DEEPSEEK_API_KEY. Fix the key and retry.\n"
            )
            sys.exit(2)
        stale = _read_cache(allow_stale=True)
        return stale or HARD_FALLBACK_MODEL
    except urllib.error.URLError:
        stale = _read_cache(allow_stale=True)
        return stale or HARD_FALLBACK_MODEL

    best = _pick_best(available) or HARD_FALLBACK_MODEL
    _write_cache(best, len(available))
    return best


# --- Chat call ------------------------------------------------------------
#
# Same retry layer as openai_critic.py — see the comment block there.

MAX_TOTAL_CHUNKS = 8
_total_chunks_submitted = 0


def call_deepseek(
    api_key: str,
    model: str,
    task: str,
    plan: str,
    ledger: list,
    depth: int = 0,
    system_prompt: str = CRITIC_PROMPT,
) -> dict:
    global _total_chunks_submitted
    _total_chunks_submitted += 1
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {"task": task, "plan": plan, "ledger": ledger},
                    ensure_ascii=False,
                ),
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", "replace")
        low = body_text.lower()
        # Budget/quota exhaustion. DeepSeek has NO free/keyless tier, so unlike
        # openai (-> browser) and glm (-> free model) there is nothing to fall
        # back to. Per the user's "don't stop the round" policy, the correct
        # behaviour here is to MUTE just this lens (exit 2) — the qPlan round
        # continues with the remaining providers. DeepSeek signals a dead
        # balance with HTTP 402 / "Insufficient Balance".
        if e.code == 402 or "insufficient balance" in low or "insufficient_balance" in low:
            sys.stderr.write(
                "deepseek_critic: balance/quota exhausted. DeepSeek has no free "
                "fallback, so this lens is muted; the qPlan round continues with "
                "the remaining providers.\n"
            )
            sys.exit(2)
        if (
            e.code == 429
            and depth < MAX_CHUNK_DEPTH
            and _total_chunks_submitted < MAX_TOTAL_CHUNKS
        ):
            parts = split_plan(plan)
            if len(parts) < 2:
                sys.stderr.write(
                    f"deepseek_critic: HTTP 429 but plan is atomic at depth "
                    f"{depth} — cannot split further. Response: {body_text}\n"
                )
                sys.exit(2)
            sleep_s = 2 ** depth
            sys.stderr.write(
                f"deepseek_critic: 429 at depth {depth}, splitting plan into "
                f"{len(parts)} parts and retrying after {sleep_s}s.\n"
            )
            time.sleep(sleep_s)
            sub_verdicts = [
                call_deepseek(api_key, model, task, p, ledger, depth + 1, system_prompt)
                for p in parts
            ]
            merged = merge_verdicts(sub_verdicts)
            merged["_chunks_submitted"] = sum(
                v.get("_chunks_submitted", 1) for v in sub_verdicts
            )
            return merged
        if e.code == 429:
            sys.stderr.write(
                f"deepseek_critic: HTTP 429 but chunk budget exhausted "
                f"(depth={depth}, total_chunks={_total_chunks_submitted}, "
                f"cap={MAX_TOTAL_CHUNKS}). Response: {body_text}\n"
            )
            sys.exit(2)
        sys.stderr.write(f"deepseek_critic: HTTP {e.code} — {body_text}\n")
        sys.exit(2)
    except urllib.error.URLError as e:
        sys.stderr.write(f"deepseek_critic: network error — {e}\n")
        sys.exit(2)

    # P1.1: guard response-shape access.
    try:
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError, TypeError) as e:
        sys.stderr.write(
            f"deepseek_critic: unexpected response shape ({type(e).__name__}: "
            f"{e}). Raw body: {json.dumps(body)[:1000]}\n"
        )
        sys.exit(2)
    except json.JSONDecodeError as e:
        sys.stderr.write(
            f"deepseek_critic: response content was not valid JSON: {e}. "
            f"Raw content: {content[:1000] if isinstance(content, str) else content}\n"
        )
        sys.exit(2)


def main() -> None:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        sys.stderr.write(
            "deepseek_critic: DEEPSEEK_API_KEY not set. qPlan does NOT silently "
            "fall back to claude — provider distinguishability is the point. "
            "Set the env var or drop deepseek from the providers list.\n"
        )
        sys.exit(2)

    try:
        req_in = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        sys.stderr.write(f"deepseek_critic: bad JSON on stdin — {e}\n")
        sys.exit(2)

    task = req_in.get("task", "")
    plan = req_in.get("plan", "")
    ledger = req_in.get("ledger", [])
    model = req_in.get("model") or discover_model(api_key)
    # Callers outside qPlan (e.g. family-setting's field-voice lens) pass their
    # own system_prompt to replace the qPlan-specific CRITIC_PROMPT — otherwise
    # their instructions only ride along as inert JSON data in the user turn
    # and the qPlan verdict/suggestions framing silently wins.
    system_prompt = req_in.get("system_prompt") or CRITIC_PROMPT

    verdict = call_deepseek(api_key, model, task, plan, ledger, system_prompt=system_prompt)
    verdict["provider"] = "deepseek"
    verdict["model"] = model
    verdict["chunks_submitted"] = verdict.pop("_chunks_submitted", 1)

    sys.stdout.write(json.dumps(verdict, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
