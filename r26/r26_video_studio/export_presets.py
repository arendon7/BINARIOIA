from __future__ import annotations

from copy import deepcopy
from typing import Any

from .project_model import VideoProject

EXPORT_PRESETS: dict[str, dict[str, Any]] = {
    "reels": {"label": "Instagram Reels", "aspect_ratio": "9:16", "resolution": [1080, 1920], "fps": 30, "quality_label": "Alta · H.264", "target_lufs": -14.0, "true_peak_db": -1.0, "platform": "instagram", "safe_title": 0.10, "safe_bottom": 0.18},
    "tiktok": {"label": "TikTok", "aspect_ratio": "9:16", "resolution": [1080, 1920], "fps": 30, "quality_label": "Alta · H.264", "target_lufs": -14.0, "true_peak_db": -1.0, "platform": "tiktok", "safe_title": 0.11, "safe_bottom": 0.20},
    "shorts": {"label": "YouTube Shorts", "aspect_ratio": "9:16", "resolution": [1080, 1920], "fps": 30, "quality_label": "Alta · H.264", "target_lufs": -14.0, "true_peak_db": -1.0, "platform": "youtube_shorts", "safe_title": 0.08, "safe_bottom": 0.16},
    "youtube": {"label": "YouTube 1080p", "aspect_ratio": "16:9", "resolution": [1920, 1080], "fps": 30, "quality_label": "Máxima · H.264", "target_lufs": -14.0, "true_peak_db": -1.0, "platform": "youtube", "safe_title": 0.06, "safe_bottom": 0.08},
    "square": {"label": "Feed cuadrado", "aspect_ratio": "1:1", "resolution": [1080, 1080], "fps": 30, "quality_label": "Alta · H.264", "target_lufs": -14.0, "true_peak_db": -1.0, "platform": "feed", "safe_title": 0.07, "safe_bottom": 0.10},
    "archive": {"label": "Master archivo", "aspect_ratio": None, "resolution": None, "fps": 30, "quality_label": "Máxima · H.264", "target_lufs": -16.0, "true_peak_db": -1.0, "platform": "archive", "safe_title": 0.05, "safe_bottom": 0.05},
}


def list_export_presets() -> list[dict[str, Any]]:
    return [{"id": key, **deepcopy(value)} for key, value in EXPORT_PRESETS.items()]


def apply_export_preset(project: VideoProject, sequence_id: str, preset_id: str) -> dict[str, Any]:
    if preset_id not in EXPORT_PRESETS:
        raise ValueError(f"unknown export preset: {preset_id}")
    preset = deepcopy(EXPORT_PRESETS[preset_id])
    seq = project.sequence(sequence_id)
    if preset.get("aspect_ratio"):
        seq.aspect_ratio = str(preset["aspect_ratio"])
    project.settings.setdefault("export", {})
    project.settings.setdefault("audio", {})
    export = project.settings["export"]
    export.update({
        "publish_preset": preset_id,
        "platform": preset["platform"],
        "fps": int(preset["fps"]),
        "quality_label": preset["quality_label"],
        "resolution": preset.get("resolution"),
        "safe_title": preset["safe_title"],
        "safe_bottom": preset["safe_bottom"],
    })
    project.settings["audio"]["target_lufs"] = float(preset["target_lufs"])
    project.settings["audio"]["true_peak_db"] = float(preset["true_peak_db"])
    project.validate()
    return {"project": project, "preset": {"id": preset_id, **preset}}
