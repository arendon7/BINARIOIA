from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, asdict
from typing import Any

_TIME_RE = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})(?:[,.](\d{1,3}))?")


def _id() -> str:
    return f"seg_{uuid.uuid4().hex[:10]}"


def _seconds(value: str) -> float:
    m = _TIME_RE.search(value.strip())
    if not m:
        raise ValueError(f"invalid timestamp: {value}")
    h = int(m.group(1) or 0)
    minute = int(m.group(2))
    sec = int(m.group(3))
    ms = int((m.group(4) or "0").ljust(3, "0")[:3])
    return h * 3600 + minute * 60 + sec + ms / 1000.0


@dataclass
class TranscriptSegment:
    id: str
    start: float
    end: float
    text: str
    speaker: str | None = None
    confidence: float | None = None

    def validate(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise ValueError("invalid transcript timing")
        if not self.text.strip():
            raise ValueError("empty transcript text")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("invalid transcript confidence")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_segments(rows: list[dict[str, Any]]) -> list[TranscriptSegment]:
    out: list[TranscriptSegment] = []
    for row in rows:
        seg = TranscriptSegment(
            id=str(row.get("id") or _id()),
            start=float(row.get("start", 0)),
            end=float(row.get("end", 0)),
            text=str(row.get("text", "")).strip(),
            speaker=(str(row["speaker"]).strip() if row.get("speaker") else None),
            confidence=(float(row["confidence"]) if row.get("confidence") is not None else None),
        )
        seg.validate()
        out.append(seg)
    out.sort(key=lambda x: (x.start, x.end, x.id))
    return out


def parse_srt(text: str) -> list[TranscriptSegment]:
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip())
    rows: list[dict[str, Any]] = []
    for block in blocks:
        lines = [line.rstrip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        timing_index = 0 if "-->" in lines[0] else 1
        if len(lines) <= timing_index or "-->" not in lines[timing_index]:
            continue
        left, right = lines[timing_index].split("-->", 1)
        body = " ".join(lines[timing_index + 1:]).strip()
        if not body:
            continue
        rows.append({"start": _seconds(left), "end": _seconds(right), "text": body})
    return normalize_segments(rows)


def parse_vtt(text: str) -> list[TranscriptSegment]:
    clean = re.sub(r"^WEBVTT[^\n]*\n", "", text.strip(), flags=re.I)
    return parse_srt(clean)
