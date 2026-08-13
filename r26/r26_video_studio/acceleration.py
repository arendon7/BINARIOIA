from __future__ import annotations

import platform
import shutil
import subprocess
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=4)
def _encoders(ffmpeg: str) -> str:
    try:
        proc = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=8, check=False)
        return (proc.stdout or "") + "\n" + (proc.stderr or "")
    except Exception:
        return ""


def acceleration_status() -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    machine = platform.machine().lower()
    system = platform.system().lower()
    text = _encoders(ffmpeg) if ffmpeg else ""
    videotoolbox = bool(ffmpeg and "h264_videotoolbox" in text)
    hevc_videotoolbox = bool(ffmpeg and "hevc_videotoolbox" in text)
    apple_silicon = system == "darwin" and machine in {"arm64", "arm64e", "aarch64"}
    return {
        "ffmpeg": ffmpeg,
        "system": system,
        "machine": machine,
        "apple_silicon": apple_silicon,
        "h264_videotoolbox": videotoolbox,
        "hevc_videotoolbox": hevc_videotoolbox,
        "recommended": "h264_videotoolbox" if apple_silicon and videotoolbox else "libx264",
        "policy": "auto_prefers_videotoolbox_on_apple_silicon_safe_fallback_libx264",
    }


def choose_h264_encoder(export_settings: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = export_settings or {}
    requested = str(settings.get("hardware_acceleration", "auto") or "auto").lower()
    status = acceleration_status()
    allow_hw = requested not in {"off", "false", "disabled", "software"}
    force_hw = requested in {"on", "true", "enabled", "hardware", "videotoolbox"}
    use_videotoolbox = allow_hw and status["apple_silicon"] and status["h264_videotoolbox"]
    if force_hw and not use_videotoolbox:
        return {**status, "encoder": "libx264", "requested": requested, "fallback_reason": "videotoolbox_unavailable"}
    return {**status, "encoder": "h264_videotoolbox" if use_videotoolbox else "libx264", "requested": requested, "fallback_reason": None}
