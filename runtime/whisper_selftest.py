from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from runtime.whisper_gateway import status as whisper_status
from runtime.whisper_gateway import transcribe

PHRASE = "Binario prueba de transcripción local"


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(text or "").lower()))


def supported() -> dict[str, Any]:
    say = shutil.which("say") if platform.system().lower() == "darwin" else None
    return {
        "supported": bool(say),
        "platform": platform.system().lower(),
        "say": say,
        "policy": "macos_say_to_whisper_end_to_end_no_ui_dependency",
    }


def run(model: str = "small", language: str = "es") -> dict[str, Any]:
    capability = supported()
    if not capability["supported"]:
        return {"ok": False, "stage": "unsupported", **capability, "error": "La auto-prueba de voz requiere macOS y el comando say."}

    before = whisper_status(model)
    if not before.get("ready"):
        return {
            "ok": False,
            "stage": "not_ready",
            "status": before,
            **capability,
            "error": "Whisper todavía no está listo; prepara/repara el runtime antes de ejecutar la auto-prueba.",
        }

    with tempfile.TemporaryDirectory(prefix="binario-whisper-selftest-") as td:
        root = Path(td)
        audio = root / "voice.aiff"
        output = root / "transcript.json"
        proc = subprocess.run(
            [str(capability["say"]), "-o", str(audio), PHRASE],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.returncode != 0 or not audio.is_file() or audio.stat().st_size <= 0:
            return {
                "ok": False,
                "stage": "say",
                **capability,
                "error": (proc.stderr or proc.stdout or "macOS say no generó audio")[-1200:],
            }

        try:
            rows = transcribe(audio, output, model=model, language=language)
        except Exception as exc:
            return {
                "ok": False,
                "stage": "transcribe",
                **capability,
                "status": whisper_status(model),
                "error": f"{type(exc).__name__}: {exc}",
            }

        transcript = " ".join(str(row.get("text") or "").strip() for row in rows if isinstance(row, dict)).strip()
        got = set(_norm(transcript).split())
        expected = set(_norm(PHRASE).split())
        overlap = len(got & expected) / max(1, len(expected))
        ok = bool(transcript) and overlap >= 0.4
        result = {
            "ok": ok,
            "stage": "ready" if ok else "mismatch",
            "phrase": PHRASE,
            "transcript": transcript,
            "overlap": round(overlap, 3),
            "segments": len(rows),
            "model": model,
            "language": language,
            "status": whisper_status(model),
            **capability,
        }
        if not ok:
            result["error"] = "Whisper respondió, pero la transcripción de prueba no fue suficientemente reconocible."
        return result


def main() -> int:
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
