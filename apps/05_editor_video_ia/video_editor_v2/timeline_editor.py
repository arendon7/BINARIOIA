from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json
from .models import TimelinePlan, TimelineCut, AssetSpec

@dataclass
class TimelineOperation:
    op: str
    target_id: str
    value: object = None

@dataclass
class TimelineRevision:
    revision: int
    created_at_utc: str
    parent_hash: str | None
    plan_hash: str
    operations: list[dict]

def plan_hash(plan: TimelinePlan) -> str:
    raw = json.dumps(plan.to_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def _retime(cuts: list[TimelineCut]) -> list[TimelineCut]:
    cursor = 0.0; out = []
    for cut in cuts:
        dur = max(0.05, cut.source_end - cut.source_start)
        out.append(replace(cut, timeline_start=cursor, timeline_end=cursor + dur)); cursor += dur
    return out

def _asset_update(asset: AssetSpec, spec: dict) -> AssetSpec:
    allowed = {"start", "end", "position", "scale", "opacity", "z_index", "enabled", "placement", "volume_db", "loop", "description", "tags", "auto_place", "x_norm", "y_norm", "width_norm", "rotation_deg", "animation_in", "animation_out", "animation_in_duration", "animation_out_duration"}
    values = {k: v for k, v in spec.items() if k in allowed}
    if "start" in values: values["start"] = float(values["start"])
    if "end" in values and values["end"] is not None: values["end"] = float(values["end"])
    if "scale" in values: values["scale"] = max(0.01, min(4.0, float(values["scale"])))
    if "opacity" in values: values["opacity"] = max(0.0, min(1.0, float(values["opacity"])))
    if "z_index" in values: values["z_index"] = int(values["z_index"])
    for key in ("x_norm", "y_norm"):
        if key in values and values[key] is not None: values[key] = max(0.0, min(1.0, float(values[key])))
    if "width_norm" in values and values["width_norm"] is not None: values["width_norm"] = max(0.03, min(0.95, float(values["width_norm"])))
    if "rotation_deg" in values: values["rotation_deg"] = max(-180.0, min(180.0, float(values["rotation_deg"])))
    for key in ("animation_in_duration", "animation_out_duration"):
        if key in values: values[key] = max(0.0, min(5.0, float(values[key])))
    if "animation_in" in values and values["animation_in"] not in {"none","fade","slide_left","slide_right","slide_up","slide_down"}: values["animation_in"] = "fade"
    if "animation_out" in values and values["animation_out"] not in {"none","fade"}: values["animation_out"] = "fade"
    if "volume_db" in values: values["volume_db"] = float(values["volume_db"])
    if "tags" in values: values["tags"] = list(values["tags"] or [])
    return replace(asset, **values)

def apply_operations(plan: TimelinePlan, operations: list[TimelineOperation]) -> TimelinePlan:
    cuts = list(plan.cuts); assets = list(plan.assets); warnings = list(plan.warnings)
    for op in operations:
        if op.op == "delete_cut": cuts = [c for c in cuts if c.id != op.target_id or c.locked]
        elif op.op == "lock_cut": cuts = [replace(c, locked=bool(op.value)) if c.id == op.target_id else c for c in cuts]
        elif op.op == "trim_cut":
            spec = dict(op.value or {}); updated = []
            for c in cuts:
                if c.id != op.target_id or c.locked: updated.append(c); continue
                start = float(spec.get("source_start", c.source_start)); end = float(spec.get("source_end", c.source_end))
                if end <= start: warnings.append(f"Edición ignorada en {c.id}: source_end debe ser > source_start."); updated.append(c)
                else:
                    audio_values = {}
                    if c.audio_source_id and c.audio_source_start is not None and c.audio_source_end is not None:
                        tempo = float(c.audio_tempo or 1.0); audio_values = {"audio_source_start": c.audio_source_start + (start - c.source_start) * tempo, "audio_source_end": c.audio_source_start + (end - c.source_start) * tempo}
                    updated.append(replace(c, source_start=start, source_end=end, **audio_values))
            cuts = updated
        elif op.op == "move_cut":
            idx = next((i for i, c in enumerate(cuts) if c.id == op.target_id), None)
            if idx is not None and not cuts[idx].locked:
                cut = cuts.pop(idx); dest = max(0, min(len(cuts), int(op.value))); cuts.insert(dest, cut)
        elif op.op == "edit_cut_text":
            text = str(op.value or "").strip(); cuts = [replace(c, text=text) if c.id == op.target_id and not c.locked else c for c in cuts]
        elif op.op == "set_cut_role":
            role = str(op.value or "other"); cuts = [replace(c, role=role) if c.id == op.target_id and not c.locked else c for c in cuts]
        elif op.op == "set_cut_focus":
            spec = dict(op.value or {}); fx = max(0.0, min(1.0, float(spec.get("x", 0.5)))); fy = max(0.0, min(1.0, float(spec.get("y", 0.5)))); conf = max(0.0, min(1.0, float(spec.get("confidence", 1.0))))
            cuts = [replace(c, focus_x_norm=fx, focus_y_norm=fy, focus_confidence=conf) if c.id == op.target_id and not c.locked else c for c in cuts]
        elif op.op == "set_cut_audio":
            spec = dict(op.value or {}); allowed = {"audio_source_id", "audio_source_start", "audio_source_end", "audio_sync_confidence", "audio_tempo", "audio_quality_score", "camera_audio_quality_score", "audio_choice_reason"}; values = {k: spec.get(k) for k in allowed if k in spec}
            for key in ("audio_source_start", "audio_source_end", "audio_sync_confidence", "audio_tempo", "audio_quality_score", "camera_audio_quality_score"):
                if key in values and values[key] is not None: values[key] = float(values[key])
            cuts = [replace(c, **values) if c.id == op.target_id and not c.locked else c for c in cuts]
        elif op.op == "split_cut":
            idx = next((i for i, c in enumerate(cuts) if c.id == op.target_id), None)
            if idx is not None and not cuts[idx].locked:
                c = cuts[idx]; split_at = float(op.value["source_time"]) if isinstance(op.value, dict) and "source_time" in op.value else c.source_start + float(op.value)
                if c.source_start + 0.10 < split_at < c.source_end - 0.10:
                    if c.audio_source_id and c.audio_source_start is not None and c.audio_source_end is not None:
                        tempo = float(c.audio_tempo or 1.0); audio_split = c.audio_source_start + (split_at - c.source_start) * tempo; left = replace(c, id=f"{c.id}-a", source_end=split_at, audio_source_end=audio_split); right = replace(c, id=f"{c.id}-b", source_start=split_at, audio_source_start=audio_split)
                    else: left = replace(c, id=f"{c.id}-a", source_end=split_at); right = replace(c, id=f"{c.id}-b", source_start=split_at)
                    cuts[idx:idx+1] = [left, right]
                else: warnings.append(f"Split ignorado en {c.id}: punto demasiado cerca del borde.")
        elif op.op == "add_asset":
            spec = dict(op.value or {}); spec.setdefault("id", op.target_id)
            if not any(a.id == spec["id"] for a in assets): assets.append(AssetSpec(**spec))
        elif op.op in {"set_asset_window", "update_asset"}: assets = [_asset_update(a, dict(op.value or {})) if a.id == op.target_id else a for a in assets]
        elif op.op == "disable_asset": assets = [replace(a, enabled=False) if a.id == op.target_id else a for a in assets]
        elif op.op == "enable_asset": assets = [replace(a, enabled=True) if a.id == op.target_id else a for a in assets]
        elif op.op == "delete_asset": assets = [a for a in assets if a.id != op.target_id]
        else: warnings.append(f"Operación desconocida: {op.op}")
    cuts = _retime(cuts); duration = cuts[-1].timeline_end if cuts else 0.0; tolerance = float(plan.analysis.get("tolerance", 2.0))
    return replace(plan, cuts=cuts, assets=assets, actual_duration=duration, within_tolerance=True if plan.target_duration is None else abs(duration - plan.target_duration) <= tolerance, warnings=warnings)

def save_revision(plan: TimelinePlan, operations: list[TimelineOperation], output_path: str | Path, revision: int = 1, parent_hash: str | None = None) -> Path:
    out = Path(output_path); out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": 1, "revision": asdict(TimelineRevision(revision=revision, created_at_utc=datetime.now(timezone.utc).isoformat(), parent_hash=parent_hash, plan_hash=plan_hash(plan), operations=[asdict(x) for x in operations])), "plan": plan.to_dict()}
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"); return out
