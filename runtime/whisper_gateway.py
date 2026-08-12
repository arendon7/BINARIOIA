from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).resolve().with_name("whisper_worker.py")
PACKAGE_SPEC = ["faster-whisper>=1.2.1,<2", "av>=11,<19", "ctranslate2>=4,<5", "tokenizers>=0.13,<1"]
APP_SUPPORT = Path.home() / "Library" / "Application Support" / "Binario IA"


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


def _executable(path: Path | str | None) -> str | None:
    if not path:
        return None
    p = Path(str(path)).expanduser()
    return str(p) if p.is_file() and os.access(p, os.X_OK) else None


def _python_arch(py: str) -> str:
    try:
        cp = subprocess.run([py, "-c", "import platform; print(platform.machine())"], capture_output=True, text=True, timeout=8, check=False)
        if cp.returncode == 0:
            return _normalize_arch(cp.stdout.strip().splitlines()[-1])
    except Exception:
        pass
    return "unknown"


def _active_runtime_python() -> str | None:
    active = APP_SUPPORT / "runtime" / "active.json"
    try:
        data = json.loads(active.read_text(encoding="utf-8"))
        root = Path(str(data.get("runtime_root") or "")).expanduser()
        for p in (root / ".venv" / "bin" / "python3", root / ".venv" / "bin" / "python"):
            candidate = _executable(p)
            if candidate:
                return candidate
    except Exception:
        pass
    return None


def _dedicated_runtime_root() -> Path:
    arch = hardware_architecture()
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    return APP_SUPPORT / "runtime" / "whisper" / f"macos-{arch}-py{version}"


def _dedicated_runtime_python() -> str | None:
    root = _dedicated_runtime_root()
    for p in (root / ".venv" / "bin" / "python3", root / ".venv" / "bin" / "python"):
        candidate = _executable(p)
        if candidate:
            return candidate
    return None


def runtime_python() -> str | None:
    explicit = _executable(os.environ.get("BINARIO_WHISPER_PYTHON", "").strip())
    if explicit:
        return explicit
    candidate = _active_runtime_python() or _dedicated_runtime_python()
    if candidate:
        return candidate
    if sys.platform != "darwin":
        return sys.executable
    return None


def _bootstrap_python_candidate() -> str | None:
    expected = hardware_architecture()
    paths = [sys.executable, "/opt/homebrew/bin/python3.12", "/opt/homebrew/bin/python3", "/usr/local/bin/python3.12", "/usr/local/bin/python3", "/usr/bin/python3"]
    seen: set[str] = set()
    for raw in paths:
        py = _executable(raw)
        if not py or py in seen:
            continue
        seen.add(py)
        arch = _python_arch(py)
        if expected in {"arm64", "x86_64"} and arch != expected:
            continue
        return py
    return None


def bootstrap_dedicated_runtime() -> dict[str, Any]:
    existing = _dedicated_runtime_python()
    if existing:
        return {"ok": True, "created": False, "python": existing, "runtime_root": str(_dedicated_runtime_root()), "architecture": _python_arch(existing)}
    base = _bootstrap_python_candidate()
    if not base:
        return {"ok": False, "stage": "runtime_missing", "error": "No hay un Python nativo compatible para crear el runtime aislado de Whisper."}
    root = _dedicated_runtime_root(); root.mkdir(parents=True, exist_ok=True)
    create = subprocess.run([base, "-m", "venv", str(root / ".venv")], capture_output=True, text=True, timeout=300, check=False)
    if create.returncode != 0:
        return {"ok": False, "stage": "venv", "python": base, "error": (create.stderr or create.stdout or "No se pudo crear el runtime Whisper")[-3000:]}
    py = _dedicated_runtime_python()
    if not py:
        return {"ok": False, "stage": "venv", "python": base, "error": "El entorno se creó pero no contiene un Python ejecutable."}
    meta = {"schema": "sbia-whisper-runtime-1.0", "python": py, "base_python": base, "hardware_arch": hardware_architecture(), "python_arch": _python_arch(py), "isolated": True}
    (root / "runtime.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "created": True, "python": py, "runtime_root": str(root), "architecture": meta["python_arch"]}


def _run_worker(action: str, *, model: str = "small", input_path: Path | None = None, output_path: Path | None = None, language: str | None = None, timeout: int = 3600) -> dict[str, Any]:
    py = runtime_python()
    if not py:
        return {"ok": False, "returncode": 127, "runtime_missing": True, "error": "No hay runtime persistente de Whisper. Usa Preparar / reparar Whisper."}
    cmd = [py, str(WORKER), action, "--model", model]
    if input_path is not None:
        cmd += ["--input", str(input_path)]
    if output_path is not None:
        cmd += ["--output", str(output_path)]
    if language:
        cmd += ["--language", language]
    env = os.environ.copy(); env["PYTHONPATH"] = str(ROOT) + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False, env=env)
    lines = [x.strip() for x in (proc.stdout or "").splitlines() if x.strip()]
    try:
        payload: dict[str, Any] = json.loads(lines[-1]) if lines else {}
    except Exception:
        payload = {}
    if not isinstance(payload, dict): payload = {}
    payload.setdefault("python", py); payload["returncode"] = proc.returncode
    if proc.returncode != 0 and not payload.get("error"):
        payload["error"] = (proc.stderr or proc.stdout or "Whisper worker failed")[-2400:]
    return payload


def status(model: str = "small") -> dict[str, Any]:
    py = runtime_python(); hardware = hardware_architecture()
    if not py:
        return {"available": False, "runtime_ok": False, "model_cached": False, "ready": False, "mode": "runtime_missing", "runtime_python": None, "runtime_machine": None, "hardware_arch": hardware, "architecture_ok": False, "model": model, "packages": {}, "error": "No hay runtime persistente de Whisper.", "repair_supported": True, "prepare_supported": True, "bootstrap_supported": True, "nonfatal": True, "policy": "single_native_runtime_worker_no_optional_binary_import_in_ui_process", "runtime_policy": "persistent_or_dedicated_native_runtime_only_never_ui_python_on_macos"}
    result = _run_worker("probe", model=model, timeout=45)
    worker_arch = _normalize_arch(str(result.get("machine") or _python_arch(py)))
    arch_ok = not (sys.platform == "darwin" and hardware in {"arm64", "x86_64"} and worker_arch not in {hardware, "unknown"})
    runtime_ok = bool(result.get("ok") and arch_ok); model_cached = bool(result.get("model_cached")); ready = bool(runtime_ok and model_cached)
    return {"available": runtime_ok, "runtime_ok": runtime_ok, "model_cached": model_cached, "ready": ready, "mode": "isolated_runtime_worker" if ready else ("needs_model_prepare" if runtime_ok else "needs_repair"), "runtime_python": py, "runtime_machine": worker_arch, "hardware_arch": hardware, "architecture_ok": arch_ok, "model": model, "packages": result.get("packages") or {}, "error": result.get("error"), "repair_supported": True, "prepare_supported": True, "bootstrap_supported": True, "nonfatal": True, "policy": "single_native_runtime_worker_no_optional_binary_import_in_ui_process", "runtime_policy": "persistent_or_dedicated_native_runtime_only_never_ui_python_on_macos"}


def repair(model: str = "small") -> dict[str, Any]:
    py = runtime_python(); bootstrap = None
    if not py:
        bootstrap = bootstrap_dedicated_runtime()
        if not bootstrap.get("ok"):
            return {"ok": False, "stage": bootstrap.get("stage") or "runtime_missing", "error": bootstrap.get("error"), "bootstrap": bootstrap}
        py = str(bootstrap["python"])
    env = os.environ.copy(); env["PIP_NO_CACHE_DIR"] = "1"
    install = subprocess.run([py, "-m", "pip", "install", "--upgrade", "--force-reinstall", "--no-cache-dir", *PACKAGE_SPEC], capture_output=True, text=True, timeout=2400, check=False, env=env)
    if install.returncode != 0:
        return {"ok": False, "stage": "pip", "python": py, "bootstrap": bootstrap, "error": (install.stderr or install.stdout or "pip failed")[-3000:]}
    prepared = _run_worker("prepare", model=model, timeout=3600)
    if not prepared.get("ok"):
        return {"ok": False, "stage": "prepare", "bootstrap": bootstrap, **prepared}
    return {"ok": True, "stage": "ready", "python": py, "bootstrap": bootstrap, "prepare": prepared, "status": status(model)}


def prepare(model: str = "small") -> dict[str, Any]:
    current = status(model)
    if not current.get("runtime_ok"):
        return repair(model)
    if current.get("model_cached"):
        return {"ok": True, "stage": "ready", "prepare": {"ok": True, "model": model, "prepared": True, "cached": True}, "status": current}
    result = _run_worker("prepare", model=model, timeout=3600)
    return {"ok": bool(result.get("ok")), "stage": "prepare", "prepare": result, "status": status(model)}


def transcribe(input_path: Path, output_path: Path, *, model: str = "small", language: str | None = None) -> list[dict[str, Any]]:
    input_path = Path(input_path).expanduser().resolve(); output_path = Path(output_path).expanduser().resolve(); current = status(model)
    if not current.get("runtime_ok"):
        fixed = repair(model)
        if not fixed.get("ok"): raise RuntimeError("Whisper runtime no está listo: " + str(fixed.get("error") or fixed))
    elif not current.get("model_cached"):
        prepared = prepare(model)
        if not prepared.get("ok"): raise RuntimeError("Whisper no pudo preparar el modelo: " + str(prepared.get("error") or prepared))
    result = _run_worker("transcribe", model=model, input_path=input_path, output_path=output_path, language=language, timeout=7200)
    if not result.get("ok"): raise RuntimeError(str(result.get("error") or "Whisper transcription failed"))
    rows = result.get("segments") or []
    if not isinstance(rows, list): raise RuntimeError("Whisper devolvió un formato de segmentos inválido")
    return rows


def self_test(model: str = "small") -> dict[str, Any]:
    if sys.platform != "darwin":
        return {"ok": False, "stage": "unsupported", "error": "La auto-prueba de voz usa la voz del sistema de macOS y solo se ejecuta en Mac."}
    prepared = prepare(model)
    if not prepared.get("ok"):
        return {"ok": False, "stage": "prepare", "error": prepared.get("error") or "Whisper no quedó listo", "prepare": prepared}
    with tempfile.TemporaryDirectory(prefix="binario-whisper-selftest-") as td:
        audio = Path(td) / "whisper-self-test.aiff"; output = Path(td) / "transcript.json"
        say = subprocess.run(["/usr/bin/say", "-o", str(audio), "Prueba de transcripción de Binario IA"], capture_output=True, text=True, timeout=30, check=False)
        if say.returncode != 0 or not audio.is_file():
            return {"ok": False, "stage": "audio", "error": (say.stderr or say.stdout or "macOS say no generó audio")[-1200:]}
        try:
            segments = transcribe(audio, output, model=model, language="es")
        except Exception as exc:
            return {"ok": False, "stage": "transcribe", "error": f"{type(exc).__name__}: {exc}"}
        transcript = " ".join(str(x.get("text") or "").strip() for x in segments).strip()
        return {"ok": bool(transcript), "stage": "ready" if transcript else "empty", "transcript": transcript, "segments": len(segments), "model": model, "runtime": status(model)}
