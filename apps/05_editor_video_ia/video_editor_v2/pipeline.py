from __future__ import annotations
from dataclasses import dataclass
from .models import ProjectSpec, TimelinePlan
from .transcriber import TranscriptProvider, transcribe_project
from .narrative import NarrativeProvider, HeuristicNarrativeAnalyzer
from .planner import build_timeline
from .asset_matcher import auto_place_assets
from .preview import generate_preview_html
from .subtitles import write_srt, write_ass
from .qc import quality_control

@dataclass
class PipelineResult:
    project: ProjectSpec
    plan: TimelinePlan
    preview_path: str | None = None
    srt_path: str | None = None
    ass_path: str | None = None
    qc: dict | None = None

class VideoEditPipeline:
    def __init__(self, transcript_provider: TranscriptProvider | None = None, narrative_provider: NarrativeProvider | None = None):
        self.transcript_provider = transcript_provider
        self.narrative_provider = narrative_provider or HeuristicNarrativeAnalyzer()

    def analyze(self, project: ProjectSpec, *, force_transcription: bool = False, preview_path: str | None = None, subtitle_dir: str | None = None) -> PipelineResult:
        if not project.transcript:
            if self.transcript_provider is None:
                raise RuntimeError("El proyecto no tiene transcripción y no se configuró TranscriptProvider.")
            transcribe_project(project, self.transcript_provider, force=force_transcription)

        project.transcript = self.narrative_provider.analyze(project.transcript)
        plan = build_timeline(project)
        plan.assets = auto_place_assets(plan, project.assets) if project.edit.smart_assets else [a for a in project.assets if a.enabled]

        preview = str(generate_preview_html(project, plan, preview_path)) if preview_path else None
        srt = ass = None
        if subtitle_dir and project.edit.subtitles:
            from pathlib import Path
            d=Path(subtitle_dir); d.mkdir(parents=True,exist_ok=True)
            srt=str(write_srt(plan,d/"subtitles.srt"))
            ass=str(write_ass(plan,d/"subtitles.ass",width=project.output.width,height=project.output.height,style=project.edit.subtitle_style,safe_area=project.edit.subtitle_safe_area,position=project.edit.subtitle_position,width_ratio=project.edit.subtitle_width_ratio,font_scale=project.edit.subtitle_font_scale,max_lines=project.edit.subtitle_max_lines))
        qc=quality_control(project,plan)
        return PipelineResult(project=project,plan=plan,preview_path=preview,srt_path=srt,ass_path=ass,qc=qc)
