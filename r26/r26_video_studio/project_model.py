from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable
import json
import uuid

TRACK_ORDER = [
    "video",
    "broll",
    "images",
    "key_ideas",
    "subtitles",
    "music",
    "voiceover",
]
TRACK_KINDS = set(TRACK_ORDER)
ASSET_KINDS = {"video", "image", "audio", "logo", "subtitle", "other"}


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass
class Asset:
    id: str
    name: str
    kind: str
    source: str
    duration: float | None = None
    removable: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.id or not self.name:
            raise ValueError("asset id/name required")
        if self.kind not in ASSET_KINDS:
            raise ValueError(f"unsupported asset kind: {self.kind}")
        if self.duration is not None and self.duration < 0:
            raise ValueError("asset duration must be >= 0")


@dataclass
class TimelineItem:
    id: str
    track: str
    start: float
    duration: float
    asset_id: str | None = None
    source_in: float = 0.0
    label: str = ""
    enabled: bool = True
    volume: float = 1.0
    opacity: float = 1.0
    z_index: int = 0
    text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    transform: dict[str, Any] = field(default_factory=lambda: {"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 0.0, "crop": {"top": 0.0, "right": 0.0, "bottom": 0.0, "left": 0.0}, "fit": "contain"})
    transitions: dict[str, Any] = field(default_factory=lambda: {"in": {"type": "none", "duration": 0.0}, "out": {"type": "none", "duration": 0.0}})
    keyframes: list[dict[str, Any]] = field(default_factory=list)
    color: dict[str, Any] = field(default_factory=lambda: {"brightness": 0.0, "contrast": 1.0, "saturation": 1.0, "gamma": 1.0, "temperature": 0.0, "tint": 0.0, "preset": "natural"})
    text_style: dict[str, Any] = field(default_factory=lambda: {"preset": "clean_white", "font_scale": 1.0, "position": "bottom"})

    @property
    def end(self) -> float:
        return self.start + self.duration

    def validate(self) -> None:
        if self.track not in TRACK_KINDS:
            raise ValueError(f"unsupported track: {self.track}")
        if self.start < 0:
            raise ValueError("timeline start must be >= 0")
        if self.duration <= 0:
            raise ValueError("timeline duration must be > 0")
        if self.source_in < 0:
            raise ValueError("source_in must be >= 0")
        if not 0 <= self.volume <= 4:
            raise ValueError("volume outside supported range")
        if not 0 <= self.opacity <= 1:
            raise ValueError("opacity outside supported range")
        if not isinstance(self.transform, dict):
            raise ValueError("transform must be object")
        x, y = float(self.transform.get("x", 0.5)), float(self.transform.get("y", 0.5))
        scale = float(self.transform.get("scale", 1.0))
        rotation = float(self.transform.get("rotation", 0.0))
        if not -2 <= x <= 3 or not -2 <= y <= 3:
            raise ValueError("transform position outside supported range")
        if not 0.01 <= scale <= 20:
            raise ValueError("transform scale outside supported range")
        if not -3600 <= rotation <= 3600:
            raise ValueError("transform rotation outside supported range")
        crop = self.transform.get("crop") or {}
        for side in ("top", "right", "bottom", "left"):
            value = float(crop.get(side, 0.0))
            if not 0 <= value <= 0.95:
                raise ValueError(f"invalid crop {side}")
        if self.transform.get("fit", "contain") not in {"contain", "cover", "stretch"}:
            raise ValueError("invalid transform fit")
        if not isinstance(self.transitions, dict):
            raise ValueError("transitions must be object")
        for edge in ("in", "out"):
            transition = self.transitions.get(edge) or {"type": "none", "duration": 0.0}
            if transition.get("type", "none") not in {"none", "fade", "dissolve", "slide_left", "slide_right", "zoom"}:
                raise ValueError("unsupported transition")
            duration = float(transition.get("duration", 0.0))
            if duration < 0 or duration > self.duration:
                raise ValueError("invalid transition duration")
        if not isinstance(self.color, dict):
            raise ValueError("color must be object")
        color_ranges = {"brightness": (-1.0, 1.0), "contrast": (0.0, 3.0), "saturation": (0.0, 4.0), "gamma": (0.1, 5.0), "temperature": (-1.0, 1.0), "tint": (-1.0, 1.0)}
        for key, (lo, hi) in color_ranges.items():
            value = float(self.color.get(key, {"brightness": 0.0, "contrast": 1.0, "saturation": 1.0, "gamma": 1.0, "temperature": 0.0, "tint": 0.0}[key]))
            if not lo <= value <= hi:
                raise ValueError(f"color {key} outside supported range")
        if self.color.get("preset", "natural") not in {"natural", "vivid", "warm", "cool", "mono", "cinematic"}:
            raise ValueError("unsupported color preset")
        if not isinstance(self.text_style, dict):
            raise ValueError("text_style must be object")
        if self.text_style.get("preset", "clean_white") not in {"clean_white", "bold_social", "minimal", "boxed", "brand_gold"}:
            raise ValueError("unsupported text style")
        if not 0.5 <= float(self.text_style.get("font_scale", 1.0)) <= 3.0:
            raise ValueError("text font scale outside supported range")
        if self.text_style.get("position", "bottom") not in {"bottom", "middle", "top"}:
            raise ValueError("unsupported text position")
        if not isinstance(self.keyframes, list):
            raise ValueError("keyframes must be list")
        last = -1.0
        for frame in sorted(self.keyframes, key=lambda f: float(f.get("time", 0))):
            time = float(frame.get("time", 0))
            if time < 0 or time > self.duration:
                raise ValueError("keyframe outside item duration")
            if time < last:
                raise ValueError("keyframes not ordered")
            last = time


@dataclass
class Track:
    id: str
    kind: str
    label: str
    enabled: bool = True
    locked: bool = False
    muted: bool = False
    items: list[TimelineItem] = field(default_factory=list)

    def validate(self) -> None:
        if self.kind not in TRACK_KINDS:
            raise ValueError(f"unsupported track kind: {self.kind}")
        for item in self.items:
            if item.track != self.kind:
                raise ValueError(f"item {item.id} track mismatch")
            item.validate()


@dataclass
class Sequence:
    id: str
    name: str
    kind: str
    aspect_ratio: str = "16:9"
    duration: float = 60.0
    playhead: float = 0.0
    tracks: list[Track] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)

    def validate(self, asset_ids: set[str]) -> None:
        if self.kind not in {"long", "clip"}:
            raise ValueError("sequence kind must be long or clip")
        if self.duration <= 0:
            raise ValueError("sequence duration must be > 0")
        kinds = [t.kind for t in self.tracks]
        if len(kinds) != len(set(kinds)):
            raise ValueError("duplicate track kind")
        for track in self.tracks:
            track.validate()
            for item in track.items:
                if item.asset_id and item.asset_id not in asset_ids:
                    raise ValueError(f"orphan timeline item: {item.asset_id}")


@dataclass
class VideoProject:
    schema_version: int
    id: str
    name: str
    assets: list[Asset]
    sequences: list[Sequence]
    active_sequence_id: str
    settings: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.schema_version < 26:
            raise ValueError("R26 project schema required")
        asset_ids: set[str] = set()
        for asset in self.assets:
            asset.validate()
            if asset.id in asset_ids:
                raise ValueError(f"duplicate asset id: {asset.id}")
            asset_ids.add(asset.id)
        seq_ids = {s.id for s in self.sequences}
        if self.active_sequence_id not in seq_ids:
            raise ValueError("active sequence missing")
        if not any(s.kind == "long" for s in self.sequences):
            raise ValueError("project must contain a long sequence")
        for seq in self.sequences:
            seq.validate(asset_ids)

    def active_sequence(self) -> Sequence:
        for seq in self.sequences:
            if seq.id == self.active_sequence_id:
                return seq
        raise KeyError(self.active_sequence_id)

    def asset(self, asset_id: str) -> Asset:
        for asset in self.assets:
            if asset.id == asset_id:
                return asset
        raise KeyError(asset_id)

    def remove_asset(self, asset_id: str, *, cascade: bool = True) -> dict[str, Any]:
        asset = self.asset(asset_id)
        if not asset.removable:
            raise ValueError("asset is protected")
        refs = []
        for seq in self.sequences:
            for track in seq.tracks:
                for item in track.items:
                    if item.asset_id == asset_id:
                        refs.append((seq.id, track.kind, item.id))
        if refs and not cascade:
            raise ValueError(f"asset is used by {len(refs)} timeline items")
        self.assets = [a for a in self.assets if a.id != asset_id]
        if cascade:
            for seq in self.sequences:
                for track in seq.tracks:
                    track.items = [i for i in track.items if i.asset_id != asset_id]
        self.validate()
        return {"removed_asset": asset_id, "removed_timeline_items": len(refs)}

    def set_key_ideas_enabled(self, enabled: bool, sequence_id: str | None = None) -> None:
        targets = self.sequences if sequence_id is None else [self.sequence(sequence_id)]
        for seq in targets:
            track = next((t for t in seq.tracks if t.kind == "key_ideas"), None)
            if track:
                track.enabled = bool(enabled)
                for item in track.items:
                    item.enabled = bool(enabled)
        self.settings["key_ideas_default"] = bool(enabled)

    def sequence(self, sequence_id: str) -> Sequence:
        for seq in self.sequences:
            if seq.id == sequence_id:
                return seq
        raise KeyError(sequence_id)

    def duplicate_sequence(self, sequence_id: str, *, name: str | None = None, kind: str = "clip") -> Sequence:
        src = self.sequence(sequence_id)
        clone = deepcopy(src)
        clone.id = _id("seq")
        clone.name = name or f"{src.name} copia"
        clone.kind = kind
        for track in clone.tracks:
            track.id = _id("track")
            for item in track.items:
                item.id = _id("item")
        self.sequences.append(clone)
        self.validate()
        return clone

    def add_asset(self, *, name: str, kind: str, source: str, duration: float | None = None, metadata: dict[str, Any] | None = None) -> Asset:
        asset = Asset(_id("asset"), name=name, kind=kind, source=source, duration=duration, metadata=metadata or {})
        asset.validate()
        self.assets.append(asset)
        return asset

    def add_timeline_item(
        self,
        sequence_id: str,
        *,
        track_kind: str,
        start: float,
        duration: float,
        asset_id: str | None = None,
        label: str = "",
        text: str | None = None,
    ) -> TimelineItem:
        seq = self.sequence(sequence_id)
        track = next((t for t in seq.tracks if t.kind == track_kind), None)
        if not track:
            raise ValueError(f"track not found: {track_kind}")
        if asset_id:
            self.asset(asset_id)
        item = TimelineItem(
            id=_id("item"),
            track=track_kind,
            start=clamp(float(start), 0, max(seq.duration - 0.05, 0)),
            duration=max(0.05, min(float(duration), seq.duration - float(start))),
            asset_id=asset_id,
            label=label,
            text=text,
        )
        if track_kind == "key_ideas":
            item.text_style["position"] = "top"
        item.validate()
        track.items.append(item)
        return item

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VideoProject":
        assets = [Asset(**a) for a in data.get("assets", [])]
        sequences: list[Sequence] = []
        for s in data.get("sequences", []):
            tracks = []
            for t in s.get("tracks", []):
                items = [TimelineItem(**i) for i in t.get("items", [])]
                tracks.append(Track(id=t["id"], kind=t["kind"], label=t["label"], enabled=t.get("enabled", True), locked=t.get("locked", False), muted=t.get("muted", False), items=items))
            seq = Sequence(id=s["id"], name=s["name"], kind=s["kind"], aspect_ratio=s.get("aspect_ratio", "16:9"), duration=float(s.get("duration", 60.0)), playhead=float(s.get("playhead", 0.0)), tracks=tracks, settings=s.get("settings", {}))
            sequences.append(seq)
        project = cls(
            schema_version=int(data.get("schema_version", 26)),
            id=data.get("id") or _id("project"),
            name=data.get("name", "Proyecto de video"),
            assets=assets,
            sequences=sequences,
            active_sequence_id=data.get("active_sequence_id") or (sequences[0].id if sequences else ""),
            settings=data.get("settings", {}),
        )
        project.validate()
        return project


def default_tracks() -> list[Track]:
    labels = {
        "video": "Video principal",
        "broll": "B-roll / video",
        "images": "Imágenes / logos",
        "key_ideas": "Ideas clave",
        "subtitles": "Subtítulos",
        "music": "Música",
        "voiceover": "Voz / audio externo",
    }
    tracks = []
    for kind in TRACK_ORDER:
        tracks.append(Track(id=_id("track"), kind=kind, label=labels[kind], enabled=(kind != "key_ideas"), locked=(kind == "subtitles")))
    return tracks


def new_project(name: str = "Video nuevo", duration: float = 60.0) -> VideoProject:
    seq = Sequence(
        id=_id("seq"),
        name="Video largo",
        kind="long",
        duration=max(1.0, duration),
        tracks=default_tracks(),
        settings={"captions_style": "white_bottom", "safe_zones": True, "snap": True},
    )
    project = VideoProject(
        schema_version=26,
        id=_id("project"),
        name=name,
        assets=[],
        sequences=[seq],
        active_sequence_id=seq.id,
        settings={
            "key_ideas_default": False,
            "autosave": True,
            "editing_mode": "simple",
            "audio": {"auto_normalize": True, "duck_music_under_voice": True, "target_lufs": -14.0, "true_peak_db": -1.0, "lra": 11.0, "voice_highpass_hz": 80, "voice_denoise": True, "voice_compression": True, "music_gain": 0.30, "limiter": True},
            "export": {"codec": "h264", "audio_codec": "aac", "preset": "social_high", "hardware_acceleration": "auto", "quality_label": "Alta · H.264"},
        },
    )
    project.validate()
    return project


def migrate_legacy_project(data: dict[str, Any]) -> VideoProject:
    if int(data.get("schema_version", 0) or 0) >= 26 and data.get("sequences"):
        project = VideoProject.from_dict(data)
        project.set_key_ideas_enabled(False)
        return project

    duration = float(data.get("duration") or data.get("target_duration") or 60.0)
    project = new_project(data.get("name") or data.get("title") or "Proyecto migrado", duration)
    seq = project.active_sequence()
    legacy_assets: Iterable[dict[str, Any]] = data.get("assets") or data.get("media") or []
    id_map: dict[str, str] = {}
    for old in legacy_assets:
        if not isinstance(old, dict):
            continue
        src = str(old.get("path") or old.get("source") or old.get("url") or "")
        name = str(old.get("name") or Path(src).name or "Recurso")
        kind = str(old.get("kind") or old.get("type") or "other").lower()
        if kind not in ASSET_KINDS:
            if kind in {"music", "voice", "audio_external"}:
                kind = "audio"
            elif kind in {"photo", "picture", "broll_image"}:
                kind = "image"
            else:
                kind = "other"
        asset = project.add_asset(name=name, kind=kind, source=src, duration=old.get("duration"), metadata={"legacy": True})
        if old.get("id"):
            id_map[str(old["id"])] = asset.id

    def add_from_rows(rows: Iterable[dict[str, Any]], track_kind: str, *, disabled: bool = False):
        track = next(t for t in seq.tracks if t.kind == track_kind)
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            start = float(row.get("start") or row.get("at") or 0)
            end = row.get("end")
            dur = float(row.get("duration") or ((float(end) - start) if end is not None else 3.0))
            old_asset = row.get("asset_id") or row.get("asset")
            item = project.add_timeline_item(
                seq.id,
                track_kind=track_kind,
                start=start,
                duration=max(0.05, dur),
                asset_id=id_map.get(str(old_asset)) if old_asset is not None else None,
                label=str(row.get("label") or row.get("title") or ""),
                text=row.get("text") or row.get("caption") or row.get("idea"),
            )
            item.enabled = not disabled
        if disabled:
            track.enabled = False

    add_from_rows(data.get("subtitles") or data.get("captions") or [], "subtitles")
    add_from_rows(data.get("images") or data.get("visual_overlays") or [], "images")
    add_from_rows(data.get("music") or data.get("music_cues") or [], "music")
    key_rows = data.get("key_ideas") or data.get("idea_overlays") or data.get("highlights") or data.get("lower_thirds") or []
    add_from_rows(key_rows, "key_ideas", disabled=True)
    project.settings["migration"] = {"source_schema": data.get("schema_version"), "key_ideas_forced_off": True}
    project.validate()
    return project


def save_project(project: VideoProject, path: Path) -> None:
    project.validate()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(project.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_project(path: Path) -> VideoProject:
    data = json.loads(path.read_text(encoding="utf-8"))
    return migrate_legacy_project(data)
