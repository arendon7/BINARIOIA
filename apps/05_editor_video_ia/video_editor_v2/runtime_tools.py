from __future__ import annotations
from pathlib import Path
import os, shutil, subprocess

HOME=Path.home()
RUNTIME_ROOT=Path(os.environ.get(
    "BINARIO_RUNTIME_ROOT",
    str(HOME / "Library" / "Application Support" / "Binario IA" / "runtime" / "v1")
)).expanduser()

class RuntimeToolError(RuntimeError):
    pass


def _candidate_real(path: str | Path | None) -> str | None:
    if not path:
        return None
    try:
        p=Path(path).expanduser()
        real=p.resolve(strict=True)
        if not real.is_file() or not os.access(real, os.X_OK):
            return None
        return str(real)
    except (OSError, RuntimeError, ValueError):
        return None


def _probe(path: str | Path | None, args=("-version",), timeout: float=8.0) -> str | None:
    real=_candidate_real(path)
    if not real:
        return None
    try:
        cp=subprocess.run([real,*args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout,check=False)
        if cp.returncode==0:
            return real
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _safe_which(name: str) -> str | None:
    try:
        return shutil.which(name)
    except OSError:
        return None


def resolve_ffmpeg(*, required: bool=True) -> str | None:
    candidates=[
        os.environ.get("BINARIO_FFMPEG"),
        RUNTIME_ROOT/"bin"/"ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/usr/bin/ffmpeg",
        _safe_which("ffmpeg"),
    ]
    try:
        import imageio_ffmpeg
        candidates.append(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        pass
    seen=set()
    for candidate in candidates:
        if not candidate:
            continue
        key=str(candidate)
        if key in seen:
            continue
        seen.add(key)
        healthy=_probe(candidate)
        if healthy:
            return healthy
    if required:
        raise RuntimeToolError(
            "FFmpeg no está disponible o su enlace está dañado. "
            "Abre Runtime Center → Instalar / reparar esenciales y vuelve a intentar."
        )
    return None


def resolve_ffprobe(*, required: bool=False) -> str | None:
    candidates=[
        os.environ.get("BINARIO_FFPROBE"),
        RUNTIME_ROOT/"bin"/"ffprobe",
        "/opt/homebrew/bin/ffprobe",
        "/usr/local/bin/ffprobe",
        "/usr/bin/ffprobe",
        _safe_which("ffprobe"),
    ]
    seen=set()
    for candidate in candidates:
        if not candidate:
            continue
        key=str(candidate)
        if key in seen:
            continue
        seen.add(key)
        healthy=_probe(candidate)
        if healthy:
            return healthy
    if required:
        raise RuntimeToolError("FFprobe no está disponible.")
    return None


def ffmpeg_diagnostic() -> dict:
    path=resolve_ffmpeg(required=False)
    return {
        "tool":"ffmpeg",
        "ready":bool(path),
        "path":path,
        "runtime_root":str(RUNTIME_ROOT),
        "api_key_required":False,
        "opencl_required":False,
    }
