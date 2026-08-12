from __future__ import annotations
from collections import defaultdict
from .models import TranscriptSegment
from .scoring import segment_score

def take_quality_score(seg: TranscriptSegment) -> float:
    technical = (
        0.30 * max(0.0, min(1.0, seg.visual_quality))
        + 0.32 * max(0.0, min(1.0, seg.audio_quality))
        + 0.20 * max(0.0, min(1.0, seg.stability))
        + 0.18 * max(0.0, min(1.0, seg.face_presence))
    )
    return 0.58 * segment_score(seg) + 0.42 * technical

def choose_best_takes(rows: list[TranscriptSegment]) -> tuple[list[TranscriptSegment], dict]:
    """Keep one candidate per explicit take_group; ungrouped segments remain untouched."""
    grouped = defaultdict(list)
    ungrouped = []
    for seg in rows:
        if seg.take_group:
            grouped[seg.take_group].append(seg)
        else:
            ungrouped.append(seg)

    chosen = list(ungrouped)
    decisions = []
    for group, candidates in grouped.items():
        best = max(candidates, key=take_quality_score)
        chosen.append(best)
        decisions.append({
            "take_group": group,
            "selected": best.id,
            "selected_source": best.source_id,
            "score": round(take_quality_score(best), 4),
            "alternatives": [
                {"id": c.id, "source_id": c.source_id, "score": round(take_quality_score(c), 4)}
                for c in sorted(candidates, key=take_quality_score, reverse=True)
                if c.id != best.id
            ],
        })
    return chosen, {"groups": len(grouped), "decisions": decisions}
