from __future__ import annotations

import importlib.util
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _file_arch(path: Path) -> str | None:
    tool = shutil.which("file")
    if not tool or not path.exists():
        return None
    try:
        proc = subprocess.run([tool, str(path)], capture_output=True, text=True, timeout=3, check=False)
        return (proc.stdout or proc.stderr).strip()[:500]
    except Exception:
        return None


def module_binary_evidence(module_name: str) -> dict[str, Any]:
    spec = importlib.util.find_spec(module_name)
    if not spec:
        return {"installed": False}
    origin = Path(spec.origin).resolve() if spec.origin and spec.origin not in {"built-in", "frozen"} else None
    evidence = {"installed": True, "origin": str(origin) if origin else spec.origin}
    if origin and origin.suffix in {".so", ".dylib"}:
        evidence["binary"] = _file_arch(origin)
    elif origin and origin.name == "__init__.py":
        candidates = list(origin.parent.glob("*.so")) + list(origin.parent.rglob("*.so"))[:8]
        binaries = []
        for p in candidates[:8]:
            binaries.append({"path": str(p), "file": _file_arch(p)})
        if binaries:
            evidence["binaries"] = binaries
    return evidence


def runtime_health() -> dict[str, Any]:
    machine = platform.machine().lower()
    modules = {name: module_binary_evidence(name) for name in ("av", "ctranslate2", "onnxruntime", "faster_whisper")}
    incompatible = []
    expected = "arm64" if machine in {"arm64", "arm64e", "aarch64"} else machine
    for name, info in modules.items():
        texts = []
        if info.get("binary"):
            texts.append(str(info["binary"]))
        for row in info.get("binaries", []):
            texts.append(str(row.get("file") or ""))
        joined = " ".join(texts).lower()
        if expected == "arm64" and joined and "x86_64" in joined and "arm64" not in joined:
            incompatible.append({"module": name, "reason": "x86_64_binary_on_arm64_runtime"})
    try:
        from runtime.whisper_gateway import status as whisper_gateway_status
        whisper = whisper_gateway_status()
    except Exception as exc:
        whisper = {"ready": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "python": sys.version.split()[0],
        "machine": machine,
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "modules": modules,
        "architecture_mismatches": incompatible,
        "whisper_runtime": whisper,
        "healthy": bool(shutil.which("ffmpeg")),
        "transcription_healthy": bool(whisper.get("ready")),
        "policy": "diagnostic_only_no_import_of_optional_video_stack",
        "whisper_policy": "ui_process_optional_binary_diagnostics_plus_isolated_whisper_runtime",
    }


def main() -> int:
    print(json.dumps(runtime_health(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
