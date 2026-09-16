#!/usr/bin/env python3
"""Local text-to-image with Z-Image, including the non-distilled base model.

Why this exists: the ComfyUI install runs `z_image_turbo`, the DISTILLED 8-step
variant of Z-Image. Distillation trades quality for speed by construction, so
"the output is not good enough" is at least partly a model choice rather than a
GPU limit. `Tongyi-MAI/Z-Image` is the same architecture undistilled: 30-50
steps with CFG 3-5, and the model card claims noticeably richer detail.

This runs it on the laptop rather than the GPU rig on purpose. Measured
2026-09-16: the laptop has 31.7 GB of system RAM against the rig's 7.7 GB, and
CPU offload -- the only way to run a ~20 GB pipeline behind 8 GB of VRAM --
needs system memory to hold the weights. The rig cannot do it.

It uses its own venv (`.venv-image`), NOT the ComfyUI one: diffusers 0.40 needs
a newer `huggingface_hub` than ComfyUI has pinned, and upgrading in place would
risk a working install for no reason.

Usage:
    python scripts/lib/run_image.py --probe
    python scripts/lib/run_image.py --prompt "..." --out out.png
    python scripts/lib/run_image.py --prompt "..." --steps 40 --cfg 4.0 --seed 42
    python scripts/lib/run_image.py --prompt "..." --compare      # base vs few-step

KILL SWITCH: delete this file, or delete `.venv-image/`. It writes only to --out.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

DEFAULT_MODEL = "ai_video/models/Z-Image-Base"
# The model card's guidance for the undistilled model. The turbo variant runs at
# 8 steps with no CFG, which is what makes the comparison meaningful.
BASE_STEPS = 40
BASE_CFG = 4.0


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def resolve_model(arg: str) -> str:
    """Accept a local directory or a Hub id; prefer the local copy."""
    p = Path(arg)
    if not p.is_absolute():
        p = repo_root() / arg
    return str(p) if p.is_dir() else arg


def probe(model_arg: str) -> dict:
    info: dict = {}
    try:
        import torch
        info["torch"] = torch.__version__
        info["cuda"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            info["device"] = torch.cuda.get_device_name(0)
            info["vram_gb"] = round(
                torch.cuda.get_device_properties(0).total_memory / 1e9, 1)
    except Exception as e:
        info["torch_error"] = repr(e)[:200]
    try:
        import diffusers
        info["diffusers"] = diffusers.__version__
        from diffusers import ZImagePipeline  # noqa: F401
        info["z_image_pipeline"] = "available"
    except Exception as e:
        info["z_image_pipeline"] = f"UNAVAILABLE: {repr(e)[:160]}"

    path = Path(resolve_model(model_arg))
    if path.is_dir():
        total = sum(f.stat().st_size for f in path.rglob("*")
                    if f.is_file() and ".cache" not in f.parts)
        incomplete = len(list(path.rglob("*.incomplete")))
        info["model_dir"] = str(path)
        info["model_gb"] = round(total / 1e9, 1)
        info["download_complete"] = incomplete == 0 and total > 15e9
        if incomplete:
            info["still_downloading"] = incomplete
    else:
        info["model_dir"] = f"(not local: {model_arg})"
    info["usable"] = bool(info.get("cuda") and
                          info.get("z_image_pipeline") == "available" and
                          info.get("download_complete"))
    return info


def build_pipeline(model: str, offload: bool):
    import torch
    from diffusers import ZImagePipeline

    # bf16: the laptop's Ada GPU supports it natively. (The Turing rig does not,
    # which is another reason this runs here.)
    pipe = ZImagePipeline.from_pretrained(model, dtype=torch.bfloat16)
    if offload:
        # ~20 GB of weights behind 8 GB of VRAM: components are moved to the GPU
        # only while they run. Slower per image, but it is the difference
        # between running and not running.
        pipe.enable_model_cpu_offload()
    else:
        pipe.to("cuda")
    return pipe


def generate(pipe, prompt: str, negative: str, steps: int, cfg: float,
             seed: int, width: int, height: int):
    import torch
    gen = torch.Generator("cpu").manual_seed(seed)
    t0 = time.time()
    kwargs = dict(prompt=prompt, num_inference_steps=steps,
                  guidance_scale=cfg, generator=gen,
                  width=width, height=height)
    if negative:
        kwargs["negative_prompt"] = negative
    image = pipe(**kwargs).images[0]
    return image, round(time.time() - t0, 1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe", action="store_true", help="report readiness and exit")
    ap.add_argument("--prompt")
    ap.add_argument("--negative", default="", help="negative prompt (base model only)")
    ap.add_argument("--out", default="out.png")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--steps", type=int, default=BASE_STEPS)
    ap.add_argument("--cfg", type=float, default=BASE_CFG)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--no-offload", action="store_true",
                    help="keep everything on the GPU (needs enough VRAM)")
    ap.add_argument("--compare", action="store_true",
                    help="also render the same seed at 8 steps / no CFG, to show "
                         "what distillation-style few-step sampling costs")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.probe:
        info = probe(args.model)
        if args.json:
            json.dump(info, sys.stdout, ensure_ascii=False)
            sys.stdout.write("\n")
        else:
            for k, v in info.items():
                print(f"{k:20} {v}")
        return 0 if info["usable"] else 1

    if not args.prompt:
        ap.error("--prompt is required (or use --probe)")

    model = resolve_model(args.model)
    import torch
    pipe = build_pipeline(model, offload=not args.no_offload)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    runs = [("base", args.steps, args.cfg, out)]
    if args.compare:
        runs.append(("fewstep", 8, 1.0,
                     out.with_name(f"{out.stem}_fewstep{out.suffix}")))

    results = []
    for label, steps, cfg, path in runs:
        image, secs = generate(pipe, args.prompt, args.negative, steps, cfg,
                               args.seed, args.width, args.height)
        image.save(path)
        results.append({"label": label, "steps": steps, "cfg": cfg,
                        "seconds": secs, "path": str(path.resolve()),
                        "size_kb": round(path.stat().st_size / 1024)})
        print(f"{label}: {steps} steps, cfg {cfg} -> {path} ({secs}s)",
              file=sys.stderr, flush=True)

    summary = {
        "model": model,
        "prompt": args.prompt,
        "seed": args.seed,
        "resolution": f"{args.width}x{args.height}",
        "offload": not args.no_offload,
        "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        "vram_peak_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2)
        if torch.cuda.is_available() else None,
        "runs": results,
    }
    json.dump(summary, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
