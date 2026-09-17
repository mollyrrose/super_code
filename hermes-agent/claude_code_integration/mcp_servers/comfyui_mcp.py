#!/usr/bin/env python3
"""Thin MCP server exposing local ComfyUI as a video-generation tool to Claude Code.

Architecture: Claude Code spawns this server via `claude mcp add`, the server
talks JSON-RPC over stdio, and forwards requests to a running ComfyUI instance
at http://127.0.0.1:8188 (Tier C launch script default). No model loading or
inference happens here — ComfyUI does all the work.

Tools exposed:
- generate_video(prompt, width, height, length_frames, steps) -> output_path
- get_queue_status() -> queue snapshot
- cancel_task(prompt_id) -> deletion confirmation

Workflow handling: the actual node graph (LTX-Video T2V) is loaded from
~/ai_video/workflows/ltxv_t2v.json (the user saves it from ComfyUI's
"Browse Templates -> Video -> LTX-Video" + "Save (API Format)"). This server
substitutes prompt + dimensions + length into the saved graph by class_type
match, never authors a graph from scratch — that responsibility stays with
ComfyUI's UI where the user can visually verify the result.

Dependencies:
- mcp (Anthropic MCP SDK, install: pip install mcp)
- stdlib only otherwise (urllib, json, time, pathlib)

Register with Claude Code:
    claude mcp add comfyui-local -- python "D:/Projects/super_code/hermes-agent/claude_code_integration/mcp_servers/comfyui_mcp.py"

Environment overrides (optional):
- COMFYUI_URL          default http://127.0.0.1:8188
- COMFYUI_WORKFLOW_DIR default D:/Projects/super_code/ai_video/workflows
- COMFYUI_OUTPUT_DIR   default <comfyui repo>/output  (used to resolve returned filenames to absolute paths)
- COMFYUI_POLL_TIMEOUT default 900 (seconds, 15 min — Tier C 5s clip takes 5-15 min)
"""

from __future__ import annotations

import asyncio
import copy
import json
import os
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
except ImportError:
    sys.stderr.write(
        "ERROR: 'mcp' package not installed. Run: pip install --user mcp\n"
    )
    sys.exit(1)


COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
WORKFLOW_DIR = Path(
    os.environ.get(
        "COMFYUI_WORKFLOW_DIR",
        "D:/Projects/super_code/ai_video/workflows",
    )
)
OUTPUT_DIR = Path(
    os.environ.get(
        "COMFYUI_OUTPUT_DIR",
        "D:/Projects/super_code/ai_video/comfyui/output",
    )
)
POLL_TIMEOUT = int(os.environ.get("COMFYUI_POLL_TIMEOUT", "900"))
POLL_INTERVAL = 2.0  # seconds between /history checks

WORKFLOW_TEMPLATE_NAME = "ltxv_t2v.json"
FLOAT_WORKFLOW_NAME = "float_t2v.json"
T2I_WORKFLOW_NAME = "t2i.json"
I2V_WORKFLOW_NAME = "i2v.json"
CLIENT_ID = str(uuid.uuid4())  # stable for this server lifetime

# Emotion options supported by the FLOAT pipeline. "none" = no override
# (the model picks based on audio prosody). The rest are forced.
FLOAT_EMOTIONS = ("none", "happy", "sad", "angry", "surprise", "fear", "disgust", "contempt", "neutral")


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only — no requests dep)
# ---------------------------------------------------------------------------

def _http_post(path: str, payload: dict, timeout: float = 15.0) -> dict:
    url = f"{COMFYUI_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get(path: str, timeout: float = 15.0) -> dict:
    url = f"{COMFYUI_URL}{path}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Workflow patching — substitute prompt + dims into saved graph by class_type
# ---------------------------------------------------------------------------

def _load_workflow_template() -> dict:
    """Load the user's saved LTX T2V workflow JSON (API format).

    Raises FileNotFoundError with a clear how-to-fix message if the file
    doesn't exist — that's the most common failure mode the first time.
    """
    path = WORKFLOW_DIR / WORKFLOW_TEMPLATE_NAME
    if not path.exists():
        raise FileNotFoundError(
            f"No workflow at {path}. Open ComfyUI in your browser, pick "
            f"'Browse Templates -> Video -> LTX-Video' (or load any LTX T2V "
            f"workflow), and use 'Save (API Format)' to write the JSON to "
            f"that exact path. Then retry."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _patch_workflow(
    workflow: dict,
    prompt: str,
    width: int,
    height: int,
    length_frames: int,
    steps: int,
) -> dict:
    """Patch a copy of the workflow: prompt text, dimensions, length, steps.

    Strategy: scan nodes by class_type. ComfyUI workflows in API format have
    the shape {"<node_id>": {"class_type": "...", "inputs": {...}}, ...}.

    Patches applied (only when a matching node exists — silent skip otherwise):
    - Any CLIPTextEncode / T5TextEncode with a 'text' input: set positive prompt
      on the first one found. (Negative prompt nodes typically have empty text
      so we deliberately skip empty-text nodes.)
    - EmptyLatentVideo / EmptyHunyuanLatentVideo / LTXVideoLatent: set width,
      height, length.
    - KSampler / KSamplerAdvanced: set steps.

    Returns a new dict (does not mutate the input).
    """
    out = copy.deepcopy(workflow)
    if not isinstance(out, dict):
        raise ValueError("workflow root must be a JSON object (API format)")

    set_prompt = False
    for node_id, node in out.items():
        if not isinstance(node, dict):
            continue
        ctype = node.get("class_type", "")
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue

        # Prompt: text-encoder nodes with a non-empty 'text' input
        if (
            not set_prompt
            and ctype in ("CLIPTextEncode", "T5TextEncode")
            and isinstance(inputs.get("text"), str)
            and inputs.get("text", "").strip()
        ):
            inputs["text"] = prompt
            set_prompt = True

        # Dimensions + length
        if ctype in (
            "EmptyLatentVideo",
            "EmptyHunyuanLatentVideo",
            "LTXVideoLatent",
            "EmptyLTXVLatentVideo",
        ):
            if "width" in inputs:
                inputs["width"] = width
            if "height" in inputs:
                inputs["height"] = height
            if "length" in inputs:
                inputs["length"] = length_frames
            if "num_frames" in inputs:
                inputs["num_frames"] = length_frames

        # Sampler / scheduler steps. The LTX templates put `steps` on the
        # scheduler (LTXVScheduler) and the sampler is the K-sampler-free
        # SamplerCustom. Hunyuan's template uses BasicScheduler the same way.
        # Patch wherever `steps` actually lives.
        if ctype in (
            "KSampler",
            "KSamplerAdvanced",
            "LTXVScheduler",
            "BasicScheduler",
        ) and "steps" in inputs:
            inputs["steps"] = steps

    if not set_prompt:
        raise ValueError(
            "Could not find a positive-prompt text-encoder node in the saved "
            "workflow. Make sure the workflow has a CLIPTextEncode or "
            "T5TextEncode node with non-empty default text."
        )
    return out


# ---------------------------------------------------------------------------
# FLOAT (talking-head) workflow loading + patching
# ---------------------------------------------------------------------------

def _load_float_workflow() -> dict:
    """Load the user's saved FLOAT T2V workflow (API format).

    Raises FileNotFoundError with a clear how-to-fix message if absent —
    the user has to Export (API) from the UI once.
    """
    path = WORKFLOW_DIR / FLOAT_WORKFLOW_NAME
    if not path.exists():
        raise FileNotFoundError(
            f"No talking-head workflow at {path}. In ComfyUI UI, open "
            f"float_talking_head.json then use Workflow -> Export (API) to "
            f"write to that exact path. Then retry."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _patch_float_workflow(
    workflow: dict,
    image_filename: str,
    audio_filename: str,
    emotion: str,
    fps: float,
) -> dict:
    """Patch a copy of the FLOAT workflow with the requested inputs.

    Strategy: scan nodes by class_type; LoadImage gets the image name,
    LoadAudio gets the audio name, FloatProcess gets emotion (if !='none'),
    and the FPS PrimitiveFloat node (if present) gets fps.

    Both inputs/filenames must already exist in ComfyUI's input/ folder —
    drop them there before calling. The MCP does not upload files.
    """
    out = copy.deepcopy(workflow)
    if not isinstance(out, dict):
        raise ValueError("workflow root must be a JSON object (API format)")

    # P2.2: separate branches (not elif) so a workflow with multiple
    # LoadImage / LoadAudio nodes patches the FIRST one of each and leaves
    # the rest alone — the original `elif` chain only visited one matching
    # class_type per node. The set_* guards prevent us from accidentally
    # overwriting subsequent matches.
    # P2.2 (FPS): add a `set_fps` guard so a workflow with multiple
    # PrimitiveFloat nodes (which IS plausible — confidence, seed
    # multipliers, etc.) doesn't blanket-overwrite everything with the
    # fps value.
    set_image = False
    set_audio = False
    set_fps = False
    set_emotion = False
    for _nid, node in out.items():
        if not isinstance(node, dict):
            continue
        ctype = node.get("class_type", "")
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue

        if ctype == "LoadImage" and "image" in inputs and not set_image:
            inputs["image"] = image_filename
            set_image = True
        if ctype == "LoadAudio" and "audio" in inputs and not set_audio:
            inputs["audio"] = audio_filename
            set_audio = True
        if (
            ctype == "FloatProcess"
            and emotion
            and emotion != "none"
            and "emotion" in inputs
            and not set_emotion
        ):
            inputs["emotion"] = emotion
            set_emotion = True
        if ctype == "PrimitiveFloat" and "value" in inputs and not set_fps:
            # Heuristic: the FPS node is the only PrimitiveFloat in the
            # shipped FLOAT workflow. The `set_fps` guard scopes the
            # heuristic to one node so a future workflow with multiple
            # PrimitiveFloat nodes still works correctly for the first.
            inputs["value"] = float(fps)
            set_fps = True

    if not set_image:
        raise ValueError("FLOAT workflow has no LoadImage node — wrong template?")
    if not set_audio:
        raise ValueError("FLOAT workflow has no LoadAudio node — wrong template?")
    return out


# ---------------------------------------------------------------------------
# T2I (text-to-image) workflow loading + patching
# ---------------------------------------------------------------------------

def _load_t2i_workflow() -> dict:
    """Load the user's saved T2I workflow (API format)."""
    path = WORKFLOW_DIR / T2I_WORKFLOW_NAME
    if not path.exists():
        raise FileNotFoundError(
            f"No T2I workflow at {path}. In ComfyUI UI, pick a "
            f"text-to-image template (e.g. Flux.1 Schnell, Z-Image-Turbo, "
            f"or any SD checkpoint), set the prompt to something non-empty, "
            f"then use Workflow -> Export (API) to write to that exact "
            f"path. Then retry."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _patch_t2i_workflow(
    workflow: dict, prompt: str, width: int, height: int, steps: int
) -> dict:
    """Patch a copy of the T2I workflow: prompt, dimensions, steps.

    Strategy mirrors `_patch_workflow` (LTX T2V) but targets image latent
    classes. Each patched node has a `set_*` guard so multi-encoder
    workflows (e.g. Flux's dual CLIP + T5) get exactly the FIRST
    positive-prompt encoder filled in, leaving the negative-prompt
    encoder alone.
    """
    out = copy.deepcopy(workflow)
    if not isinstance(out, dict):
        raise ValueError("workflow root must be a JSON object (API format)")
    set_prompt = False
    set_dims = False
    set_steps = False
    for _nid, node in out.items():
        if not isinstance(node, dict):
            continue
        ctype = node.get("class_type", "")
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue

        if (
            not set_prompt
            and ctype in ("CLIPTextEncode", "T5TextEncode")
            and isinstance(inputs.get("text"), str)
            and inputs.get("text", "").strip()
        ):
            inputs["text"] = prompt
            set_prompt = True

        if (
            ctype in ("EmptyLatentImage", "EmptySD3LatentImage", "ModelSamplingFlux")
            and not set_dims
        ):
            if "width" in inputs:
                inputs["width"] = width
            if "height" in inputs:
                inputs["height"] = height
            set_dims = True

        if (
            ctype in ("KSampler", "KSamplerAdvanced", "BasicScheduler")
            and "steps" in inputs
            and not set_steps
        ):
            inputs["steps"] = steps
            set_steps = True

    if not set_prompt:
        raise ValueError(
            "T2I workflow has no positive-prompt text-encoder node with "
            "non-empty default text — make sure the saved template has a "
            "CLIPTextEncode / T5TextEncode with placeholder text."
        )
    return out


# ---------------------------------------------------------------------------
# I2V (image-to-video) workflow loading + patching
# ---------------------------------------------------------------------------

def _load_i2v_workflow() -> dict:
    """Load the user's saved I2V workflow (API format)."""
    path = WORKFLOW_DIR / I2V_WORKFLOW_NAME
    if not path.exists():
        raise FileNotFoundError(
            f"No I2V workflow at {path}. In ComfyUI UI, pick an "
            f"image-to-video template (e.g. LTX-Video Image to Video, "
            f"Wan 2.2 I2V, Hunyuan I2V), then use Workflow -> Export "
            f"(API) to write to that exact path. Then retry."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _patch_i2v_workflow(
    workflow: dict,
    image_filename: str,
    prompt: str,
    width: int,
    height: int,
    length_frames: int,
    steps: int,
) -> dict:
    """Patch a copy of the I2V workflow.

    LoadImage = reference frame. First text-encoder = motion / scene
    description. Same dimensions / length / steps patching pattern as
    the FLOAT and T2V patchers.
    """
    out = copy.deepcopy(workflow)
    if not isinstance(out, dict):
        raise ValueError("workflow root must be a JSON object (API format)")
    set_image = False
    set_prompt = False
    set_dims = False
    set_steps = False
    for _nid, node in out.items():
        if not isinstance(node, dict):
            continue
        ctype = node.get("class_type", "")
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue

        if ctype == "LoadImage" and "image" in inputs and not set_image:
            inputs["image"] = image_filename
            set_image = True

        if (
            not set_prompt
            and ctype in ("CLIPTextEncode", "T5TextEncode")
            and isinstance(inputs.get("text"), str)
            and inputs.get("text", "").strip()
        ):
            inputs["text"] = prompt
            set_prompt = True

        if (
            ctype in (
                "EmptyLatentVideo",
                "EmptyHunyuanLatentVideo",
                "LTXVideoLatent",
                "EmptyLTXVLatentVideo",
            )
            and not set_dims
        ):
            if "width" in inputs:
                inputs["width"] = width
            if "height" in inputs:
                inputs["height"] = height
            if "length" in inputs:
                inputs["length"] = length_frames
            if "num_frames" in inputs:
                inputs["num_frames"] = length_frames
            set_dims = True

        if (
            ctype in ("KSampler", "KSamplerAdvanced", "LTXVScheduler", "BasicScheduler")
            and "steps" in inputs
            and not set_steps
        ):
            inputs["steps"] = steps
            set_steps = True

    if not set_image:
        raise ValueError("I2V workflow has no LoadImage node — wrong template?")
    if not set_prompt:
        raise ValueError(
            "I2V workflow has no positive-prompt text-encoder node — "
            "make sure the saved template has a CLIPTextEncode / "
            "T5TextEncode with non-empty default text."
        )
    return out


# ---------------------------------------------------------------------------
# Submit + poll
# ---------------------------------------------------------------------------

def _submit_workflow(workflow: dict) -> str:
    """POST workflow to ComfyUI; return prompt_id."""
    resp = _http_post("/prompt", {"prompt": workflow, "client_id": CLIENT_ID})
    pid = resp.get("prompt_id")
    if not pid:
        raise RuntimeError(f"ComfyUI did not return a prompt_id: {resp}")
    return pid


def _wait_for_completion(prompt_id: str) -> dict:
    """Poll /history/<prompt_id> until the entry shows up + has outputs.

    Returns the history entry dict. Raises TimeoutError after POLL_TIMEOUT.

    P2.4: a consecutive-URLError counter surfaces a stderr warning after
    10 retries in a row, so a ComfyUI crash mid-generation produces an
    operator-visible signal instead of silently retrying for the full
    15-minute timeout.
    """
    deadline = time.monotonic() + POLL_TIMEOUT
    consecutive_url_errors = 0
    warned = False
    while time.monotonic() < deadline:
        try:
            history = _http_get(f"/history/{prompt_id}")
            consecutive_url_errors = 0
            warned = False
        except urllib.error.URLError as e:
            consecutive_url_errors += 1
            if consecutive_url_errors >= 10 and not warned:
                sys.stderr.write(
                    f"comfyui_mcp: {consecutive_url_errors} consecutive poll "
                    f"failures contacting {COMFYUI_URL} (last: {e}). ComfyUI "
                    f"may have crashed; will keep retrying until "
                    f"POLL_TIMEOUT={POLL_TIMEOUT}s.\n"
                )
                warned = True
            time.sleep(POLL_INTERVAL)
            continue
        entry = history.get(prompt_id)
        if entry and entry.get("outputs"):
            return entry
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(
        f"ComfyUI did not finish prompt {prompt_id} within {POLL_TIMEOUT}s "
        f"(Tier C 5s clip typically 5-15 min; raise COMFYUI_POLL_TIMEOUT if "
        f"you're consistently hitting this)."
    )


def _extract_output_paths(history_entry: dict) -> list[str]:
    """Find produced video/image file paths in the history entry's outputs.

    ComfyUI output entries look like:
        {"images": [{"filename": "...", "subfolder": "...", "type": "output"}]}
        {"gifs": [...]}, {"videos": [...]}  (depends on the save node)
    We resolve filenames to absolute paths under OUTPUT_DIR.
    """
    paths: list[str] = []
    outputs = history_entry.get("outputs", {})
    for _node_id, out in outputs.items():
        if not isinstance(out, dict):
            continue
        for key in ("images", "gifs", "videos", "files"):
            for item in out.get(key, []) or []:
                fn = item.get("filename")
                sub = item.get("subfolder", "") or ""
                if fn:
                    p = OUTPUT_DIR / sub / fn if sub else OUTPUT_DIR / fn
                    paths.append(str(p))
    return paths


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

server: Server = Server("comfyui-local")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="generate_video",
            description=(
                "Generate a video clip on the local ComfyUI instance using the "
                "saved LTX-Video T2V workflow. Substitutes prompt + dimensions "
                "into the workflow and submits to /prompt; polls /history "
                "until done. Tier C defaults (832x480, 121 frames at 24 fps = "
                "~5 s clip, 20 sampling steps) typically take 5-15 minutes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Positive prompt"},
                    "width": {"type": "integer", "default": 832},
                    "height": {"type": "integer", "default": 480},
                    "length_frames": {
                        "type": "integer",
                        "default": 121,
                        "description": "Total frames; 121 @ 24 fps = ~5 s",
                    },
                    "steps": {"type": "integer", "default": 20},
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="get_queue_status",
            description="Get ComfyUI's current queue state (running + pending).",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="cancel_task",
            description="Cancel a pending or running prompt by its prompt_id.",
            inputSchema={
                "type": "object",
                "properties": {"prompt_id": {"type": "string"}},
                "required": ["prompt_id"],
            },
        ),
        Tool(
            name="generate_image",
            description=(
                "Generate a still image on the local ComfyUI using a saved "
                "text-to-image workflow (Flux / Z-Image-Turbo / SD checkpoint "
                "/ etc.). Requires a user-saved workflow JSON at "
                "ai_video/workflows/t2i.json (Export API from the UI once). "
                "Returns the absolute path to the generated PNG."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Positive prompt"},
                    "width": {"type": "integer", "default": 1024},
                    "height": {"type": "integer", "default": 1024},
                    "steps": {"type": "integer", "default": 20},
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="generate_image_to_video",
            description=(
                "Animate a still image into a video on the local ComfyUI "
                "using a saved image-to-video workflow (LTX I2V, Wan 2.2 "
                "I2V, Hunyuan I2V, etc.). Requires a user-saved workflow "
                "JSON at ai_video/workflows/i2v.json. The reference image "
                "must already exist inside ai_video/comfyui/input/ — this "
                "tool does not upload."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "image_filename": {
                        "type": "string",
                        "description": "Bare filename of the reference image in ai_video/comfyui/input/",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Motion / scene description to drive the animation",
                    },
                    "width": {"type": "integer", "default": 832},
                    "height": {"type": "integer", "default": 480},
                    "length_frames": {"type": "integer", "default": 121},
                    "steps": {"type": "integer", "default": 20},
                },
                "required": ["image_filename", "prompt"],
            },
        ),
        Tool(
            name="generate_talking_head",
            description=(
                "Generate a talking-portrait video on the local ComfyUI using "
                "the FLOAT pipeline (audio-driven lip-sync). The reference "
                "image and audio file must already exist inside "
                "ai_video/comfyui/input/ — this tool does not upload. "
                "Typical Tier C wall-clock: 1-2 minutes per 5-second clip. "
                "License reminder: FLOAT is CC BY-NC-SA 4.0 — non-commercial only."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "image_filename": {
                        "type": "string",
                        "description": "Filename of the reference portrait inside ai_video/comfyui/input/ (e.g. 'sam_altman_512x512.jpg').",
                    },
                    "audio_filename": {
                        "type": "string",
                        "description": "Filename of the audio inside ai_video/comfyui/input/ (e.g. 'aud-sample-vs-1.wav').",
                    },
                    "emotion": {
                        "type": "string",
                        "enum": list(FLOAT_EMOTIONS),
                        "default": "none",
                        "description": "Force a specific emotion override, or 'none' to let the model infer from audio prosody.",
                    },
                    "fps": {
                        "type": "number",
                        "default": 25,
                        "description": "Output frame rate.",
                    },
                },
                "required": ["image_filename", "audio_filename"],
            },
        ),
    ]


def _ok(payload: dict) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(payload, indent=2))]


def _err(msg: str) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps({"error": msg}, indent=2))]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "generate_video":
            prompt = arguments.get("prompt", "").strip()
            if not prompt:
                return _err("prompt is required and must be non-empty")
            width = int(arguments.get("width", 832))
            height = int(arguments.get("height", 480))
            length_frames = int(arguments.get("length_frames", 121))
            steps = int(arguments.get("steps", 20))

            template = _load_workflow_template()
            patched = _patch_workflow(
                template, prompt, width, height, length_frames, steps
            )
            t0 = time.monotonic()
            prompt_id = _submit_workflow(patched)
            entry = _wait_for_completion(prompt_id)
            paths = _extract_output_paths(entry)
            dt = time.monotonic() - t0
            return _ok(
                {
                    "prompt_id": prompt_id,
                    "duration_s": round(dt, 1),
                    "outputs": paths,
                    "workflow_template": str(WORKFLOW_DIR / WORKFLOW_TEMPLATE_NAME),
                }
            )

        if name == "get_queue_status":
            return _ok(_http_get("/queue"))

        if name == "cancel_task":
            pid = arguments.get("prompt_id", "").strip()
            if not pid:
                return _err("prompt_id is required")
            resp = _http_post("/queue", {"delete": [pid]})
            return _ok({"deleted": pid, "response": resp})

        if name == "generate_image":
            prompt = arguments.get("prompt", "").strip()
            if not prompt:
                return _err("prompt is required and must be non-empty")
            width = int(arguments.get("width", 1024))
            height = int(arguments.get("height", 1024))
            steps = int(arguments.get("steps", 20))

            template = _load_t2i_workflow()
            patched = _patch_t2i_workflow(template, prompt, width, height, steps)
            t0 = time.monotonic()
            prompt_id = _submit_workflow(patched)
            entry = _wait_for_completion(prompt_id)
            paths = _extract_output_paths(entry)
            dt = time.monotonic() - t0
            return _ok({
                "prompt_id": prompt_id,
                "duration_s": round(dt, 1),
                "outputs": paths,
                "workflow_template": str(WORKFLOW_DIR / T2I_WORKFLOW_NAME),
            })

        if name == "generate_image_to_video":
            image_name = arguments.get("image_filename", "").strip()
            prompt = arguments.get("prompt", "").strip()
            if not image_name:
                return _err("image_filename is required (file must exist in ai_video/comfyui/input/)")
            if not prompt:
                return _err("prompt is required (describes the motion / scene change)")
            # Same path-traversal guard as generate_talking_head — bare filename only.
            if "/" in image_name or "\\" in image_name or image_name.startswith(".."):
                return _err(
                    f"image_filename must be a bare filename (no slashes, no '..'). "
                    f"Got: {image_name!r}"
                )
            width = int(arguments.get("width", 832))
            height = int(arguments.get("height", 480))
            length_frames = int(arguments.get("length_frames", 121))
            steps = int(arguments.get("steps", 20))

            template = _load_i2v_workflow()
            patched = _patch_i2v_workflow(
                template, image_name, prompt, width, height, length_frames, steps
            )
            t0 = time.monotonic()
            prompt_id = _submit_workflow(patched)
            entry = _wait_for_completion(prompt_id)
            paths = _extract_output_paths(entry)
            dt = time.monotonic() - t0
            return _ok({
                "prompt_id": prompt_id,
                "duration_s": round(dt, 1),
                "outputs": paths,
                "workflow_template": str(WORKFLOW_DIR / I2V_WORKFLOW_NAME),
            })

        if name == "generate_talking_head":
            image_name = arguments.get("image_filename", "").strip()
            audio_name = arguments.get("audio_filename", "").strip()
            emotion = arguments.get("emotion", "none")
            fps = float(arguments.get("fps", 25))

            if not image_name:
                return _err("image_filename is required (file must exist in ai_video/comfyui/input/)")
            if not audio_name:
                return _err("audio_filename is required (file must exist in ai_video/comfyui/input/)")
            # P2.3: defensive path-traversal check. ComfyUI internally
            # resolves these relative to its input/ folder and is supposed
            # to sandbox there, but a stripped filename is cheap insurance
            # and makes the contract explicit ("we only accept a bare
            # filename, no slashes").
            for arg_name, val in (("image_filename", image_name), ("audio_filename", audio_name)):
                if "/" in val or "\\" in val or val.startswith(".."):
                    return _err(
                        f"{arg_name} must be a bare filename (no slashes, "
                        f"no '..'). Got: {val!r}"
                    )
            if emotion not in FLOAT_EMOTIONS:
                return _err(f"emotion must be one of {list(FLOAT_EMOTIONS)}")

            template = _load_float_workflow()
            patched = _patch_float_workflow(template, image_name, audio_name, emotion, fps)
            t0 = time.monotonic()
            prompt_id = _submit_workflow(patched)
            entry = _wait_for_completion(prompt_id)
            paths = _extract_output_paths(entry)
            dt = time.monotonic() - t0
            return _ok({
                "prompt_id": prompt_id,
                "duration_s": round(dt, 1),
                "outputs": paths,
                "workflow_template": str(WORKFLOW_DIR / FLOAT_WORKFLOW_NAME),
                "license_note": "FLOAT model is CC BY-NC-SA 4.0 (non-commercial)",
            })

        return _err(f"unknown tool: {name}")

    except FileNotFoundError as e:
        return _err(str(e))
    except (urllib.error.URLError, ConnectionError) as e:
        return _err(
            f"Cannot reach ComfyUI at {COMFYUI_URL}: {e}. Is start_comfyui.bat "
            f"running? Default URL is http://127.0.0.1:8188."
        )
    except json.JSONDecodeError as e:
        # Malformed workflow file or unexpected response shape from ComfyUI.
        traceback.print_exc(file=sys.stderr)
        return _err(f"JSON decode error: {e}. Check the workflow template syntax.")
    except ValueError as e:
        # Patcher complains about wrong-shape templates or bad inputs.
        traceback.print_exc(file=sys.stderr)
        return _err(f"ValueError: {e}")
    except Exception as e:
        # P1.2: surface the full traceback on stderr so operators see what
        # actually broke instead of an opaque tool-error JSON. The bare
        # except still returns a clean error to Claude Code so the tool
        # call doesn't crash the MCP server, but the trace is now in
        # ComfyUI's stderr stream where it's findable.
        traceback.print_exc(file=sys.stderr)
        return _err(f"{type(e).__name__}: {e}")


async def _main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(_main())
