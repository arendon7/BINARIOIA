from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, Literal, Any
import json

class EditMode(str, Enum):
    NATURAL = "natural"
    TARGET_DURATION = "target_duration"

class NarrativeRole(str, Enum):
    HOOK = "hook"
    CONTEXT = "context"
    MAIN_IDEA = "main_idea"
    ARGUMENT = "argument"
    EVIDENCE = "evidence"
    EXAMPLE = "example"
    TRANSITION = "transition"
    CTA = "cta"
    CLOSING = "closing"
    FILLER = "filler"
    REPETITION = "repetition"
    OTHER = "other"

@dataclass
class VideoSource:
    id: str
    path: str
    label: str = ""
    order: int = 0
    enabled: bool = True
    camera: str = ""
    quality_hint: float = 0.5

@dataclass
class AudioSource:
    id: str
    path: str
    label: str = ""
    kind: Literal["dialogue", "room", "reference"] = "dialogue"
    enabled: bool = True
    quality_hint: float = 0.5
    notes: str = ""

@dataclass
class TranscriptSegment:
    id: str
    source_id: str
    start: float
    end: float
    text: str
    role: str = NarrativeRole.OTHER.value
    relevance: float = 0.6
    clarity: float = 0.6
    energy: float = 0.5
    redundancy: float = 0.0
    must_keep: bool = False
    allow_trim: bool = True
    narrative_order: Optional[int] = None
    keywords: list[str] = field(default_factory=list)
    take_group: Optional[str] = None
    visual_quality: float = 0.5
    audio_quality: float = 0.5
    stability: float = 0.5
    face_presence: float = 0.5

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

@dataclass
class AssetSpec:
    id: str
    path: str
    kind: Literal["logo", "image", "background", "broll", "music", "sfx", "subject_matte", "lower_third"]
    start: float = 0.0
    end: Optional[float] = None
    position: str = "top-right"
    scale: float = 0.20
    opacity: float = 1.0
    z_index: int = 10
    enabled: bool = True
    placement: Literal["background", "behind_subject", "foreground", "broll"] = "foreground"
    tags: list[str] = field(default_factory=list)
    description: str = ""
    auto_place: bool = False
    max_duration: Optional[float] = None
    score: Optional[float] = None
    volume_db: float = -18.0
    loop: bool = True
    x_norm: Optional[float] = None
    y_norm: Optional[float] = None
    width_norm: Optional[float] = None
    rotation_deg: float = 0.0
    animation_in: Literal["none", "fade", "slide_left", "slide_right", "slide_up", "slide_down"] = "fade"
    animation_out: Literal["none", "fade"] = "fade"
    animation_in_duration: float = 0.25
    animation_out_duration: float = 0.25

@dataclass
class OutputSpec:
    width: int = 1080
    height: int = 1920
    fps: int = 30
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    crf: int = 20
    preset: str = "medium"
    proxy_width: int = 360
    proxy_height: int = 640
    proxy_crf: int = 30

@dataclass
class EditPreferences:
    mode: EditMode = EditMode.NATURAL
    target_duration: Optional[float] = None
    tolerance: float = 2.0
    montage_order: Literal["source", "narrative"] = "narrative"
    preserve_all_meaningful_content: bool = True
    remove_fillers: bool = True
    remove_repetitions: bool = True
    min_natural_score: float = 0.45
    pace: Literal["calm", "natural", "dynamic"] = "natural"
    subtitles: bool = True
    smart_assets: bool = True
    smart_broll: bool = True
    subject_layers: bool = False
    transcription_language: Optional[str] = None
    select_best_takes: bool = True
    audio_cleanup: bool = True
    auto_enhance_audio: bool = True
    audio_enhancement_preset: Literal["auto", "natural", "clean", "studio"] = "auto"
    audio_denoise_mode: Literal["off", "auto", "on"] = "auto"
    voice_enhancement: bool = True
    noise_reduction: bool = False
    normalize_loudness: bool = True
    target_lufs: float = -16.0
    true_peak: float = -1.5
    music_ducking: bool = True
    music_duck_threshold: float = 0.025
    music_duck_ratio: float = 8.0
    use_best_dialogue_audio: bool = True
    auto_sync_external_audio: bool = True
    audio_sync_confidence_min: float = 0.28
    audio_replace_margin: float = 0.035
    audio_max_offset_seconds: float = 30.0
    audio_join_fade_ms: float = 12.0
    burn_subtitles: bool = False
    subtitle_style: str = "social"
    subtitle_safe_area: bool = True
    subtitle_position: Literal["bottom", "center", "top"] = "bottom"
    subtitle_width_ratio: float = 0.84
    subtitle_font_scale: float = 1.0
    subtitle_max_lines: int = 2
    auto_reframe: bool = True
    reframe_mode: Literal["center", "subject"] = "subject"
    auto_lower_thirds: bool = True
    brand_preset: str = "binario"

@dataclass
class TimelineCut:
    id: str
    source_id: str
    source_start: float
    source_end: float
    timeline_start: float
    timeline_end: float
    text: str
    role: str
    score: float
    keywords: list[str] = field(default_factory=list)
    locked: bool = False
    focus_x_norm: float = 0.5
    focus_y_norm: float = 0.5
    focus_confidence: float = 0.0
    audio_source_id: Optional[str] = None
    audio_source_start: Optional[float] = None
    audio_source_end: Optional[float] = None
    audio_sync_confidence: float = 1.0
    audio_tempo: float = 1.0
    audio_quality_score: float = 0.0
    camera_audio_quality_score: float = 0.0
    audio_choice_reason: str = ""

    @property
    def duration(self) -> float:
        return max(0.0, self.timeline_end - self.timeline_start)

@dataclass
class TimelinePlan:
    mode: str
    target_duration: Optional[float]
    actual_duration: float
    recommended_min_duration: float
    within_tolerance: bool
    cuts: list[TimelineCut] = field(default_factory=list)
    assets: list[AssetSpec] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    analysis: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class ProjectSpec:
    name: str
    sources: list[VideoSource]
    audio_sources: list[AudioSource] = field(default_factory=list)
    transcript: list[TranscriptSegment] = field(default_factory=list)
    assets: list[AssetSpec] = field(default_factory=list)
    output: OutputSpec = field(default_factory=OutputSpec)
    edit: EditPreferences = field(default_factory=EditPreferences)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, path: str | Path) -> "ProjectSpec":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        edit_data = data.get("edit", {})
        mode = EditMode(edit_data.get("mode", EditMode.NATURAL.value))
        edit = EditPreferences(**{**edit_data, "mode": mode})
        return cls(
            name=data["name"],
            sources=[VideoSource(**x) for x in data.get("sources", [])],
            audio_sources=[AudioSource(**x) for x in data.get("audio_sources", [])],
            transcript=[TranscriptSegment(**x) for x in data.get("transcript", [])],
            assets=[AssetSpec(**x) for x in data.get("assets", [])],
            output=OutputSpec(**data.get("output", {})),
            edit=edit,
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["edit"]["mode"] = self.edit.mode.value
        return data

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
