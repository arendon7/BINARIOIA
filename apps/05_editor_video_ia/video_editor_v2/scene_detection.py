from __future__ import annotations
import re
from .runtime_tools import resolve_ffmpeg

PTS_RE = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")

def compile_scene_detection_command(input_path: str, threshold: float = 0.35) -> list[str]:
    threshold = max(0.05, min(0.95, float(threshold)))
    return [
        resolve_ffmpeg(), "-hide_banner", "-i", input_path,
        "-filter:v", f"select='gt(scene,{threshold:.3f})',showinfo",
        "-an", "-f", "null", "-",
    ]

def parse_scene_times(ffmpeg_log: str, min_gap: float = 0.35) -> list[float]:
    raw = [float(x) for x in PTS_RE.findall(ffmpeg_log or "")]
    out = []
    for t in raw:
        if not out or t - out[-1] >= min_gap:
            out.append(round(t, 3))
    return out

def scenes_from_times(duration: float, boundaries: list[float]) -> list[tuple[float, float]]:
    points = [0.0] + [x for x in boundaries if 0 < x < duration] + [duration]
    points = sorted(set(round(x, 3) for x in points))
    return [(points[i], points[i+1]) for i in range(len(points)-1) if points[i+1] > points[i]]
