from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from .models import ProjectSpec, EditMode, TimelinePlan
from .planner import build_timeline

@dataclass
class MontageVariant:
    id: str
    label: str
    rationale: str
    plan: TimelinePlan


def _dynamic_project(project: ProjectSpec) -> ProjectSpec:
    p = deepcopy(project)
    p.edit.pace = "dynamic"
    p.edit.min_natural_score = max(p.edit.min_natural_score, 0.56)
    boosts = {
        "hook": 0.14, "main_idea": 0.12, "evidence": 0.10,
        "cta": 0.12, "closing": 0.06, "argument": 0.06,
        "context": -0.10, "transition": -0.18, "example": -0.04,
    }
    for s in p.transcript:
        s.relevance = max(0.0, min(1.0, s.relevance + boosts.get(s.role, 0.0)))
        if s.role in {"transition", "context"} and not s.must_keep:
            s.redundancy = min(1.0, s.redundancy + 0.10)
    if p.edit.mode == EditMode.NATURAL:
        p.edit.preserve_all_meaningful_content = False
    return p


def create_montage_variants(project: ProjectSpec) -> list[MontageVariant]:
    balanced = build_timeline(deepcopy(project))
    dynamic = build_timeline(_dynamic_project(project))
    return [
        MontageVariant(id="A", label="Equilibrado", rationale="Conserva la estructura narrativa propuesta y prioriza continuidad y claridad.", plan=balanced),
        MontageVariant(id="B", label="Dinámico", rationale="Prioriza hook, idea central, evidencia y CTA; reduce contexto y transiciones de menor valor.", plan=dynamic),
    ]


def variants_summary(project: ProjectSpec) -> list[dict]:
    out = []
    for v in create_montage_variants(project):
        out.append({"id": v.id,"label": v.label,"rationale": v.rationale,"duration": round(v.plan.actual_duration, 3),"cuts": len(v.plan.cuts),"within_tolerance": v.plan.within_tolerance,"roles": [c.role for c in v.plan.cuts]})
    return out
