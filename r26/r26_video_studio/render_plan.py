from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json

from .project_model import VideoProject, Sequence

@dataclass
class RenderLayer:
    track: str
    item_id: str
    asset_id: str | None
    start: float
    duration: float
    enabled: bool
    payload: dict[str, Any]

@dataclass
class RenderPlan:
    project_id: str
    sequence_id: str
    duration: float
    aspect_ratio: str
    layers: list[RenderLayer]
    audio_policy: dict[str, Any]
    export: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_render_plan(project: VideoProject, sequence_id: str | None = None) -> RenderPlan:
    project.validate()
    seq = project.sequence(sequence_id or project.active_sequence_id)
    layers: list[RenderLayer] = []
    for track in seq.tracks:
        if not track.enabled:
            continue
        for item in sorted(track.items, key=lambda i: (i.start, i.z_index, i.id)):
            if not item.enabled:
                continue
            layers.append(RenderLayer(
                track=track.kind,
                item_id=item.id,
                asset_id=item.asset_id,
                start=item.start,
                duration=item.duration,
                enabled=True,
                payload={
                    "source_in": item.source_in,
                    "volume": 0.0 if track.muted else item.volume,
                    "track_muted": track.muted,
                    "opacity": item.opacity,
                    "z_index": item.z_index,
                    "text": item.text,
                    "transform": item.transform,
                    "transitions": item.transitions,
                    "keyframes": item.keyframes,
                    "metadata": item.metadata,
                },
            ))
    return RenderPlan(
        project_id=project.id,
        sequence_id=seq.id,
        duration=seq.duration,
        aspect_ratio=seq.aspect_ratio,
        layers=layers,
        audio_policy=project.settings.get("audio", {}),
        export=project.settings.get("export", {}),
    )


def export_render_plan(project: VideoProject, path: Path, sequence_id: str | None = None) -> Path:
    plan = build_render_plan(project, sequence_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
