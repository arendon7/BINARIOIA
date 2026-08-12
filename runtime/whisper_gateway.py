from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).resolve().with_name("whisper_worker.py")
PACKAGE_SPEC = ["faster-whisper>=1.2.1,<2", "av>=11,<19", "ctranslate2>=4,<5", "tokenizers>=0.13,<1"]


def _normalize_arch(value: str | None) -> str:
    v = (value or "").lower().strip()
    if v in {"aarch64", "arm64", "arm64e"}:
        return "arm64"
    if v in {"amd64", "x86_64", "x64"}:
        return "x86_64"
    return v or "unknown"


def hardware_architecture() -> str:
    if sys.platform == "darwin":
        try:
            cp = subprocess.run(["/usr/sbin/sysctl", "-in", "hw.optional.arm64"], capture_output=True, text=True, timeout=3, check=False)
            if cp.returncode == 0 and cp.stdout.strip() == "1":
                return "arm64"
        except Exception:
            pass
    return _normalize_arch(platform.machine())


def _active_runtime_python() -> str | None:
    active = Path.home() / "Library" / "Application Support" / "Binario IA" / "runtime" / "active.json"
    try:
        data = json.loads(active.read_text(encoding="utf-8"))
        root = Path(str(data.get("runtime_root") or "")).expanduser()
        for p in (root / ".venv" / "bin" / "python3", root / ".venv" / "bin" / "python"):
            if p.is_file() and os.access(p, os.X_OK):
                return str(p)
    except Exception:
        pass
    try:
        from runtime.runtime_manager import python_path
        candidate = Path(python_path())
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    except Exception:
        pass
    return None


def runtime_python() -> str:
    return os.environ.get("BINARIO_WHISPER_PYTHON", "").strip() or _active_runtime_python() or sys.executable


def _run_worker(action: str, *, model: str = "small", input_path: Path | None = None, output_path: Path | None = None, language: str | None = None, timeout: int = 3600) -> dict[str, Any]:
    py = runtime_python()
    cmd = [py, str(WORKER), action, "--model", model]
    if input_path is not None:
        cmd += ["--input", str(input_path)]
    if output_path is not None:
        cmd += ["--output", str(output_path)]
    if language:
        cmd += ["--language", language]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False, env=env)
    lines = [x.strip() for x in (proc.stdout or "").splitlines() if x.strip()]
    payload: dict[str, Any]
    try:
        payload = json.loads(lines[-1]) if lines else {}
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload.setdefault("python", py)
    payload["returncode"] = proc.returncode
    if proc.returncode != 0 and not payload.get("error"):
        payload["error"] = (proc.stderr or proc.stdout or "Whisper worker failed")[-2400:]
    return payload


def status(model: str = "small") -> dict[str, Any]:
    py = runtime_python()
    result = _run_worker("probe", model=model, timeout=45)
    worker_arch = _normalize_arch(str(result.get("machine") or ""))
    hardware = hardware_architecture()
    arch_ok = not (sys.platform == "darwin" and hardware in {"arm64", "x86_64"} and worker_arch not in {hardware, "unknown"})
    ready = bool(result.get("ok") and arch_ok)
    return {
        "available": ready,
        "ready": ready,
        "mode": "isolated_runtime_worker" if ready else "needs_repair",
        "runtime_python": py,
        "runtime_machine": worker_arch,
        "hardware_arch": hardware,
        "architecture_ok": arch_ok,
        "model": model,
        "packages": result.get("packages") or {},
        "error": result.get("error"),
        "repair_supported": True,
        "prepare_supported": True,
        "nonfatal": True,
        "policy": "single_native_runtime_worker_no_optional_binary_import_in_ui_process",
    }


def repair(model: str = "small") -> dict[str, Any]:
    py = runtime_python()
    env = os.environ.copy()
    env["PIP_NO_CACHE_DIR"] = "1"
    install = subprocess.run([py, "-m", "pip", "install", "--upgrade", "--force-reinstall", "--no-cache-dir", *PACKAGE_SPEC], capture_output=True, text=True, timeout=2400, check=False, env=env)
    if install.returncode != 0:
        return {"ok": False, "stage": "pip", "python": py, "error": (install.stderr or install.stdout or "pip failed")[-3000:]}
    prepared = _run_worker("prepare", model=model, timeout=3600)
    if not prepared.get("ok"):
        return {"ok": False, "stage": "prepare", **prepared}
    return {"ok": True, "stage": "ready", "python": py, "prepare": prepared, "status": status(model)}


def prepare(model: str = "small") -> dict[str, Any]:
    current = status(model)
    if not current.get("ready"):
        return repair(model)
    result = _run_worker("prepare", model=model, timeout=3600)
    return {"ok": bool(result.get("ok")), "prepare": result, "status": status(model)}


def transcribe(input_path: Path, output_path: Path, *, model: str = "small", language: str | None = None) -> list[dict[str, Any]]:
    input_path = Path(input_path).expanduser().resolve()
    output_path = Path(output_path).expanduser().resolve()
    current = status(model)
    if not current.get("ready"):
        fixed = repair(model)
        if not fixed.get("ok"):
            raise RuntimeError("Whisper runtime no está listo: " + str(fixed.get("error") or fixed))
    result = _run_worker("transcribe", model=model, input_path=input_path, output_path=output_path, language=language, timeout=7200)
    if not result.get("ok"):
        raise RuntimeError(str(result.get("error") or "Whisper transcription failed"))
    rows = result.get("segments") or []
    if not isinstance(rows, list):
        raise RuntimeError("Whisper devolvió un formato de segmentos inválido")
    return rows
