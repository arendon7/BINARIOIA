from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from common import project_center


def project_row(project_id: str) -> dict[str, Any]:
    row = project_center.get(project_id)
    if not row:
        raise FileNotFoundError(project_id)
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    root_raw = meta.get("project_path")
    folders = meta.get("folders") if isinstance(meta.get("folders"), dict) else {}
    if not root_raw:
        row = project_center.update(project_id, {"metadata": meta})
        meta = row.get("metadata") or {}
        root_raw = meta.get("project_path")
        folders = meta.get("folders") or {}
    return {"row": row, "root": Path(str(root_raw)).expanduser().resolve(), "folders": {k: Path(str(v)).expanduser().resolve() for k, v in folders.items()}}


def _safe_app_id(app_id: str) -> str:
    value = str(app_id or "").strip()
    if not value or "/" in value or "\\" in value or value in {".", ".."}:
        raise ValueError("app_id inválido")
    return value


def app_state_dir(project_id: str, app_id: str) -> Path:
    info = project_row(project_id)
    base = info["folders"].get("autosave") or (info["root"] / "autosave")
    target = base / "apps" / _safe_app_id(app_id)
    target.mkdir(parents=True, exist_ok=True)
    return target


def app_export_dir(project_id: str, app_id: str) -> Path:
    info = project_row(project_id)
    base = info["folders"].get("exports") or (info["root"] / "exports")
    target = base / _safe_app_id(app_id)
    target.mkdir(parents=True, exist_ok=True)
    return target


def app_training_dir(project_id: str, app_id: str) -> Path:
    info = project_row(project_id)
    base = info["folders"].get("training") or (info["root"] / "training")
    target = base / _safe_app_id(app_id)
    target.mkdir(parents=True, exist_ok=True)
    return target


def app_log_path(project_id: str, app_id: str, name: str = "activity.jsonl") -> Path:
    info = project_row(project_id)
    base = info["folders"].get("logs") or (info["root"] / "logs")
    target = base / _safe_app_id(app_id)
    target.mkdir(parents=True, exist_ok=True)
    return target / Path(name).name


def migrate_legacy_state(project_id: str, app_id: str, legacy_dir: Path) -> dict[str, Any]:
    """Copy legacy app state into the canonical project without deleting the legacy source."""
    legacy_dir = Path(legacy_dir).expanduser().resolve()
    target = app_state_dir(project_id, app_id)
    copied: list[str] = []
    if not legacy_dir.is_dir() or legacy_dir == target:
        return {"ok": True, "copied": copied, "legacy": str(legacy_dir), "target": str(target)}
    for source in legacy_dir.rglob("*"):
        if not source.is_file():
            continue
        rel = source.relative_to(legacy_dir)
        if rel.parts and rel.parts[0] == "exports":
            destination = app_export_dir(project_id, app_id) / Path(*rel.parts[1:])
        elif source.name == "activity.jsonl" and len(rel.parts) == 1:
            destination = app_log_path(project_id, app_id)
        else:
            destination = target / rel
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(str(rel))
    marker = target / "legacy-migration.json"
    marker.write_text(json.dumps({"schema": "sbia-project-storage-migration-1.0", "source": str(legacy_dir), "copied": copied, "non_destructive": True}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "copied": copied, "legacy": str(legacy_dir), "target": str(target), "marker": str(marker)}
