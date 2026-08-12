from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

SCHEMA = "binario-ia/ui-preferences/v1"
DEFAULTS: dict[str, Any] = {
    "video_editing_mode": "simple",
    "video_focus_mode": False,
}
ALLOWED_VIDEO_MODES = {"simple", "pro"}


def preferences_path() -> Path:
    override = os.environ.get("BINARIO_UI_PREFERENCES_FILE")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / "Library" / "Application Support" / "Binario IA" / "ui" / "preferences.json").resolve()


def _sanitize(data: dict[str, Any] | None) -> dict[str, Any]:
    source = data if isinstance(data, dict) else {}
    mode = str(source.get("video_editing_mode") or DEFAULTS["video_editing_mode"])
    if mode not in ALLOWED_VIDEO_MODES:
        mode = DEFAULTS["video_editing_mode"]
    return {
        "schema": SCHEMA,
        "video_editing_mode": mode,
        "video_focus_mode": bool(source.get("video_focus_mode", DEFAULTS["video_focus_mode"])),
    }


def load_preferences() -> dict[str, Any]:
    path = preferences_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = {}
    result = _sanitize(data)
    result["path"] = str(path)
    return result


def update_preferences(patch: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(patch, dict):
        raise ValueError("preferences patch must be object")
    current = load_preferences()
    merged = {**current}
    if "video_editing_mode" in patch:
        mode = str(patch["video_editing_mode"])
        if mode not in ALLOWED_VIDEO_MODES:
            raise ValueError("video_editing_mode must be simple or pro")
        merged["video_editing_mode"] = mode
    if "video_focus_mode" in patch:
        merged["video_focus_mode"] = bool(patch["video_focus_mode"])
    result = _sanitize(merged)
    path = preferences_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    result["path"] = str(path)
    return result
