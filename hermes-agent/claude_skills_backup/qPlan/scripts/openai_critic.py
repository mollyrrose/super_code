#!/usr/bin/env python3
"""
qPlan cross-model critic — OpenAI provider.

Reads JSON from stdin:
  { "task": "<original task>",
    "plan": "<current plan.md content>",
    "ledger": [ { "text": "...", "status": "...", "tier": "..." }, ... ],
    "model": "<optional model override>" }

Writes JSON to stdout:
  { "verdict": "major issue|minor issue|no material issue",
    "suggestions": [ { "text": "...", "tier_hint": "..." } ],
    "provider": "openai",
    "model": "<model used>" }

If the caller does NOT pass a `model` key, the script auto-discovers the
best chat model the OPENAI_API_KEY can reach by listing /v1/models and
matching against the MODEL_PRIORITY table (best-first). The pick is cached
in ~/.claude/.qplan_openai_model_cache.json for CACHE_TTL_HOURS to avoid
hitting /v1/models on every critic round. Force a refresh with the env var
QPLAN_OPENAI_MODEL_REFRESH=1 or by deleting the cache file.

Two backends, picked by the `backend` key on stdin (or QPLAN_OPENAI_BACKEND
env), default "api":

  - "api"     — calls the OpenAI HTTP API. Needs OPENAI_API_KEY. Fails loud
                (non-zero exit + stderr) if the key is missing or the chat
                call errors. Does NOT fall back to a stub or to claude —
                provider distinguishability is the point. The /v1/models
                lookup is the only soft-fail path: on error it falls back to
                a stale cache then HARD_FALLBACK_MODEL.
  - "browser" — drives the logged-in ChatGPT WEB session via Playwright, so
                it needs NO OPENAI_API_KEY (it rides the user's ChatGPT
                subscription). One-time setup: `python openai_critic.py
                --login`. Honest trade-offs, accepted by the user: automating
                the ChatGPT web UI is against OpenAI's ToS, it is brittle (UI
                / Cloudflare changes break it), and it is slower than the API.
                Any failure (Playwright missing, not logged in, selector
                drift, timeout) exits 2 with a clear message so the qPlan
                panel just MUTES this lens instead of crashing the round.

Stdlib only for the "api" backend (no `openai` package needed). The
"browser" backend additionally needs Playwright: `pip install playwright`
then `playwright install chromium`.
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

# Shared chunking helpers (kept in plan_chunker.py so a fix applies once
# to both openai_critic.py and deepseek_critic.py).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from plan_chunker import (  # noqa: E402
    MAX_CHUNK_DEPTH,
    merge_verdicts,
    split_plan,
)

CRITIC_PROMPT = """You are the critic in a qPlan author<->critic loop.

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


class _BudgetExhausted(Exception):
    """Raised when the OpenAI API rejects the call for billing/quota reasons
    (HTTP 402, or 429 with insufficient_quota) — distinct from a transient
    TPM rate-limit. Signals main() to fall back to the browser backend rather
    than muting the lens, so a dead API balance does not stop the round."""


# --- Model auto-discovery -------------------------------------------------

CACHE_PATH = Path.home() / ".claude" / ".qplan_openai_model_cache.json"
CACHE_TTL_HOURS = 24.0

# Best-first priority. Each entry matches a model family root; within a
# matched family we prefer the un-dated stable alias (e.g. `gpt-5` over
# `gpt-5-2025-07-15`) because OpenAI routes the alias to the latest
# snapshot of that family. Order reflects critic-quality vs cost: newest
# general-purpose first, then strong reasoning, then smaller / older
# models as graceful degradation. Add new families at the top as OpenAI
# releases them — this list is the only thing that needs updating.
MODEL_PRIORITY = [
    re.compile(r"^gpt-5\.5(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^gpt-5\.1(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^gpt-5(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^o3-pro(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^o3(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^gpt-5-mini(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^gpt-4\.1(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^o1(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^o3-mini(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^gpt-4\.1-mini(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^gpt-4o(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^gpt-4o-mini(?:-\d{4}-\d{2}-\d{2})?$"),
    re.compile(r"^o1-mini(?:-\d{4}-\d{2}-\d{2})?$"),
]

# Last-resort literal if /v1/models is unreachable AND no cache exists.
# Was gpt-4o; raised 2026-09-16 because gpt-4o is now three families behind and
# the fallback should still be a usable critic, not the oldest thing that works.
HARD_FALLBACK_MODEL = "gpt-5"


def _list_models(api_key: str) -> list[str]:
    req = urllib.request.Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return [m["id"] for m in body.get("data", [])]


# Variants that are cheaper/narrower than their family's general model. A
# critic must never land on one just because its family number sorts high.
_WEAK_VARIANT = re.compile(
    r"(mini|nano|chat-latest|search|audio|realtime|image|tts|whisper"
    r"|embedding|moderation|transcribe|preview|instruct)"
)
_DATED = re.compile(r"-\d{4}-\d{2}-\d{2}$")


def _version_key(model_id: str):
    """Rank a general-purpose OpenAI model by PARSED version; None if not one.

    Added 2026-09-16: MODEL_PRIORITY above topped out at gpt-5.5 while the
    account already served gpt-5.6-luna/sol/terra and gpt-6-astra, so the
    "always pick the highest model" rule was quietly picking a stale one. A
    hand-written list cannot keep up with OpenAI's release cadence; parsing the
    version means the next family (gpt-7, ...) wins with no code change.
    MODEL_PRIORITY is kept below purely as the fallback when nothing parses.
    """
    if _WEAK_VARIANT.search(model_id):
        return None
    m = re.match(r"^gpt-(\d+)(?:\.(\d+))?", model_id)
    if m:
        major, minor = int(m.group(1)), int(m.group(2) or 0)
    elif re.match(r"^o\d+(-pro)?$", model_id):
        # o-series predates the gpt-5 line: rank below every gpt family.
        major, minor = 0, int(re.match(r"^o(\d+)", model_id).group(1))
    else:
        return None
    pro = 1 if "-pro" in model_id else 0
    undated = 0 if _DATED.search(model_id) else 1
    # Same-version codenames (luna/sol/terra) carry no public ordering; the
    # final key is alphabetical purely to make the pick deterministic.
    return (major, minor, pro, undated, model_id)


def _pick_best(available: list[str]) -> str | None:
    ranked = [(k, m) for m in available if (k := _version_key(m)) is not None]
    if ranked:
        return max(ranked)[1]
    for pattern in MODEL_PRIORITY:
        matches = [m for m in available if pattern.match(m)]
        if not matches:
            continue
        # Prefer the un-dated stable alias — OpenAI keeps it pointed at the
        # latest snapshot of the family.
        stable = [m for m in matches if not re.search(r"-\d{4}-\d{2}-\d{2}$", m)]
        if stable:
            return stable[0]
        # Else take the lexicographically latest dated snapshot
        # (YYYY-MM-DD sorts chronologically).
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
        # Cache write failure is non-fatal, but surface it on stderr so a
        # full-disk or permission storm leaves a trace instead of going
        # silent forever. Flagged as a P3 in the qRev pass.
        sys.stderr.write(f"openai_critic: cache write failed (non-fatal): {e}\n")


def discover_model(api_key: str) -> str:
    """Pick the best chat model accessible to OPENAI_API_KEY.

    Cached for CACHE_TTL_HOURS. Force refresh with
    QPLAN_OPENAI_MODEL_REFRESH=1 or by deleting CACHE_PATH.
    """
    if not os.environ.get("QPLAN_OPENAI_MODEL_REFRESH"):
        fresh = _read_cache(allow_stale=False)
        if fresh:
            return fresh

    try:
        available = _list_models(api_key)
    except urllib.error.HTTPError as e:
        # P2.5: 401/403 means the key is bad — re-raise loudly instead of
        # silently falling back to a stale cache or HARD_FALLBACK_MODEL.
        # Hiding auth failures here makes key-rotation issues invisible.
        if e.code in (401, 403):
            sys.stderr.write(
                f"openai_critic: /v1/models returned HTTP {e.code} — bad or "
                f"revoked OPENAI_API_KEY. Fix the key and retry.\n"
            )
            sys.exit(2)
        # Other transient errors (5xx, network blip) — accept stale cache.
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
# Chunking on HTTP 429 is implemented via the shared plan_chunker module
# (split_plan, merge_verdicts, MAX_CHUNK_DEPTH). The retry layer adds two
# extra safeguards beyond the chunker:
#
#   1. MAX_TOTAL_CHUNKS process-wide counter — hard cap on paid API calls
#      per critic round. Pathological 429 storms can otherwise burn 16
#      paid requests per round; this caps the total irrespective of how
#      the split-tree falls out.
#   2. time.sleep(2 ** depth) exponential backoff before each retry so a
#      provider that's actually throttling has a chance to recover before
#      we hammer it with the chunks.
#
# Both flagged as P2.8 in the qRev pass.

MAX_TOTAL_CHUNKS = 8
_total_chunks_submitted = 0


def call_openai(
    api_key: str,
    model: str,
    task: str,
    plan: str,
    ledger: list,
    depth: int = 0,
) -> dict:
    global _total_chunks_submitted
    _total_chunks_submitted += 1
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": CRITIC_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"task": task, "plan": plan, "ledger": ledger},
                    ensure_ascii=False,
                ),
            },
        ],
        "response_format": {"type": "json_object"},
    }
    # 2026-06-10: GPT-5+ models reject any non-default temperature with HTTP
    # 400. Only send temperature for legacy models that accept it.
    # 2026-09-16: this was `model.startswith("gpt-5")`, which is FALSE for
    # gpt-6-astra -- the moment model discovery picked gpt-6 the critic would
    # have sent temperature and taken a 400 on every call. Parse the family
    # number instead of matching a literal prefix, so gpt-7+ stays covered.
    _fam = re.match(r"^gpt-(\d+)", model)
    _modern = (_fam and int(_fam.group(1)) >= 5) or re.match(r"^o\d", model)
    if not _modern:
        payload["temperature"] = 0.3
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
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
        # Budget/quota exhaustion is NOT a transient rate-limit: chunk-splitting
        # cannot help (every retry 429s on a $0 balance). Detect it and signal
        # main() to fall back to the browser backend so a dead balance does not
        # stop the planning round. 402 = Payment Required; 429 +
        # insufficient_quota = billing hard-stop (vs 429 TPM throttle below).
        _low = body_text.lower()
        if e.code == 402 or (
            e.code == 429
            and ("insufficient_quota" in _low or "exceeded your current quota" in _low)
        ):
            raise _BudgetExhausted(body_text)
        # 2026-06-12: TPM caps differ per model (gpt-5.5 chat ~50K, gpt-4o
        # 30K). On 429, split the plan and retry per chunk. Same task and
        # ledger ride along with each chunk so the critic still has full
        # context. See feedback_model_selection_highest.md.
        if (
            e.code == 429
            and depth < MAX_CHUNK_DEPTH
            and _total_chunks_submitted < MAX_TOTAL_CHUNKS
        ):
            parts = split_plan(plan)
            if len(parts) < 2:
                sys.stderr.write(
                    f"openai_critic: HTTP 429 but plan is atomic at depth "
                    f"{depth} — cannot split further. Response: {body_text}\n"
                )
                sys.exit(2)
            # Exponential backoff before retrying. Gives the provider a
            # chance to recover from a real throttle event.
            sleep_s = 2 ** depth
            sys.stderr.write(
                f"openai_critic: TPM 429 at depth {depth}, splitting plan "
                f"into {len(parts)} parts and retrying after {sleep_s}s.\n"
            )
            time.sleep(sleep_s)
            sub_verdicts = [
                call_openai(api_key, model, task, p, ledger, depth + 1)
                for p in parts
            ]
            merged = merge_verdicts(sub_verdicts)
            merged["_chunks_submitted"] = sum(
                v.get("_chunks_submitted", 1) for v in sub_verdicts
            )
            return merged
        if e.code == 429:
            sys.stderr.write(
                f"openai_critic: HTTP 429 but chunk budget exhausted "
                f"(depth={depth}, total_chunks={_total_chunks_submitted}, "
                f"cap={MAX_TOTAL_CHUNKS}). Response: {body_text}\n"
            )
            sys.exit(2)
        sys.stderr.write(f"openai_critic: HTTP {e.code} — {body_text}\n")
        sys.exit(2)
    except urllib.error.URLError as e:
        sys.stderr.write(f"openai_critic: network error — {e}\n")
        sys.exit(2)

    # P1.1: guard the response-shape access. content-filter refusals,
    # finish_reason: "length" without a message.content, future API
    # changes, etc. all show up as KeyError/IndexError otherwise — which
    # would bubble out with exit code 1 instead of the documented 2 and
    # no useful error message.
    try:
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError, TypeError) as e:
        sys.stderr.write(
            f"openai_critic: unexpected response shape ({type(e).__name__}: "
            f"{e}). Raw body: {json.dumps(body)[:1000]}\n"
        )
        sys.exit(2)
    except json.JSONDecodeError as e:
        sys.stderr.write(
            f"openai_critic: response content was not valid JSON: {e}. "
            f"Raw content: {content[:1000] if isinstance(content, str) else content}\n"
        )
        sys.exit(2)


# --- Browser backend (no API key — drives the logged-in ChatGPT web UI) ---
#
# This path automates the ChatGPT web session instead of calling the API, so
# it needs NO OPENAI_API_KEY — it rides the user's existing ChatGPT
# subscription. Trade-offs (documented, accepted by the user): automating the
# ChatGPT web UI is against OpenAI's ToS, it is brittle (UI/selector changes
# and Cloudflare bot-checks can break it), and it is slower than the API.
#
# One-time setup: run `python openai_critic.py --login` once to open a headed
# browser and log in; the session persists in BROWSER_PROFILE_DIR and is
# reused on every later call. Needs Playwright: `pip install playwright` then
# `playwright install chromium`.

# Profile dir is overridable (kill switch / hermetic tests) via env.
BROWSER_PROFILE_DIR = Path(
    os.environ.get(
        "QPLAN_CHATGPT_PROFILE_DIR",
        str(Path.home() / ".claude" / ".qplan_chatgpt_profile"),
    )
)
CHATGPT_URL = "https://chatgpt.com/"
# Selectors tried in order — UI-drift fallback chains.
_COMPOSER_SELECTORS = ("#prompt-textarea", "div[contenteditable='true']", "textarea")
_ASSISTANT_SELECTOR = "[data-message-author-role='assistant']"
_STOP_BUTTON_SELECTORS = ("[data-testid='stop-button']", "button[aria-label*='Stop']")


def _import_playwright():
    """Lazy import so the api backend + smoketest never need Playwright."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: E402

        return sync_playwright
    except Exception:  # ImportError or a partial/broken install
        sys.stderr.write(
            "openai_critic[browser]: Playwright not installed. Run "
            "`pip install playwright` then `playwright install chromium`. "
            "Lens muted for this round.\n"
        )
        sys.exit(2)


def _strip_json_fences(text: str) -> str:
    """ChatGPT often wraps JSON in ```json fences or prose — extract the JSON."""
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(.+?)```", t, re.DOTALL)
    if m:
        return m.group(1).strip()
    i, j = t.find("{"), t.rfind("}")
    if i != -1 and j != -1 and j > i:
        return t[i : j + 1]
    return t


def _looks_logged_in(page) -> bool:
    for sel in _COMPOSER_SELECTORS:
        try:
            if page.locator(sel).count() > 0:
                return True
        except Exception:
            continue
    return False


def _is_generating(page) -> bool:
    for sel in _STOP_BUTTON_SELECTORS:
        try:
            if page.locator(sel).count() > 0:
                return True
        except Exception:
            continue
    return False


def _wait_for_answer(
    page, prior_count: int, timeout_s: int = 240, stable_s: float = 2.5
) -> str:
    """Wait until a NEW assistant message appears and its text stabilises."""
    deadline = time.time() + timeout_s
    last_text = ""
    stable_since = None
    while time.time() < deadline:
        msgs = page.locator(_ASSISTANT_SELECTOR)
        try:
            count = msgs.count()
        except Exception:
            count = 0
        if count > prior_count:
            try:
                cur = msgs.nth(count - 1).inner_text().strip()
            except Exception:
                cur = ""
            if cur and cur == last_text and not _is_generating(page):
                if stable_since and (time.time() - stable_since) >= stable_s:
                    return cur
            else:
                last_text = cur
                stable_since = time.time()
        time.sleep(0.5)
    if last_text:
        return last_text
    sys.stderr.write(
        "openai_critic[browser]: timed out waiting for response. Lens muted.\n"
    )
    sys.exit(2)


def do_login() -> None:
    """One-time interactive login: opens a headed browser to ChatGPT and waits
    until the composer is visible (logged in), persisting the session."""
    sync_playwright = _import_playwright()
    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    ok = False
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(BROWSER_PROFILE_DIR), headless=False
        )
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(CHATGPT_URL, timeout=60000)
            sys.stderr.write(
                "openai_critic[browser]: log in to ChatGPT in the opened "
                "window. Waiting up to 5 min for the composer to appear...\n"
            )
            for _ in range(300):  # ~5 min at 1s poll
                if _looks_logged_in(page):
                    ok = True
                    break
                time.sleep(1)
        finally:
            ctx.close()
    if ok:
        sys.stderr.write("openai_critic[browser]: login saved.\n")
        sys.exit(0)
    sys.stderr.write("openai_critic[browser]: timed out waiting for login.\n")
    sys.exit(2)


def call_openai_browser(task: str, plan: str, ledger: list) -> dict:
    sync_playwright = _import_playwright()
    if not BROWSER_PROFILE_DIR.exists():
        sys.stderr.write(
            "openai_critic[browser]: no saved session. Run "
            "`python openai_critic.py --login` once. Lens muted.\n"
        )
        sys.exit(2)
    headless = os.environ.get("QPLAN_OPENAI_BROWSER_HEADLESS") == "1"
    message = (
        CRITIC_PROMPT
        + "\n\nINPUT (task, plan, ledger as JSON):\n"
        + json.dumps(
            {"task": task, "plan": plan, "ledger": ledger}, ensure_ascii=False
        )
        + "\n\nReturn ONLY the JSON verdict described above."
    )
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(BROWSER_PROFILE_DIR), headless=headless
        )
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(CHATGPT_URL, timeout=60000)
            if not _looks_logged_in(page):
                sys.stderr.write(
                    "openai_critic[browser]: session not logged in (expired?). "
                    "Re-run `--login`. Lens muted.\n"
                )
                sys.exit(2)
            composer = None
            for sel in _COMPOSER_SELECTORS:
                loc = page.locator(sel).first
                try:
                    if loc.count() > 0:
                        composer = loc
                        break
                except Exception:
                    continue
            if composer is None:
                sys.stderr.write(
                    "openai_critic[browser]: composer not found (UI drift). "
                    "Lens muted.\n"
                )
                sys.exit(2)
            prior = page.locator(_ASSISTANT_SELECTOR).count()
            composer.click()
            page.keyboard.insert_text(message)
            page.keyboard.press("Enter")
            text = _wait_for_answer(page, prior)
        finally:
            ctx.close()
    return json.loads(_strip_json_fences(text))


def main() -> None:
    if "--login" in sys.argv[1:]:
        do_login()
        return

    try:
        req_in = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        sys.stderr.write(f"openai_critic: bad JSON on stdin — {e}\n")
        sys.exit(2)

    backend = (
        req_in.get("backend") or os.environ.get("QPLAN_OPENAI_BACKEND") or "api"
    ).lower()
    task = req_in.get("task", "")
    plan = req_in.get("plan", "")
    ledger = req_in.get("ledger", [])

    if backend == "browser":
        try:
            verdict = call_openai_browser(task, plan, ledger)
        except json.JSONDecodeError as e:
            sys.stderr.write(
                "openai_critic[browser]: ChatGPT reply was not valid JSON "
                f"({e}). Lens muted.\n"
            )
            sys.exit(2)
        verdict["provider"] = "openai"
        verdict["model"] = "chatgpt-web (browser session)"
        verdict["backend"] = "browser"
        sys.stdout.write(json.dumps(verdict, ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
        return

    # --- api backend (default) ---
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.stderr.write(
            "openai_critic: OPENAI_API_KEY not set. qPlan does NOT silently "
            "fall back to claude — provider distinguishability is the point. "
            "Set the env var or switch critic_provider back to claude.\n"
        )
        sys.exit(2)

    # stdin (task/plan/ledger) was already read at the top of main().
    # Explicit override locks the model; otherwise auto-discover.
    model = req_in.get("model") or discover_model(api_key)

    try:
        verdict = call_openai(api_key, model, task, plan, ledger)
    except _BudgetExhausted:
        # The key is valid but its balance/quota is dead. Per the user's policy,
        # do NOT stop the round — fall back to the browser (ChatGPT web session),
        # which rides the subscription and needs no balance. Disable this with
        # QPLAN_OPENAI_NO_BROWSER_FALLBACK=1 (then it just mutes the lens).
        if os.environ.get("QPLAN_OPENAI_NO_BROWSER_FALLBACK") == "1":
            sys.stderr.write(
                "openai_critic: API budget exhausted and browser fallback "
                "disabled (QPLAN_OPENAI_NO_BROWSER_FALLBACK=1). Lens muted.\n"
            )
            sys.exit(2)
        sys.stderr.write(
            "openai_critic: API budget/quota exhausted — falling back to the "
            "browser backend (ChatGPT web session). Run `--login` once if it "
            "mutes for not being logged in.\n"
        )
        try:
            verdict = call_openai_browser(task, plan, ledger)
        except json.JSONDecodeError as je:
            sys.stderr.write(
                "openai_critic[browser-fallback]: ChatGPT reply was not valid "
                f"JSON ({je}). Lens muted.\n"
            )
            sys.exit(2)
        verdict["provider"] = "openai"
        verdict["model"] = "chatgpt-web (browser fallback after budget)"
        verdict["backend"] = "browser"
        verdict["chunks_submitted"] = verdict.pop("_chunks_submitted", 1)
        sys.stdout.write(json.dumps(verdict, ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
        return

    verdict["provider"] = "openai"
    verdict["model"] = model
    # Surface chunk count so the caller can tell the plan was split.
    verdict["chunks_submitted"] = verdict.pop("_chunks_submitted", 1)

    sys.stdout.write(json.dumps(verdict, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
