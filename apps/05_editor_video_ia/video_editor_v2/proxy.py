from __future__ import annotations
from .ffmpeg_compiler import compile_ffmpeg
from .models import ProjectSpec, TimelinePlan

def compile_proxy_ffmpeg(project: ProjectSpec, plan: TimelinePlan, output_path: str, subtitle_path: str | None = None) -> list[str]:
    """Build a low-resolution proxy using the exact same edit decisions."""
    cmd = compile_ffmpeg(project, plan, output_path, subtitle_path=subtitle_path, proxy=True)
    return cmd
