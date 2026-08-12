from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_AUDIO_POLICY: dict[str, Any] = {
    "auto_normalize": True,
    "duck_music_under_voice": True,
    "target_lufs": -14.0,
    "true_peak_db": -1.0,
    "lra": 11.0,
    "voice_highpass_hz": 80,
    "voice_denoise": True,
    "voice_compression": True,
    "music_gain": 0.30,
    "duck_threshold": 0.03,
    "duck_ratio": 10.0,
    "duck_attack_ms": 20,
    "duck_release_ms": 280,
    "limiter": True,
}


def normalize_audio_policy(value: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(DEFAULT_AUDIO_POLICY)
    if value:
        out.update(value)
    out["target_lufs"] = max(-24.0, min(-8.0, float(out["target_lufs"])))
    out["true_peak_db"] = max(-6.0, min(-0.1, float(out["true_peak_db"])))
    out["lra"] = max(1.0, min(20.0, float(out["lra"])))
    out["voice_highpass_hz"] = max(20, min(220, int(out["voice_highpass_hz"])))
    out["music_gain"] = max(0.0, min(2.0, float(out["music_gain"])))
    out["duck_threshold"] = max(0.001, min(1.0, float(out["duck_threshold"])))
    out["duck_ratio"] = max(1.0, min(30.0, float(out["duck_ratio"])))
    out["duck_attack_ms"] = max(1, min(1000, int(out["duck_attack_ms"])))
    out["duck_release_ms"] = max(20, min(5000, int(out["duck_release_ms"])))
    return out


def analyze_loudness(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"ok": False, "reason": "ffmpeg_not_available"}
    cmd = [
        ffmpeg, "-hide_banner", "-nostats", "-v", "info", "-i", str(path),
        "-vn", "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    stderr = proc.stderr or ""
    matches = re.findall(r"\{\s*\"input_i\".*?\}", stderr, flags=re.S)
    if not matches:
        return {"ok": False, "reason": "loudnorm_summary_missing", "detail": stderr[-1200:]}
    try:
        raw = json.loads(matches[-1])
    except json.JSONDecodeError as exc:
        return {"ok": False, "reason": "invalid_loudnorm_json", "detail": str(exc)}
    def num(key: str) -> float | None:
        try:
            return float(raw.get(key))
        except (TypeError, ValueError):
            return None
    return {
        "ok": True,
        "tool": "ffmpeg:loudnorm",
        "integrated_lufs": num("input_i"),
        "true_peak_db": num("input_tp"),
        "lra": num("input_lra"),
        "threshold": num("input_thresh"),
        "raw": raw,
    }


def voice_filter(policy: dict[str, Any]) -> str:
    p = normalize_audio_policy(policy)
    filters = [f"highpass=f={p['voice_highpass_hz']}"]
    if p["voice_denoise"]:
        filters.append("afftdn=nf=-25")
    if p["voice_compression"]:
        filters.append("acompressor=threshold=0.125:ratio=3:attack=12:release=180:makeup=1.5")
    return ",".join(filters)


def master_filter(policy: dict[str, Any]) -> str:
    p = normalize_audio_policy(policy)
    filters: list[str] = []
    if p["auto_normalize"]:
        filters.append(f"loudnorm=I={p['target_lufs']}:TP={p['true_peak_db']}:LRA={p['lra']}")
    if p["limiter"]:
        filters.append("alimiter=limit=0.95:attack=5:release=50")
    return ",".join(filters) or "anull"
