from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.whisper_gateway import prepare as prepare_runtime_whisper
from runtime.whisper_gateway import repair as repair_runtime_whisper
from runtime.whisper_gateway import status as runtime_whisper_status
from runtime.whisper_gateway import transcribe as runtime_transcribe
from .transcript import normalize_segments


def transcription_status() -> dict[str, Any]:
    template = os.environ.get("BINARIO_R25_TRANSCRIBE_CMD", "").strip()
    runtime = runtime_whisper_status(os.environ.get("BINARIO_WHISPER_MODEL", "small").strip() or "small")
    if template:
        return {
            "available": True,
            "ready": True,
            "mode": "explicit_external_override",
            "r25_external": True,
            "runtime": runtime,
            "env": "BINARIO_R25_TRANSCRIBE_CMD",
            "contract": "Command receives {input} and {output}; output must be JSON list or {segments:[...]}",
            "repair_supported": True,
            "nonfatal": True,
            "policy": "editor_never_depends_on_transcription; explicit_external_override_then_isolated_native_runtime",
        }
    return {
        **runtime,
        "r25_external": False,
        "runtime": runtime,
        "env": "BINARIO_R25_TRANSCRIBE_CMD",
        "contract": "Whisper runs in the architecture-certified persistent runtime, isolated from the Video Studio UI process.",
        "nonfatal": True,
        "policy": "editor_never_depends_on_transcription; single_native_runtime_worker_no_optional_binary_import_in_ui_process",
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


def prepare() -> dict[str, Any]:
    return prepare_runtime_whisper(os.environ.get("BINARIO_WHISPER_MODEL", "small").strip() or "small")


def repair() -> dict[str, Any]:
    return repair_runtime_whisper(os.environ.get("BINARIO_WHISPER_MODEL", "small").strip() or "small")


def transcribe(path: Path, output_path: Path, language: str | None = None) -> list[dict[str, Any]]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if os.environ.get("BINARIO_R25_TRANSCRIBE_CMD", "").strip():
        return _external_transcribe(path, output_path)
    rows = runtime_transcribe(
        path,
        output_path,
        model=os.environ.get("BINARIO_WHISPER_MODEL", "small").strip() or "small",
        language=language,
    )
    return [s.to_dict() for s in normalize_segments(rows)]
