from __future__ import annotations
from dataclasses import dataclass, asdict
from .models import TimelinePlan

@dataclass
class StoryNode:
    index: int
    role: str
    start: float
    end: float
    duration: float
    text: str
    cut_ids: list[str]
    score: float


def build_story_map(plan: TimelinePlan) -> dict:
    nodes: list[StoryNode] = []
    for cut in plan.cuts:
        if nodes and nodes[-1].role == cut.role and abs(nodes[-1].end - cut.timeline_start) < 0.05:
            prev = nodes[-1]
            prev.end = cut.timeline_end
            prev.duration = prev.end - prev.start
            prev.text = (prev.text + " " + cut.text).strip()
            prev.cut_ids.append(cut.id)
            prev.score = round((prev.score + cut.score) / 2, 4)
        else:
            nodes.append(StoryNode(
                index=len(nodes) + 1,
                role=cut.role,
                start=cut.timeline_start,
                end=cut.timeline_end,
                duration=cut.duration,
                text=cut.text,
                cut_ids=[cut.id],
                score=round(cut.score, 4),
            ))
    roles = [n.role for n in nodes]
    return {
        "nodes": [asdict(n) for n in nodes],
        "roles": roles,
        "duration": plan.actual_duration,
        "has_hook": "hook" in roles,
        "has_cta": "cta" in roles,
        "has_closing": "closing" in roles,
        "narrative_density": round(len(nodes) / max(plan.actual_duration, 1.0), 4),
    }
