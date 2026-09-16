#!/usr/bin/env python3
"""Speech-to-text for local audio, with the Windows/ComfyUI traps handled.

There was no ASR anywhere in this setup: ComfyUI-F5-TTS goes text -> speech, and
nothing went the other way. This fills that gap.

Two things make a naive `transformers` ASR call fail in this repo's ComfyUI venv,
and both are handled here:

1. **torchcodec cannot load its DLL.** `transformers` pulls in torchcodec for
   audio decoding, and `libtorchcodec_coreN.dll` needs the matching FFmpeg
   shared libraries. On Windows, Python 3.8+ ignores PATH for DLL resolution, so
   the DLLs have to be registered with `os.add_dll_directory()`. The repo already
   ships FFmpeg 8 at `ai_video/ffmpeg/` (avcodec-62, avutil-60, ...), which is
   what `libtorchcodec_core8.dll` wants.
2. **Whisper repeats itself on long audio.** Default decoding produces loops --
   measured on a real 97-second clip, "because then it creates a lot of space in
   our minds" came out three times in a row when the speaker said it once. The
   anti-repetition decoding parameters below fix that and are on by default;
   `--raw-decoding` turns them off if you want to compare.

Usage:
    python scripts/lib/run_asr.py --probe
    python scripts/lib/run_asr.py --input <file-or-dir> --out transcripts.json
    python scripts/lib/run_asr.py --input audio/ --out out.json --language hu
    python scripts/lib/run_asr.py --input audio/ --out out.json --srt-dir subs/

Measured on an RTX 4070 Laptop (8 GB): 22.5 minutes of audio in 60 seconds
(22.5x realtime), 1.85 GB VRAM peak, with whisper-large-v3-turbo.

KILL SWITCH: delete this file. It writes only where --out / --srt-dir point.
"""

import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path

AUDIO_EXTS = (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".aac")
DEFAULT_MODEL = "openai/whisper-large-v3-turbo"

# Whisper's standard anti-hallucination / anti-repetition settings. Without
# these, long-form audio loops phrases the speaker said once.
ANTI_REPEAT = {
    "no_repeat_ngram_size": 4,
    "condition_on_prev_tokens": False,
    "compression_ratio_threshold": 1.35,
    "logprob_threshold": -1.0,
    "no_speech_threshold": 0.6,
    "temperature": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
}


def register_ffmpeg_dlls(repo_root: Path) -> str:
    """Make torchcodec able to find FFmpeg. Returns the directory used, or ''."""
    for cand in (repo_root / "ai_video" / "ffmpeg", repo_root / "ffmpeg"):
        if cand.is_dir() and any(cand.glob("avcodec-*.dll")):
            try:
                os.add_dll_directory(str(cand))
                return str(cand)
            except (OSError, AttributeError):
                # add_dll_directory is Windows-only; elsewhere the system loader
                # already handles this.
                return ""
    return ""


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def load_audio(path: str):
    """Decode to a mono 16 kHz float32 array, which is what Whisper expects."""
    import soundfile as sf
    import librosa

    audio, sr = sf.read(path, dtype="float32")
    if getattr(audio, "ndim", 1) > 1:
        audio = audio.mean(axis=1)
    if sr != 16000:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
        sr = 16000
    return audio, sr


def collect_inputs(target: str) -> list[str]:
    p = Path(target)
    if p.is_file():
        return [str(p)]
    if p.is_dir():
        found: list[str] = []
        for ext in AUDIO_EXTS:
            found += glob.glob(str(p / f"*{ext}"))
        return sorted(found)
    return []


def to_srt(chunks: list[dict]) -> str:
    def stamp(seconds: float) -> str:
        if seconds is None:
            seconds = 0.0
        ms = int(round(seconds * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    out = []
    for i, c in enumerate(chunks, 1):
        ts = c.get("timestamp") or (None, None)
        text = (c.get("text") or "").strip()
        if not text:
            continue
        out.append(f"{i}\n{stamp(ts[0])} --> {stamp(ts[1])}\n{text}\n")
    return "\n".join(out)


def probe() -> dict:
    info: dict = {"ffmpeg_dll_dir": register_ffmpeg_dlls(repo_root()) or None}
    try:
        import torch
        info["torch"] = torch.__version__
        info["cuda"] = torch.cuda.is_available()
        info["device"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
    except Exception as e:
        info["torch_error"] = repr(e)[:200]
    for mod in ("transformers", "soundfile", "librosa"):
        try:
            info[mod] = __import__(mod).__version__
        except Exception:
            info[mod] = None
    try:
        import torchcodec  # noqa: F401
        info["torchcodec"] = "loads"
    except Exception as e:
        info["torchcodec"] = f"FAILS: {repr(e)[:120]}"
    info["usable"] = bool(info.get("transformers") and info.get("soundfile"))
    return info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe", action="store_true", help="report environment readiness and exit")
    ap.add_argument("--input", help="audio file or directory")
    ap.add_argument("--out", help="write JSON results here")
    ap.add_argument("--srt-dir", help="also write one .srt per input file here")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--language", help="force a language (e.g. hu, en); default: auto-detect")
    ap.add_argument("--raw-decoding", action="store_true",
                    help="disable the anti-repetition settings (for comparison)")
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = ap.parse_args()

    if args.probe:
        info = probe()
        if args.json:
            json.dump(info, sys.stdout, ensure_ascii=False)
            sys.stdout.write("\n")
        else:
            for k, v in info.items():
                print(f"{k:16} {v}")
        return 0 if info["usable"] else 1

    if not args.input:
        ap.error("--input is required (or use --probe)")
    files = collect_inputs(args.input)
    if not files:
        print(f"run_asr: no audio found at {args.input}", file=sys.stderr)
        return 1

    dll_dir = register_ffmpeg_dlls(repo_root())
    import torch
    from transformers import pipeline

    device = 0 if torch.cuda.is_available() else -1
    gen_kwargs = {} if args.raw_decoding else dict(ANTI_REPEAT)
    if args.language:
        gen_kwargs["language"] = args.language

    asr = pipeline("automatic-speech-recognition", model=args.model,
                   dtype=torch.float16 if device == 0 else torch.float32,
                   device=device)

    results, t0 = [], time.time()
    for i, path in enumerate(files, 1):
        name = os.path.basename(path)
        try:
            audio, sr = load_audio(path)
            t1 = time.time()
            r = asr({"array": audio, "sampling_rate": sr},
                    return_timestamps=True, generate_kwargs=gen_kwargs)
            chunks = [{"timestamp": c.get("timestamp"), "text": (c.get("text") or "").strip()}
                      for c in (r.get("chunks") or [])]
            results.append({"file": name, "audio_seconds": round(len(audio) / sr, 1),
                            "seconds": round(time.time() - t1, 1),
                            "text": r["text"].strip(), "chunks": chunks})
            if args.srt_dir and chunks:
                Path(args.srt_dir).mkdir(parents=True, exist_ok=True)
                (Path(args.srt_dir) / f"{Path(name).stem}.srt").write_text(
                    to_srt(chunks), encoding="utf-8")
            print(f"[{i}/{len(files)}] {name} {results[-1]['audio_seconds']}s "
                  f"-> {results[-1]['seconds']}s", file=sys.stderr, flush=True)
        except Exception as e:
            results.append({"file": name, "error": repr(e)[:300]})
            print(f"[{i}/{len(files)}] {name} FAILED: {repr(e)[:160]}",
                  file=sys.stderr, flush=True)

    total_audio = sum(r.get("audio_seconds", 0) for r in results)
    wall = time.time() - t0
    summary = {
        "files": len(files),
        "failed": sum(1 for r in results if "error" in r),
        "device": torch.cuda.get_device_name(0) if device == 0 else "cpu",
        "model": args.model,
        "anti_repetition": not args.raw_decoding,
        "ffmpeg_dll_dir": dll_dir or None,
        "audio_seconds_total": round(total_audio, 1),
        "wall_seconds": round(wall, 1),
        "realtime_factor": round(total_audio / max(wall, 1e-9), 1),
        "vram_peak_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2) if device == 0 else None,
        "results": results,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(summary, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
    json.dump({k: v for k, v in summary.items() if k != "results"},
              sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
