from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import wave
from array import array
from pathlib import Path
from typing import Any


def media_tools() -> dict[str, Any]:
    return {
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "policy": "optional_acceleration_editor_remains_usable_without_tools",
    }


def probe_media(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {"ok": True, "path": str(path), "duration": None, "streams": [], "tool": None}
    cmd = [
        ffprobe, "-v", "error", "-show_entries",
        "format=duration,size,format_name:stream=index,codec_type,codec_name,width,height,sample_rate,channels",
        "-of", "json", str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if proc.returncode != 0:
        return {"ok": False, "path": str(path), "duration": None, "streams": [], "tool": "ffprobe", "error": proc.stderr.strip()[-1000:]}
    data = json.loads(proc.stdout or "{}")
    fmt = data.get("format") or {}
    try:
        duration = float(fmt.get("duration")) if fmt.get("duration") is not None else None
    except (TypeError, ValueError):
        duration = None
    return {
        "ok": True,
        "path": str(path),
        "duration": duration,
        "size": int(fmt.get("size") or path.stat().st_size),
        "format_name": fmt.get("format_name"),
        "streams": data.get("streams") or [],
        "tool": "ffprobe",
    }


def _normalize_peaks(values: list[float]) -> list[float]:
    if not values:
        return []
    maximum = max(max(values), 1e-9)
    return [round(max(0.0, min(1.0, v / maximum)), 4) for v in values]


def _bucket_abs(samples: list[float], points: int) -> list[float]:
    if not samples:
        return [0.0] * points
    points = max(16, min(1200, int(points)))
    stride = max(1, math.ceil(len(samples) / points))
    out: list[float] = []
    for i in range(0, len(samples), stride):
        chunk = samples[i:i + stride]
        if not chunk:
            continue
        peak = max(abs(x) for x in chunk)
        rms = math.sqrt(sum(x * x for x in chunk) / len(chunk))
        out.append(0.7 * peak + 0.3 * rms)
        if len(out) >= points:
            break
    if len(out) < points:
        out.extend([0.0] * (points - len(out)))
    return _normalize_peaks(out[:points])


def _wav_waveform(path: Path, points: int) -> dict[str, Any] | None:
    if path.suffix.lower() != ".wav":
        return None
    try:
        with wave.open(str(path), "rb") as wf:
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            rate = wf.getframerate()
            frames = wf.getnframes()
            if width != 2:
                return None
            raw = wf.readframes(frames)
            vals = array("h")
            vals.frombytes(raw)
            if channels > 1:
                mono = []
                for i in range(0, len(vals), channels):
                    row = vals[i:i + channels]
                    mono.append(sum(row) / (32768.0 * max(1, len(row))))
            else:
                mono = [v / 32768.0 for v in vals]
            return {"peaks": _bucket_abs(mono, points), "duration": frames / float(rate or 1), "tool": "wave"}
    except (wave.Error, OSError):
        return None


def generate_waveform(path: Path, points: int = 220) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    points = max(16, min(1200, int(points)))
    native = _wav_waveform(path, points)
    if native:
        return {"ok": True, **native, "points": points}
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"ok": False, "peaks": [], "duration": None, "points": points, "tool": None, "reason": "ffmpeg_not_available"}
    cmd = [ffmpeg, "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "400", "-t", "21600", "-f", "f32le", "pipe:1"]
    proc = subprocess.run(cmd, capture_output=True, timeout=90)
    if proc.returncode != 0:
        return {"ok": False, "peaks": [], "duration": None, "points": points, "tool": "ffmpeg", "reason": proc.stderr.decode("utf-8", "ignore")[-1000:]}
    vals = array("f")
    vals.frombytes(proc.stdout)
    samples = [float(v) for v in vals]
    duration = len(samples) / 400.0
    return {"ok": True, "peaks": _bucket_abs(samples, points), "duration": duration, "points": points, "tool": "ffmpeg"}


def detect_scenes(path: Path, *, threshold: float = 0.30, min_gap: float = 0.75, max_scenes: int = 80) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    threshold = max(0.05, min(0.95, float(threshold)))
    min_gap = max(0.10, min(30.0, float(min_gap)))
    max_scenes = max(1, min(240, int(max_scenes)))
    probe = probe_media(path)
    duration = probe.get("duration")
    ffmpeg = shutil.which("ffmpeg")
    scenes: list[dict[str, Any]] = [{"time": 0.0, "score": None}]
    if not ffmpeg:
        return {"ok": False, "reason": "ffmpeg_not_available", "duration": duration, "threshold": threshold, "scenes": scenes, "tool": None}
    expr = f"select='gt(scene,{threshold:.4f})',showinfo"
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "info", "-i", str(path), "-an", "-vf", expr, "-vsync", "vfr", "-f", "null", "-"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "scene_detection_timeout", "duration": duration, "threshold": threshold, "scenes": scenes, "tool": "ffmpeg"}
    text = (proc.stderr or "") + "\n" + (proc.stdout or "")
    times: list[float] = []
    for match in re.finditer(r"pts_time:([0-9]+(?:\.[0-9]+)?)", text):
        try:
            t = float(match.group(1))
        except ValueError:
            continue
        if t <= 0.01:
            continue
        if times and t - times[-1] < min_gap:
            continue
        times.append(t)
        if len(times) >= max_scenes - 1:
            break
    for t in times:
        scenes.append({"time": round(t, 3), "score": None})
    ok = proc.returncode == 0 or len(scenes) > 1
    return {"ok": ok, "reason": None if ok else "scene_detection_no_results", "duration": duration, "threshold": threshold, "min_gap": min_gap, "scenes": scenes, "tool": "ffmpeg:select(scene)"}


_SILENCE_START_RE = re.compile(r"silence_start:\s*([0-9]+(?:\.[0-9]+)?)")
_SILENCE_END_RE = re.compile(r"silence_end:\s*([0-9]+(?:\.[0-9]+)?)")


def detect_silences(path: Path, *, noise_db: float = -35.0, min_duration: float = 0.45, padding: float = 0.12, max_ranges: int = 500) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    noise_db = max(-80.0, min(-10.0, float(noise_db)))
    min_duration = max(0.10, min(10.0, float(min_duration)))
    padding = max(0.0, min(1.0, float(padding)))
    max_ranges = max(1, min(5000, int(max_ranges)))
    probe = probe_media(path)
    duration = float(probe.get("duration") or 0.0)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"ok": False, "reason": "ffmpeg_not_available", "duration": duration, "ranges": [], "total_silence": 0.0, "tool": None}
    cmd = [ffmpeg, "-hide_banner", "-nostats", "-i", str(path), "-af", f"silencedetect=noise={noise_db:.2f}dB:d={min_duration:.3f}", "-f", "null", "-"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "silence_detection_timeout", "duration": duration, "ranges": [], "total_silence": 0.0, "tool": "ffmpeg:silencedetect"}
    text = (proc.stderr or "") + "\n" + (proc.stdout or "")
    events: list[tuple[str, float]] = []
    for line in text.splitlines():
        sm = _SILENCE_START_RE.search(line)
        if sm:
            events.append(("start", float(sm.group(1))))
        em = _SILENCE_END_RE.search(line)
        if em:
            events.append(("end", float(em.group(1))))
    ranges: list[dict[str, float]] = []
    start: float | None = None
    for kind, value in events:
        if kind == "start":
            start = value
        elif kind == "end" and start is not None:
            raw_start, raw_end = start, value
            cut_start = max(0.0, raw_start + padding)
            cut_end = min(duration or raw_end, raw_end - padding)
            if cut_end - cut_start >= 0.05:
                ranges.append({"start": round(cut_start, 3), "end": round(cut_end, 3), "duration": round(cut_end-cut_start, 3), "raw_start": round(raw_start,3), "raw_end": round(raw_end,3)})
            start = None
            if len(ranges) >= max_ranges:
                break
    if start is not None and duration > start and len(ranges) < max_ranges:
        cut_start=max(0.0,start+padding); cut_end=max(cut_start, duration-padding)
        if cut_end-cut_start>=0.05:
            ranges.append({"start": round(cut_start,3), "end": round(cut_end,3), "duration": round(cut_end-cut_start,3), "raw_start": round(start,3), "raw_end": round(duration,3)})
    total = round(sum(r["duration"] for r in ranges), 3)
    return {"ok": proc.returncode == 0 or bool(events), "reason": None if (proc.returncode == 0 or events) else "silence_detection_no_results", "duration": duration, "noise_db": noise_db, "min_duration": min_duration, "padding": padding, "ranges": ranges, "total_silence": total, "estimated_duration_after": round(max(0.0, duration-total),3), "tool": "ffmpeg:silencedetect"}
