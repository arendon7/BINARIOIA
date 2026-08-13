from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .acceleration import choose_h264_encoder


def _cache_root(project: dict[str, Any]) -> Path:
    root = (Path(project["folders"]["autosave"]) / "cache").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _key(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.name}|{stat.st_size}|{stat.st_mtime_ns}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def generate_thumbnail(path: Path, project: dict[str, Any], *, at: float | None = None) -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"ok": False, "reason": "ffmpeg_not_available"}
    path = path.resolve()
    seek = max(0.0, float(at if at is not None else 0.5))
    seek_key = hashlib.sha256(f"{_key(path)}|{seek:.3f}".encode()).hexdigest()[:16]
    target = _cache_root(project) / f"thumb-{seek_key}.jpg"
    if target.is_file() and target.stat().st_size > 0:
        return {"ok": True, "cached": True, "path": str(target), "cache_name": target.name}
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-ss", str(seek), "-i", str(path), "-frames:v", "1", "-vf", "scale=480:-2:force_original_aspect_ratio=decrease", "-q:v", "3", str(target)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45, check=False)
    if proc.returncode != 0 or not target.is_file():
        return {"ok": False, "reason": "thumbnail_failed", "detail": (proc.stderr or "")[-1200:]}
    return {"ok": True, "cached": False, "path": str(target), "cache_name": target.name}


def generate_proxy(path: Path, project: dict[str, Any], *, max_width: int = 960) -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"ok": False, "reason": "ffmpeg_not_available"}
    path = path.resolve()
    target = _cache_root(project) / f"proxy-{_key(path)}.mp4"
    if target.is_file() and target.stat().st_size > 0:
        return {"ok": True, "cached": True, "path": str(target), "cache_name": target.name, "mode": "editing_proxy"}
    width = max(320, min(1280, int(max_width)))
    encoder = choose_h264_encoder({"hardware_acceleration": "auto"})
    video_args = ["-c:v", encoder["encoder"]]
    if encoder["encoder"] == "h264_videotoolbox":
        video_args += ["-b:v", "2500k", "-maxrate", "3500k", "-bufsize", "5000k", "-realtime", "1"]
    else:
        video_args += ["-preset", "veryfast", "-crf", "30"]
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-map", "0:v:0", "-map", "0:a?", "-vf", f"scale='min({width},iw)':-2:force_original_aspect_ratio=decrease",
        *video_args, "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(target),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60 * 30, check=False)
    if proc.returncode != 0 or not target.is_file():
        return {"ok": False, "reason": "proxy_failed", "detail": (proc.stderr or "")[-1600:]}
    return {"ok": True, "cached": False, "path": str(target), "cache_name": target.name, "size": target.stat().st_size, "mode": "editing_proxy", "encoder": encoder["encoder"]}


def cache_file(project: dict[str, Any], name: str) -> Path:
    safe = Path(name).name
    if safe != name or not safe:
        raise ValueError("invalid cache filename")
    target = (_cache_root(project) / safe).resolve()
    if target.parent != _cache_root(project) or not target.is_file():
        raise FileNotFoundError(target)
    return target
