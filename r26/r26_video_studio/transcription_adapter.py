from __future__ import annotations

import importlib.util
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

from .runtime_health import runtime_health
from .transcript import normalize_segments


def transcription_status() -> dict[str, Any]:
    template = os.environ.get("BINARIO_R25_TRANSCRIBE_CMD", "").strip()
    faster = importlib.util.find_spec("faster_whisper") is not None
    health = runtime_health()
    mismatches = health.get("architecture_mismatches") or []
    local_safe = faster and not mismatches
    available = bool(template) or local_safe
    mode = "r25_external" if template else ("local_faster_whisper" if local_safe else "not_available")
    return {
        "available": available,
        "mode": mode,
        "r25_external": bool(template),
        "local_faster_whisper": local_safe,
        "env": "BINARIO_R25_TRANSCRIBE_CMD",
        "contract": "R25 command receives {input} and {output}; output must be JSON list or {segments:[...]}",
        "nonfatal": True,
        "architecture_mismatches": mismatches,
        "policy": "prefer_r25_then_safe_local_whisper_editor_never_depends_on_transcription",
    }


def _external_transcribe(path: Path, output_path: Path) -> list[dict[str, Any]]:
    template = os.environ["BINARIO_R25_TRANSCRIBE_CMD"]
    command = template.format(input=shlex.quote(str(path)), output=shlex.quote(str(output_path)))
    proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60 * 60)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "transcription failed")[-2000:])
    if not output_path.is_file():
        raise RuntimeError("transcription command did not create output JSON")
    data = json.loads(output_path.read_text(encoding="utf-8"))
    rows = data.get("segments", []) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise RuntimeError("transcription output must contain a list of segments")
    return [s.to_dict() for s in normalize_segments(rows)]


def _local_transcribe(path: Path, output_path: Path) -> list[dict[str, Any]]:
    from faster_whisper import WhisperModel  # type: ignore

    model_name = os.environ.get("BINARIO_WHISPER_MODEL", "small").strip() or "small"
    compute_type = os.environ.get("BINARIO_WHISPER_COMPUTE", "int8").strip() or "int8"
    model = WhisperModel(model_name, device="cpu", compute_type=compute_type)
    segments, info = model.transcribe(str(path), vad_filter=True, beam_size=5)
    rows: list[dict[str, Any]] = []
    for n, seg in enumerate(segments, 1):
        rows.append({"id": f"whisper_{n}", "start": float(seg.start), "end": float(seg.end), "text": str(seg.text).strip()})
    normalized = [s.to_dict() for s in normalize_segments(rows)]
    output_path.write_text(json.dumps({"segments": normalized, "language": getattr(info, "language", None), "engine": "faster_whisper"}, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def transcribe(path: Path, output_path: Path) -> list[dict[str, Any]]:
    status = transcription_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if status["r25_external"]:
        return _external_transcribe(path, output_path)
    if status["local_faster_whisper"]:
        return _local_transcribe(path, output_path)
    mismatch = status.get("architecture_mismatches") or []
    detail = f"; architecture mismatch: {mismatch}" if mismatch else ""
    raise RuntimeError("No safe transcription engine is configured. Editor and rendering remain available" + detail)
