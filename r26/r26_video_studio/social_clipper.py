from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass, asdict
from typing import Any

from .transcript import TranscriptSegment, normalize_segments

HOOK_WORDS = {"cómo", "porque", "por qué", "secreto", "error", "nunca", "mejor", "clave", "importante", "resultado", "aprende", "evita", "mira", "esto", "tres", "3", "cinco", "5"}


def _id() -> str:
    return f"clip_{uuid.uuid4().hex[:10]}"


@dataclass
class ClipCandidate:
    id: str
    start: float
    end: float
    duration: float
    score: float
    title: str
    hook: str
    reason: list[str]
    segment_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _score(text: str, duration: float, target: float) -> tuple[float, list[str]]:
    low = text.lower()
    score = 0.0
    reasons: list[str] = []
    found = [w for w in HOOK_WORDS if w in low]
    if found:
        score += min(2.0, 0.5 + 0.25 * len(found))
        reasons.append("hook verbal")
    if "?" in text:
        score += 0.55
        reasons.append("pregunta")
    if re.search(r"\b\d+\b", text):
        score += 0.45
        reasons.append("dato/lista")
    word_count = len(re.findall(r"\w+", text))
    density = word_count / max(duration, 1.0)
    if 1.8 <= density <= 3.8:
        score += 0.5
        reasons.append("ritmo verbal")
    score += max(0.0, 1.0 - abs(duration - target) / max(target, 1))
    if 18 <= duration <= 55:
        score += 0.45
        reasons.append("duración social")
    return round(score, 4), reasons or ["continuidad narrativa"]


def generate_candidates(rows: list[dict[str, Any]] | list[TranscriptSegment], *, target_seconds: float = 35.0, min_seconds: float = 15.0, max_seconds: float = 60.0, limit: int = 8) -> list[ClipCandidate]:
    segments = rows if rows and isinstance(rows[0], TranscriptSegment) else normalize_segments(rows)  # type: ignore[index,arg-type]
    if not segments:
        return []
    target_seconds = max(min_seconds, min(max_seconds, float(target_seconds)))
    candidates: list[ClipCandidate] = []
    for start_idx, first in enumerate(segments):
        words: list[str] = []
        ids: list[str] = []
        for seg in segments[start_idx:]:
            if seg.start - first.start > max_seconds + 5:
                break
            words.append(seg.text)
            ids.append(seg.id)
            duration = seg.end - first.start
            if duration < min_seconds:
                continue
            if duration > max_seconds:
                break
            text = " ".join(words).strip()
            score, reasons = _score(text, duration, target_seconds)
            hook = re.split(r"(?<=[.!?])\s+", text)[0][:160]
            title = re.sub(r"\s+", " ", hook).strip(" .")[:72] or "Clip candidato"
            candidates.append(ClipCandidate(_id(), first.start, seg.end, duration, score, title, hook, reasons, list(ids)))
            if duration >= target_seconds:
                break
    ordered = sorted(candidates, key=lambda c: (-c.score, abs(c.duration - target_seconds), c.start))
    selected: list[ClipCandidate] = []
    for c in ordered:
        if any(abs(c.start - x.start) < 5 and abs(c.end - x.end) < 8 for x in selected):
            continue
        selected.append(c)
        if len(selected) >= max(1, min(30, int(limit))):
            break
    return selected
