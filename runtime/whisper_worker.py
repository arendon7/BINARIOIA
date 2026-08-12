#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

DEFAULT_MODEL = "small"
DEFAULT_MODELS_ROOT = Path.home() / "Library" / "Application Support" / "Binario IA" / "models" / "whisper"


def models_root() -> Path:
    return Path(os.environ.get("BINARIO_WHISPER_MODELS", str(DEFAULT_MODELS_ROOT))).expanduser().resolve()


def _package_version(name: str) -> str | None:
    try:
        import importlib.metadata
        return importlib.metadata.version(name)
    except Exception:
        return None


def probe(model_name: str = DEFAULT_MODEL) -> dict:
    result = {
        "ok": False,
        "python": sys.executable,
        "python_version": sys.version.split()[0],
        "machine": platform.machine(),
        "packages": {},
        "models_root": str(models_root()),
    }
    try:
        import av  # noqa: F401
        import ctranslate2  # noqa: F401
        import faster_whisper  # noqa: F401
        result["packages"] = {
            "faster-whisper": _package_version("faster-whisper"),
            "av": _package_version("av"),
            "ctranslate2": _package_version("ctranslate2"),
        }
        source = _model_source(model_name)
        result["model"] = model_name
        result["model_source"] = source
        result["model_cached"] = source != model_name
        result["ok"] = True
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _model_source(model_name: str) -> str:
    root = models_root()
    deterministic = root / model_name
    if deterministic.is_dir() and (deterministic / "model.bin").is_file():
        return str(deterministic)
    safe = model_name.replace("/", "--")
    for prefix in ("Systran", "systran"):
        legacy = root / f"models--{prefix}--faster-whisper-{safe}"
        if legacy.is_dir() and (legacy / "model.bin").is_file():
            return str(legacy)
        for snapshot in legacy.glob("snapshots/*") if legacy.exists() else ():
            if snapshot.is_dir() and (snapshot / "model.bin").is_file():
                return str(snapshot)
    return model_name


def _load_model(model_name: str):
    from faster_whisper import WhisperModel

    root = models_root()
    root.mkdir(parents=True, exist_ok=True)
    compute_type = os.environ.get("BINARIO_WHISPER_COMPUTE", "int8").strip() or "int8"
    device = os.environ.get("BINARIO_WHISPER_DEVICE", "cpu").strip() or "cpu"
    source = _model_source(model_name)
    kwargs = {"device": device, "compute_type": compute_type}
    if source == model_name:
        kwargs["download_root"] = str(root)
    return WhisperModel(source, **kwargs)


def prepare(model_name: str) -> dict:
    started = time.time()
    status = probe(model_name)
    if not status.get("ok"):
        return status
    try:
        _load_model(model_name)
        return {
            **status,
            "ok": True,
            "model": model_name,
            "prepared": True,
            "elapsed_seconds": round(time.time() - started, 3),
        }
    except Exception as exc:
        return {
            **status,
            "ok": False,
            "model": model_name,
            "prepared": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def transcribe(input_path: Path, output_path: Path, model_name: str, language: str | None = None) -> dict:
    started = time.time()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    model = _load_model(model_name)
    kwargs = {"vad_filter": True, "beam_size": 5}
    if language:
        kwargs["language"] = language
    segments, info = model.transcribe(str(input_path), **kwargs)
    rows = []
    for n, seg in enumerate(segments, 1):
        text = str(getattr(seg, "text", "") or "").strip()
        if not text:
            continue
        rows.append({
            "id": f"whisper_{n}",
            "start": round(float(seg.start), 3),
            "end": round(float(seg.end), 3),
            "text": text,
        })
    payload = {
        "ok": True,
        "segments": rows,
        "language": getattr(info, "language", language),
        "language_probability": getattr(info, "language_probability", None),
        "engine": "faster_whisper_runtime_worker",
        "model": model_name,
        "python": sys.executable,
        "machine": platform.machine(),
        "elapsed_seconds": round(time.time() - started, 3),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["probe", "prepare", "transcribe"])
    ap.add_argument("--model", default=os.environ.get("BINARIO_WHISPER_MODEL", DEFAULT_MODEL))
    ap.add_argument("--input")
    ap.add_argument("--output")
    ap.add_argument("--language")
    args = ap.parse_args()
    try:
        if args.action == "probe":
            result = probe(args.model)
        elif args.action == "prepare":
            result = prepare(args.model)
        else:
            if not args.input or not args.output:
                raise ValueError("--input y --output son requeridos para transcribe")
            result = transcribe(Path(args.input).expanduser().resolve(), Path(args.output).expanduser().resolve(), args.model, args.language)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("ok") else 2
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}", "python": sys.executable, "machine": platform.machine()}, ensure_ascii=False))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
