#!/usr/bin/env python3
"""Thin MCP server exposing OpenAI's Sora 2 video API as a tool to Claude Code.

Sora 2 ($0.10/s) and Sora 2 Pro ($0.30/s) generate text-to-video and
image-to-video at 720x1280 (portrait) or 1280x720 (landscape). Output
includes synced audio.

Tools exposed:
- generate_video(prompt, model, size, seconds, ...) -> downloads MP4 to cache,
  returns absolute path
- get_video_status(video_id)                       -> raw status object
- list_videos(limit)                               -> recent video IDs
- delete_video(video_id)                           -> server-side delete

Dependencies:
- mcp                (Anthropic MCP SDK)
- openai>=1.50.0     (Sora API)
- stdlib otherwise

API key resolution (first non-empty wins):
1. OPENAI_API_KEY environment variable
2. File at ~/.claude/.openai_api_key (single line, gitignored).

Register with Claude Code:
    claude mcp add sora-cloud -- python "D:/Projects/super_code/hermes-agent/claude_code_integration/mcp_servers/sora_mcp.py"

Environment overrides:
- SORA_OUTPUT_DIR    default ~/.cache/sora_outputs/
- SORA_POLL_TIMEOUT  default 600 (seconds; typical Sora video < 3 min)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
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

try:
    from openai import OpenAI
except ImportError:
    sys.stderr.write(
        "ERROR: 'openai' package not installed. Run: pip install --user openai\n"
    )
    sys.exit(1)


HOME = Path(os.path.expanduser("~"))
API_KEY_FILE = HOME / ".claude" / ".openai_api_key"
OUTPUT_DIR = Path(
    os.environ.get("SORA_OUTPUT_DIR", str(HOME / ".cache" / "sora_outputs"))
)
POLL_TIMEOUT = int(os.environ.get("SORA_POLL_TIMEOUT", "600"))
SUPPORTED_SIZES = {"1280x720", "720x1280"}
SUPPORTED_MODELS = {"sora-2", "sora-2-pro"}


def _resolve_api_key() -> str:
    """API key from env first, then ~/.claude/.openai_api_key."""
    env_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if env_key:
        return env_key
    if API_KEY_FILE.exists():
        try:
            key = API_KEY_FILE.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(f"cannot read {API_KEY_FILE}: {exc}") from exc
        if key:
            return key
    raise RuntimeError(
        f"No OpenAI API key. Set OPENAI_API_KEY in the environment or "
        f"write one line to {API_KEY_FILE} (gitignored, never committed)."
    )


_client: OpenAI | None = None


def _client_or_init() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=_resolve_api_key())
    return _client


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

server: Server = Server("sora-cloud")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="generate_video",
            description=(
                "Generate a video on OpenAI Sora 2 and download it locally. "
                "Pricing: sora-2 = $0.10/s, sora-2-pro = $0.30/s. Output is "
                "MP4 with synced audio at 1280x720 (landscape) or 720x1280 "
                "(portrait). Polls until ready (typically 1-3 min), then "
                "downloads to SORA_OUTPUT_DIR. Returns the absolute file path."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Positive prompt"},
                    "model": {
                        "type": "string",
                        "enum": list(SUPPORTED_MODELS),
                        "default": "sora-2",
                    },
                    "size": {
                        "type": "string",
                        "enum": list(SUPPORTED_SIZES),
                        "default": "1280x720",
                    },
                    "seconds": {
                        "type": "integer",
                        "default": 4,
                        "description": "Video length in seconds",
                    },
                    "input_reference": {
                        "type": "string",
                        "description": (
                            "Optional: path to an input image (image-to-video). "
                            "If supplied, the file is uploaded with the request."
                        ),
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="get_video_status",
            description="Get raw status object for a Sora video by ID.",
            inputSchema={
                "type": "object",
                "properties": {"video_id": {"type": "string"}},
                "required": ["video_id"],
            },
        ),
        Tool(
            name="list_videos",
            description="List your most recent Sora videos (default 10).",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10, "maximum": 100}
                },
            },
        ),
        Tool(
            name="delete_video",
            description="Server-side delete a Sora video by ID.",
            inputSchema={
                "type": "object",
                "properties": {"video_id": {"type": "string"}},
                "required": ["video_id"],
            },
        ),
    ]


def _ok(payload: dict) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(payload, indent=2, default=str))]


def _err(msg: str) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps({"error": msg}, indent=2))]


def _download_video(client: OpenAI, video_id: str, target_path: Path) -> Path:
    """Stream the video content to disk via client.videos.download_content."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    # The SDK returns a streaming response object; iterate bytes
    resp = client.videos.download_content(video_id)
    with target_path.open("wb") as f:
        # OpenAI SDK versions return either a raw bytes object or a streaming
        # response; handle both.
        if hasattr(resp, "iter_bytes"):
            for chunk in resp.iter_bytes():
                f.write(chunk)
        elif hasattr(resp, "read"):
            f.write(resp.read())
        elif hasattr(resp, "content"):
            f.write(resp.content)
        else:
            f.write(bytes(resp))
    return target_path


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        client = _client_or_init()

        if name == "generate_video":
            prompt = arguments.get("prompt", "").strip()
            if not prompt:
                return _err("prompt is required and must be non-empty")
            model = arguments.get("model", "sora-2")
            size = arguments.get("size", "1280x720")
            seconds = int(arguments.get("seconds", 4))
            ref = arguments.get("input_reference")

            if model not in SUPPORTED_MODELS:
                return _err(f"model must be one of {sorted(SUPPORTED_MODELS)}")
            if size not in SUPPORTED_SIZES:
                return _err(f"size must be one of {sorted(SUPPORTED_SIZES)}")
            if seconds < 1 or seconds > 60:
                return _err("seconds must be in [1, 60]")

            create_kwargs: dict[str, Any] = {
                "model": model,
                "prompt": prompt,
                "size": size,
                "seconds": str(seconds),
            }
            if ref:
                p = Path(ref)
                if not p.exists():
                    return _err(f"input_reference path not found: {p}")
                with p.open("rb") as f:
                    create_kwargs["input_reference"] = f
                    video = client.videos.create_and_poll(
                        poll_interval=2.0, timeout=POLL_TIMEOUT, **create_kwargs
                    )
            else:
                video = client.videos.create_and_poll(
                    poll_interval=2.0, timeout=POLL_TIMEOUT, **create_kwargs
                )

            if getattr(video, "status", "") != "completed":
                return _err(
                    f"video did not complete: status={getattr(video, 'status', '?')}, "
                    f"error={getattr(video, 'error', None)}"
                )

            ts = int(time.time())
            target = OUTPUT_DIR / f"sora_{ts}_{video.id}.mp4"
            _download_video(client, video.id, target)
            return _ok(
                {
                    "video_id": video.id,
                    "model": model,
                    "size": size,
                    "seconds": seconds,
                    "output_path": str(target),
                    "estimated_cost_usd": round(
                        seconds * (0.30 if model == "sora-2-pro" else 0.10), 2
                    ),
                }
            )

        if name == "get_video_status":
            vid = arguments.get("video_id", "").strip()
            if not vid:
                return _err("video_id is required")
            v = client.videos.retrieve(vid)
            return _ok({"video_id": vid, "status": v.status, "raw": v.model_dump()})

        if name == "list_videos":
            limit = min(int(arguments.get("limit", 10)), 100)
            videos = client.videos.list(limit=limit)
            return _ok(
                {
                    "videos": [
                        {
                            "id": v.id,
                            "status": v.status,
                            "created_at": v.created_at,
                            "model": getattr(v, "model", None),
                        }
                        for v in videos.data
                    ]
                }
            )

        if name == "delete_video":
            vid = arguments.get("video_id", "").strip()
            if not vid:
                return _err("video_id is required")
            client.videos.delete(vid)
            return _ok({"deleted": vid})

        return _err(f"unknown tool: {name}")

    except Exception as e:
        return _err(f"{type(e).__name__}: {e}")


async def _main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(_main())
