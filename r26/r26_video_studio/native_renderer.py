from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from .audio_pipeline import master_filter, normalize_audio_policy, voice_filter
from .acceleration import choose_h264_encoder
from .media_analysis import probe_media
from .project_model import TimelineItem, VideoProject


def _resolution(ratio: str, export_settings: dict[str, Any] | None = None) -> tuple[int, int]:
    settings = export_settings or {}
    resolution = settings.get("resolution")
    if isinstance(resolution, (list, tuple)) and len(resolution) == 2:
        try:
            w, h = int(resolution[0]), int(resolution[1])
            if 240 <= w <= 7680 and 240 <= h <= 7680:
                return (w // 2 * 2, h // 2 * 2)
        except (TypeError, ValueError):
            pass
    return {"9:16": (720, 1280), "1:1": (1080, 1080), "16:9": (1280, 720)}.get(ratio, (1280, 720))


def _has_audio(path: Path) -> bool:
    try:
        return any(x.get("codec_type") == "audio" for x in (probe_media(path).get("streams") or []))
    except Exception:
        return False


def _filter_escape(text: str) -> str:
    return str(text).replace("\\", r"\\").replace("'", r"\'").replace(":", r"\:").replace("%", r"\%")


def _drawtext_available(ffmpeg: str) -> bool:
    try:
        proc = subprocess.run([ffmpeg, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=5, check=False)
        return " drawtext " in (proc.stdout or "") or "drawtext" in (proc.stdout or "")
    except Exception:
        return False


def _color_filters(item: TimelineItem) -> list[str]:
    c = item.color or {}
    brightness = max(-1.0, min(1.0, float(c.get("brightness", 0.0))))
    contrast = max(0.0, min(3.0, float(c.get("contrast", 1.0))))
    saturation = max(0.0, min(4.0, float(c.get("saturation", 1.0))))
    gamma = max(0.1, min(5.0, float(c.get("gamma", 1.0))))
    temperature = max(-1.0, min(1.0, float(c.get("temperature", 0.0))))
    tint = max(-1.0, min(1.0, float(c.get("tint", 0.0))))
    out = []
    if any(abs(v-d) > 1e-6 for v,d in ((brightness,0),(contrast,1),(saturation,1),(gamma,1))):
        out.append(f"eq=brightness={brightness:.5f}:contrast={contrast:.5f}:saturation={saturation:.5f}:gamma={gamma:.5f}")
    if abs(temperature) > 1e-6 or abs(tint) > 1e-6:
        rs=max(-1.0,min(1.0,temperature*.18)); bs=-rs; gm=max(-1.0,min(1.0,-tint*.12))
        out.append(f"colorbalance=rs={rs:.5f}:bs={bs:.5f}:gm={gm:.5f}")
    return out


def _text_style(item: TimelineItem, track_kind: str, height: int) -> str:
    style = item.text_style or {}
    preset = style.get("preset", "clean_white")
    scale=max(.5,min(3.0,float(style.get("font_scale",1.0))))
    position=style.get("position", "bottom" if track_kind == "subtitles" else "top")
    base=max(22, int(height*(.035 if track_kind == "subtitles" else .04)*scale))
    if position == "top": y=int(height*.10)
    elif position == "middle": y="(h-text_h)/2"
    else: y=f"h-text_h-{int(height*.075)}"
    x="(w-text_w)/2"
    if preset == "bold_social":
        return f"fontcolor=white:fontsize={int(base*1.18)}:x={x}:y={y}:borderw=3:bordercolor=black@0.9:shadowx=2:shadowy=2:shadowcolor=black@0.6"
    if preset == "minimal":
        return f"fontcolor=white:fontsize={base}:x={x}:y={y}:shadowx=1:shadowy=1:shadowcolor=black@0.65"
    if preset == "boxed":
        return f"fontcolor=white:fontsize={base}:x={x}:y={y}:box=1:boxcolor=black@0.72:boxborderw=14"
    if preset == "brand_gold":
        return f"fontcolor=0xE4C36A:fontsize={base}:x={x}:y={y}:borderw=2:bordercolor=black@0.9:box=1:boxcolor=black@0.42:boxborderw=10"
    return f"fontcolor=white:fontsize={base}:x={x}:y={y}:box=1:boxcolor=black@0.48:boxborderw=12"


def _visual_filter(item: TimelineItem, idx: int, n: int, width: int, height: int) -> tuple[str, str]:
    t = item.transform or {}
    crop = t.get("crop") or {}
    left, right = float(crop.get("left", 0)), float(crop.get("right", 0))
    top, bottom = float(crop.get("top", 0)), float(crop.get("bottom", 0))
    scale = max(0.01, min(20.0, float(t.get("scale", 1.0))))
    target_w = max(2, int(width * scale) // 2 * 2)
    rotation = float(t.get("rotation", 0.0))
    opacity = max(0.0, min(1.0, float(item.opacity)))
    parts = [f"[{idx}:v]setpts=PTS-STARTPTS+{item.start:.6f}/TB"]
    if any(v > 0 for v in (left, right, top, bottom)):
        parts.append(f"crop=iw*{max(.01, 1-left-right):.6f}:ih*{max(.01, 1-top-bottom):.6f}:iw*{left:.6f}:ih*{top:.6f}")
    tin = item.transitions.get("in", {}) if isinstance(item.transitions, dict) else {}
    tout = item.transitions.get("out", {}) if isinstance(item.transitions, dict) else {}
    in_type = str(tin.get("type", "none")); out_type = str(tout.get("type", "none"))
    in_d = min(item.duration, max(0.0, float(tin.get("duration", 0) or 0)))
    out_d = min(item.duration, max(0.0, float(tout.get("duration", 0) or 0)))
    zoom_expr = "1"
    if in_type == "zoom" and in_d > 0:
        zoom_expr = f"(0.88+0.12*clip((t-{item.start:.6f})/{in_d:.6f},0,1))"
    if out_type == "zoom" and out_d > 0:
        start_out = item.end - out_d
        zoom_expr = f"if(gte(t,{start_out:.6f}),1+0.12*clip((t-{start_out:.6f})/{out_d:.6f},0,1),{zoom_expr})"
    if zoom_expr != "1":
        parts.append(f"scale=w='trunc(({target_w})*({zoom_expr})/2)*2':h=-2:force_original_aspect_ratio=decrease:eval=frame")
    else:
        parts.append(f"scale={target_w}:-2:force_original_aspect_ratio=decrease")
    parts.extend(_color_filters(item))
    parts.append("format=rgba")
    if abs(rotation) > 0.001:
        parts.append(f"rotate={rotation:.6f}*PI/180:ow=rotw(iw):oh=roth(ih):c=none")
    if in_type in {"fade", "dissolve", "zoom"} and in_d > 0:
        parts.append(f"fade=t=in:st=0:d={in_d:.6f}:alpha=1")
    if out_type in {"fade", "dissolve", "zoom"} and out_d > 0:
        parts.append(f"fade=t=out:st={max(0, item.duration-out_d):.6f}:d={out_d:.6f}:alpha=1")
    if opacity < .999:
        parts.append(f"colorchannelmixer=aa={opacity:.6f}")
    label = f"ov{n}"
    chain = ",".join(parts) + f"[{label}]"
    x = float(t.get("x", .5)); y = float(t.get("y", .5))
    base_x = f"W*{x:.6f}-w/2"
    base_y = f"H*{y:.6f}-h/2"
    x_expr, y_expr = base_x, base_y
    if in_d > 0 and in_type in {"slide_left", "slide_right"}:
        origin = "W" if in_type == "slide_left" else "-w"
        p = f"clip((t-{item.start:.6f})/{in_d:.6f},0,1)"
        x_expr = f"({origin})+(({base_x})-({origin}))*({p})"
    if out_d > 0 and out_type in {"slide_left", "slide_right"}:
        dest = "-w" if out_type == "slide_left" else "W"
        start_out = item.end - out_d
        p = f"clip((t-{start_out:.6f})/{out_d:.6f},0,1)"
        x_expr = f"if(gte(t,{start_out:.6f}),({base_x})+(({dest})-({base_x}))*({p}),({x_expr}))"
    return chain, f"x='{x_expr}':y='{y_expr}':enable='between(t,{item.start:.6f},{item.end:.6f})'"


def _volume_automation(item: TimelineItem) -> str:
    points: list[tuple[float, float]] = []
    for frame in item.keyframes or []:
        if "volume" not in frame:
            continue
        try:
            t = max(0.0, min(float(item.duration), float(frame.get("time", 0))))
            v = max(0.0, min(4.0, float(frame.get("volume"))))
        except (TypeError, ValueError):
            continue
        points.append((t, v))
    points.sort(key=lambda row: row[0])
    base = max(0.0, min(4.0, float(item.volume)))
    if not points:
        return f"{base:.6f}"
    if points[0][0] > 1e-6:
        points.insert(0, (0.0, base))
    dedup: list[tuple[float, float]] = []
    for row in points:
        if dedup and abs(row[0] - dedup[-1][0]) < 1e-6:
            dedup[-1] = row
        else:
            dedup.append(row)
    if len(dedup) == 1:
        return f"{dedup[0][1]:.6f}"
    expr = f"{dedup[-1][1]:.6f}"
    for (t0, v0), (t1, v1) in reversed(list(zip(dedup[:-1], dedup[1:]))):
        span = max(1e-6, t1 - t0)
        linear = f"({v0:.6f}+({v1-v0:.6f})*(t-{t0:.6f})/{span:.6f})"
        expr = f"if(lt(t,{t1:.6f}),{linear},{expr})"
    return expr


def render_native(project: VideoProject, sequence_id: str, assets_dir: Path, output_path: Path, *, progress: Callable[[float], None] | None = None) -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not available")
    project.validate()
    seq = project.sequence(sequence_id)
    export_settings = project.settings.get("export") or {}
    width, height = _resolution(seq.aspect_ratio, export_settings)
    fps = int(export_settings.get("fps", 30) or 30)
    fps = max(15, min(60, fps))
    duration = float(seq.duration)
    assets_dir = assets_dir.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd: list[str] = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-progress", "pipe:1", "-nostats"]
    cmd += ["-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:r={fps}:d={duration}"]
    cmd += ["-f", "lavfi", "-t", str(duration), "-i", "anullsrc=r=48000:cl=stereo"]
    specs: list[dict[str, Any]] = []
    asset_map = {a.id: a for a in project.assets}
    ordered_tracks = {"video": 0, "broll": 1, "images": 2, "key_ideas": 3, "subtitles": 4, "music": 5, "voiceover": 6}
    items = []
    for tr in seq.tracks:
        if not tr.enabled:
            continue
        for item in tr.items:
            if item.enabled:
                items.append((ordered_tracks.get(tr.kind, 99), tr, item))
    items.sort(key=lambda row: (row[0], row[2].start, row[2].z_index, row[2].id))
    input_idx = 2
    for _, tr, item in items:
        asset = asset_map.get(item.asset_id or "")
        if not asset:
            continue
        path = (assets_dir / Path(asset.name).name).resolve()
        if path.parent != assets_dir or not path.is_file():
            continue
        if asset.kind == "image":
            cmd += ["-loop", "1", "-t", str(item.duration), "-i", str(path)]
        else:
            if item.source_in > 0:
                cmd += ["-ss", f"{item.source_in:.6f}"]
            cmd += ["-t", f"{item.duration:.6f}", "-i", str(path)]
        specs.append({"idx": input_idx, "track": tr.kind, "track_muted": tr.muted, "item": item, "asset": asset, "path": path, "has_audio": asset.kind in {"video", "audio"} and _has_audio(path)})
        input_idx += 1
    filters: list[str] = ["[0:v]format=yuv420p[v0]"]
    vprev = "v0"
    visual_specs = [s for s in specs if s["asset"].kind in {"video", "image"} and s["track"] in {"video", "broll", "images"}]
    for n, spec in enumerate(visual_specs, 1):
        item: TimelineItem = spec["item"]
        chain, overlay_args = _visual_filter(item, spec["idx"], n, width, height)
        filters.append(chain)
        out = f"v{n}"
        filters.append(f"[{vprev}][ov{n}]overlay={overlay_args}:shortest=0[{out}]")
        vprev = out
    drawtext = _drawtext_available(ffmpeg)
    text_idx = 0
    if drawtext:
        for _, tr, item in items:
            if tr.kind not in {"subtitles", "key_ideas"} or not item.text:
                continue
            text_idx += 1
            out = f"vt{text_idx}"
            text = _filter_escape(item.text)
            style = _text_style(item, tr.kind, height)
            filters.append(f"[{vprev}]drawtext=text='{text}':{style}:enable='between(t,{item.start:.6f},{item.end:.6f})'[{out}]")
            vprev = out
    filters.append(f"[{vprev}]format=yuv420p[vout]")
    policy = normalize_audio_policy(project.settings.get("audio") or {})
    voices: list[str] = []; music: list[str] = []; ambience: list[str] = []; ai = 0
    for spec in specs:
        if not spec["has_audio"] or spec["track_muted"]:
            continue
        ai += 1
        item: TimelineItem = spec["item"]
        label = f"a{ai}"; delay = max(0, int(round(item.start * 1000))); volume_expr = _volume_automation(item)
        filters.append(f"[{spec['idx']}:a]atrim=0:{item.duration:.6f},asetpts=PTS-STARTPTS,volume='{volume_expr}':eval=frame,adelay={delay}:all=1[{label}]")
        if spec["track"] in {"video", "voiceover"}: voices.append(label)
        elif spec["track"] == "music": music.append(label)
        else: ambience.append(label)
    def mix(labels: list[str], out: str) -> str | None:
        if not labels: return None
        if len(labels) == 1: filters.append(f"[{labels[0]}]anull[{out}]")
        else:
            joined = "".join(f"[{x}]" for x in labels); filters.append(f"{joined}amix=inputs={len(labels)}:duration=longest:dropout_transition=0[{out}]")
        return out
    voice_bus = mix(voices, "voice0")
    if voice_bus:
        filters.append(f"[{voice_bus}]{voice_filter(policy)}[voice]"); voice_bus = "voice"
    music_bus = mix(music, "music0")
    if music_bus:
        filters.append(f"[{music_bus}]volume={policy['music_gain']:.6f}[music]"); music_bus = "music"
    ambience_bus = mix(ambience, "amb"); buses: list[str] = []
    if music_bus and voice_bus and policy["duck_music_under_voice"]:
        filters.append(f"[{music_bus}][{voice_bus}]sidechaincompress=threshold={policy['duck_threshold']}:ratio={policy['duck_ratio']}:attack={policy['duck_attack_ms']}:release={policy['duck_release_ms']}[musicduck]"); buses.extend([voice_bus, "musicduck"])
    else:
        if voice_bus: buses.append(voice_bus)
        if music_bus: buses.append(music_bus)
    if ambience_bus: buses.append(ambience_bus)
    if not buses: filters.append(f"[1:a]atrim=0:{duration:.6f}[amaster0]")
    elif len(buses) == 1: filters.append(f"[{buses[0]}]apad,atrim=0:{duration:.6f}[amaster0]")
    else:
        joined = "".join(f"[{x}]" for x in buses); filters.append(f"{joined}amix=inputs={len(buses)}:duration=longest:dropout_transition=0,apad,atrim=0:{duration:.6f}[amaster0]")
    filters.append(f"[amaster0]{master_filter(policy)}[aout]")
    quality = str(export_settings.get("quality_label", "Alta · H.264")); preset, crf = ("fast", "24") if "Rápida" in quality else (("slow", "18") if "Máxima" in quality else ("medium", "20"))
    encoder = choose_h264_encoder(export_settings); video_args = ["-c:v", encoder["encoder"]]
    if encoder["encoder"] == "h264_videotoolbox":
        bitrate = "4500k" if "Rápida" in quality else ("10000k" if "Máxima" in quality else "7000k"); video_args += ["-b:v", bitrate, "-maxrate", bitrate, "-bufsize", "14000k", "-realtime", "1"]
    else: video_args += ["-preset", preset, "-crf", crf]
    cmd += ["-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]", *video_args, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", str(duration), str(output_path)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    last_progress = 0.0
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.strip()
        if line.startswith("out_time_us="):
            try:
                seconds = int(line.split("=", 1)[1]) / 1_000_000.0; last_progress = max(last_progress, min(0.99, seconds / max(duration, .01)))
                if progress: progress(last_progress)
            except ValueError: pass
    stderr = proc.stderr.read() if proc.stderr else ""; code = proc.wait()
    if code != 0 or not output_path.is_file() or output_path.stat().st_size <= 0:
        raise RuntimeError((stderr or "native ffmpeg render failed")[-3000:])
    if progress: progress(1.0)
    return {"ok": True, "engine": "native_ffmpeg", "path": str(output_path), "size": output_path.stat().st_size, "resolution": [width, height], "fps": fps, "encoder": encoder["encoder"], "hardware_acceleration": encoder["encoder"] == "h264_videotoolbox", "text_rendered": drawtext, "warnings": [] if drawtext else ["drawtext_unavailable_text_layers_skipped"], "command_preview": cmd[:12] + ["…"]}
