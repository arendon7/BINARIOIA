#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.whisper_gateway import status
from runtime.whisper_selftest import run as self_test


def doctor(model: str = "small", run_test: bool = False) -> dict:
    current = status(model)
    result = {
        "schema": "binario-whisper-doctor/v1",
        "platform": platform.system().lower(),
        "hardware_arch": current.get("hardware_arch"),
        "runtime_machine": current.get("runtime_machine"),
        "architecture_ok": current.get("architecture_ok"),
        "runtime_python": current.get("runtime_python"),
        "runtime_ok": current.get("runtime_ok"),
        "model": current.get("model"),
        "model_cached": current.get("model_cached"),
        "ready": current.get("ready"),
        "mode": current.get("mode"),
        "packages": current.get("packages") or {},
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "say": shutil.which("say") if platform.system().lower() == "darwin" else None,
        "error": current.get("error"),
        "self_test": None,
    }
    if run_test:
        result["self_test"] = self_test(model=model)
    blockers = []
    if not result["architecture_ok"]:
        blockers.append("runtime_architecture_mismatch")
    if not result["runtime_ok"]:
        blockers.append("runtime_not_ready")
    elif not result["model_cached"]:
        blockers.append("model_not_prepared")
    if run_test and not (result.get("self_test") or {}).get("ok"):
        blockers.append("self_test_failed")
    result["blockers"] = blockers
    result["ok"] = not blockers
    result["recommendation"] = (
        "Whisper listo para transcribir."
        if result["ok"]
        else "Usa Preparar/Reparar Whisper desde Inicio; no reinstales todo Binario IA salvo que el runtime siga fallando."
    )
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Diagnóstico reproducible de Whisper para Binario IA")
    ap.add_argument("--model", default="small")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    result = doctor(args.model, args.self_test)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
