from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json, threading
from .models import TimelinePlan, TimelineCut, AssetSpec
from .timeline_editor import TimelineOperation, apply_operations, plan_hash


def plan_from_dict(data: dict) -> TimelinePlan:
    return TimelinePlan(
        mode=data["mode"],
        target_duration=data.get("target_duration"),
        actual_duration=float(data.get("actual_duration", 0)),
        recommended_min_duration=float(data.get("recommended_min_duration", 0)),
        within_tolerance=bool(data.get("within_tolerance", True)),
        cuts=[TimelineCut(**x) for x in data.get("cuts", [])],
        assets=[AssetSpec(**x) for x in data.get("assets", [])],
        warnings=list(data.get("warnings", [])),
        analysis=dict(data.get("analysis", {})),
    )

@dataclass
class SessionSnapshot:
    label: str
    created_at_utc: str
    plan: dict
    plan_hash: str

@dataclass
class EditorSession:
    original_plan: TimelinePlan
    current_plan: TimelinePlan
    max_history: int = 100
    undo_stack: list[SessionSnapshot] = field(default_factory=list)
    redo_stack: list[SessionSnapshot] = field(default_factory=list)
    revision: int = 0

    def __post_init__(self): self._lock = threading.RLock()
    @classmethod
    def create(cls, plan: TimelinePlan, max_history: int = 100) -> "EditorSession":
        original = plan_from_dict(plan.to_dict()); current = plan_from_dict(plan.to_dict()); return cls(original_plan=original, current_plan=current, max_history=max_history)
    def _snapshot(self, label: str) -> SessionSnapshot:
        return SessionSnapshot(label=label,created_at_utc=datetime.now(timezone.utc).isoformat(),plan=self.current_plan.to_dict(),plan_hash=plan_hash(self.current_plan))
    def apply(self, operation: TimelineOperation, label: str | None = None) -> TimelinePlan:
        with self._lock:
            self.undo_stack.append(self._snapshot(label or operation.op)); self.undo_stack=self.undo_stack[-self.max_history:]; self.redo_stack.clear(); self.current_plan=apply_operations(self.current_plan,[operation]); self.revision+=1; return self.current_plan
    def apply_many(self, operations: list[TimelineOperation], label: str = "batch") -> TimelinePlan:
        with self._lock:
            if not operations: return self.current_plan
            self.undo_stack.append(self._snapshot(label)); self.undo_stack=self.undo_stack[-self.max_history:]; self.redo_stack.clear(); self.current_plan=apply_operations(self.current_plan,operations); self.revision+=1; return self.current_plan
    def undo(self) -> TimelinePlan:
        with self._lock:
            if not self.undo_stack: return self.current_plan
            self.redo_stack.append(self._snapshot("redo")); snap=self.undo_stack.pop(); self.current_plan=plan_from_dict(snap.plan); self.revision+=1; return self.current_plan
    def redo(self) -> TimelinePlan:
        with self._lock:
            if not self.redo_stack: return self.current_plan
            self.undo_stack.append(self._snapshot("undo")); snap=self.redo_stack.pop(); self.current_plan=plan_from_dict(snap.plan); self.revision+=1; return self.current_plan
    def reset(self) -> TimelinePlan:
        with self._lock:
            self.undo_stack.append(self._snapshot("before_reset")); self.redo_stack.clear(); self.current_plan=plan_from_dict(self.original_plan.to_dict()); self.revision+=1; return self.current_plan
    def state(self) -> dict:
        with self._lock:
            return {"schema":1,"revision":self.revision,"plan_hash":plan_hash(self.current_plan),"can_undo":bool(self.undo_stack),"can_redo":bool(self.redo_stack),"undo_depth":len(self.undo_stack),"redo_depth":len(self.redo_stack),"plan":self.current_plan.to_dict()}
    def save(self, output_path: str | Path) -> Path:
        out=Path(output_path); out.parent.mkdir(parents=True,exist_ok=True); payload=self.state(); payload["saved_at_utc"]=datetime.now(timezone.utc).isoformat(); out.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8"); return out
    @classmethod
    def load(cls, path: str | Path, original_plan: TimelinePlan | None = None) -> "EditorSession":
        data=json.loads(Path(path).read_text(encoding="utf-8")); current=plan_from_dict(data["plan"]); original=plan_from_dict(original_plan.to_dict()) if original_plan else plan_from_dict(data["plan"]); obj=cls(original_plan=original,current_plan=current); obj.revision=int(data.get("revision",0)); return obj
