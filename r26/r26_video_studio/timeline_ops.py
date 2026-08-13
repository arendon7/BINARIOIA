from __future__ import annotations

from copy import deepcopy
import uuid
from typing import Any

from .project_model import TimelineItem, VideoProject


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def normalize_ranges(rows: list[dict[str, Any]], duration: float) -> list[dict[str, float]]:
    parsed: list[dict[str, float]] = []
    for row in rows or []:
        try:
            start=max(0.0,min(float(duration),float(row.get("start",0))))
            end=max(0.0,min(float(duration),float(row.get("end",0))))
        except (TypeError,ValueError):
            continue
        if end-start >= .01:
            parsed.append({"start":start,"end":end})
    parsed.sort(key=lambda r:r["start"])
    merged: list[dict[str,float]]=[]
    for r in parsed:
        if merged and r["start"] <= merged[-1]["end"] + .001:
            merged[-1]["end"] = max(merged[-1]["end"],r["end"])
        else:
            merged.append(dict(r))
    return merged


def mapped_time(time: float, ranges: list[dict[str,float]]) -> float:
    shift=0.0
    for r in ranges:
        if time >= r["end"]:
            shift += r["end"]-r["start"]
        elif time > r["start"]:
            return max(0.0,r["start"]-shift)
        else:
            break
    return max(0.0,time-shift)


def _inside(time: float, ranges: list[dict[str,float]]) -> bool:
    return any(r["start"] <= time < r["end"] for r in ranges)


def _kept_intervals(start: float,end: float,ranges:list[dict[str,float]]) -> list[tuple[float,float]]:
    kept=[]; cursor=start
    for r in ranges:
        if r["end"] <= cursor or r["start"] >= end:
            continue
        if r["start"] > cursor:
            kept.append((cursor,min(r["start"],end)))
        cursor=max(cursor,r["end"])
        if cursor>=end:
            break
    if cursor<end:
        kept.append((cursor,end))
    return [(a,b) for a,b in kept if b-a>=.05]


def _split_item(item: TimelineItem,ranges:list[dict[str,float]]) -> list[TimelineItem]:
    pieces=[]
    for idx,(a,b) in enumerate(_kept_intervals(item.start,item.end,ranges)):
        clone=deepcopy(item)
        if idx:
            clone.id=_uid("item")
        clone.start=mapped_time(a,ranges)
        clone.duration=b-a
        clone.source_in=max(0.0,float(item.source_in)+(a-item.start))
        keyframes=[]
        for frame in item.keyframes or []:
            try: absolute=item.start+float(frame.get("time",0))
            except (TypeError,ValueError): continue
            if a <= absolute <= b:
                f=deepcopy(frame); f["time"]=round(absolute-a,3); keyframes.append(f)
        clone.keyframes=keyframes
        pieces.append(clone)
    return pieces


def apply_ripple(project: VideoProject, sequence_id: str, rows: list[dict[str,Any]]) -> dict[str,Any]:
    out=deepcopy(project)
    seq=out.sequence(sequence_id)
    old_duration=float(seq.duration)
    ranges=normalize_ranges(rows,old_duration)
    if not ranges:
        return {"project":out,"removed_seconds":0.0,"ranges":[],"items_before":sum(len(t.items) for t in seq.tracks),"items_after":sum(len(t.items) for t in seq.tracks)}
    items_before=sum(len(t.items) for t in seq.tracks)
    for track in seq.tracks:
        next_items=[]
        for item in track.items:
            next_items.extend(_split_item(item,ranges))
        track.items=next_items
    removed=sum(r["end"]-r["start"] for r in ranges)
    seq.duration=max(.1,old_duration-removed)
    seq.playhead=min(seq.duration,mapped_time(seq.playhead,ranges))
    if seq.kind == "long":
        transcript=(out.settings or {}).get("transcript") or {}
        segments=[]
        for row in transcript.get("segments") or []:
            try: start=float(row.get("start",0)); end=float(row.get("end",start+.1))
            except (TypeError,ValueError): continue
            for idx,(a,b) in enumerate(_kept_intervals(start,end,ranges)):
                clone=deepcopy(row)
                if idx: clone["id"]=_uid("seg")
                clone["start"]=round(mapped_time(a,ranges),3); clone["end"]=round(clone["start"]+(b-a),3)
                segments.append(clone)
        transcript["segments"]=segments; out.settings["transcript"]=transcript
        strip=(out.settings or {}).get("scene_strip") or {}
        strip["scenes"]=[{**sc,"time":round(mapped_time(float(sc.get("time",0)),ranges),3)} for sc in (strip.get("scenes") or []) if not _inside(float(sc.get("time",0)),ranges)]
        out.settings["scene_strip"]=strip
    cleanup=(out.settings or {}).get("silence_cleanup") or {}
    cleanup.update({"ranges":[],"total_silence":0.0,"analyzed":False,"last_applied_ranges":ranges,"last_removed_seconds":round(removed,3)})
    out.settings["silence_cleanup"]=cleanup
    out.validate()
    return {"project":out,"removed_seconds":round(removed,3),"ranges":ranges,"items_before":items_before,"items_after":sum(len(t.items) for t in seq.tracks)}


def _find_item(project: VideoProject, sequence_id: str, item_id: str):
    seq = project.sequence(sequence_id)
    for track in seq.tracks:
        for item in track.items:
            if item.id == item_id:
                return seq, track, item
    raise KeyError(item_id)


def magnet_points(project: VideoProject, sequence_id: str, *, exclude_item_id: str | None = None) -> list[float]:
    seq = project.sequence(sequence_id)
    points = {0.0, float(seq.duration)}
    for track in seq.tracks:
        for item in track.items:
            if item.id == exclude_item_id:
                continue
            points.add(round(float(item.start), 6))
            points.add(round(float(item.end), 6))
    if seq.kind == "long":
        strip = (project.settings or {}).get("scene_strip") or {}
        for row in strip.get("scenes") or []:
            try:
                points.add(round(float(row.get("time", 0)), 6))
            except (TypeError, ValueError):
                pass
    return sorted(x for x in points if 0 <= x <= seq.duration)


def snap_value(value: float, points: list[float], threshold: float = .18) -> tuple[float, float | None]:
    value = float(value)
    if not points:
        return value, None
    nearest = min(points, key=lambda x: abs(x - value))
    if abs(nearest - value) <= max(0.0, float(threshold)):
        return float(nearest), float(nearest)
    return value, None


def move_item(project: VideoProject, sequence_id: str, item_id: str, new_start: float, *, mode: str = "magnetic", threshold: float = .18, ripple_scope: str = "all") -> dict[str, Any]:
    if mode not in {"free", "magnetic", "ripple"}:
        raise ValueError("mode must be free, magnetic or ripple")
    if ripple_scope not in {"track", "all"}:
        raise ValueError("ripple_scope must be track or all")
    out = deepcopy(project)
    seq, selected_track, item = _find_item(out, sequence_id, item_id)
    if selected_track.locked:
        raise ValueError("track is locked")
    old_start = float(item.start)
    old_end = float(item.end)
    target = max(0.0, min(float(new_start), max(0.0, seq.duration - item.duration)))
    snapped_to = None
    if mode in {"magnetic", "ripple"}:
        points = magnet_points(out, sequence_id, exclude_item_id=item.id)
        start_candidate, start_snap = snap_value(target, points, threshold)
        end_candidate, end_snap = snap_value(target + item.duration, points, threshold)
        if start_snap is not None and (end_snap is None or abs(start_candidate-target) <= abs((end_candidate-item.duration)-target)):
            target, snapped_to = start_candidate, start_snap
        elif end_snap is not None:
            target, snapped_to = end_candidate - item.duration, end_snap
        target = max(0.0, min(target, max(0.0, seq.duration - item.duration)))
    delta = target - old_start
    item.start = target
    shifted = 0
    if mode == "ripple" and abs(delta) > 1e-9:
        tracks = seq.tracks if ripple_scope == "all" else [selected_track]
        for track in tracks:
            if track.locked and track is not selected_track:
                continue
            for other in track.items:
                if other.id == item.id:
                    continue
                if other.start >= old_end - 1e-6:
                    other.start = max(0.0, other.start + delta)
                    shifted += 1
        max_end = max((i.end for t in seq.tracks for i in t.items), default=seq.duration)
        seq.duration = max(.1, max(seq.duration + max(0.0, delta), max_end))
        if delta < 0:
            seq.duration = max(.1, max_end)
        if seq.kind == "long" and abs(delta) > 1e-9:
            transcript = (out.settings or {}).get("transcript") or {}
            for row in transcript.get("segments") or []:
                try:
                    if float(row.get("start", 0)) >= old_end - 1e-6:
                        row["start"] = max(0.0, float(row["start"]) + delta)
                        row["end"] = max(row["start"] + .01, float(row.get("end", row["start"] + .01)) + delta)
                except (TypeError, ValueError):
                    continue
            strip = (out.settings or {}).get("scene_strip") or {}
            for row in strip.get("scenes") or []:
                try:
                    if float(row.get("time", 0)) >= old_end - 1e-6:
                        row["time"] = max(0.0, float(row["time"]) + delta)
                except (TypeError, ValueError):
                    continue
    seq.playhead = max(0.0, min(seq.duration, item.start))
    out.validate()
    return {"project": out, "item_id": item.id, "old_start": round(old_start, 6), "new_start": round(item.start, 6), "delta": round(delta, 6), "snapped_to": snapped_to, "shifted_items": shifted, "mode": mode, "ripple_scope": ripple_scope}
