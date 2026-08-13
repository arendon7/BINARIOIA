from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse


def _query(raw: str) -> dict[str, str]:
    return {k: (v[-1] if v else "") for k, v in parse_qs(raw, keep_blank_values=True).items()}


def install(handler_cls, root, manifests_fn):
    """Additive compatibility layer for historical Hub contracts.

    R27 handlers remain authoritative. Only historical routes that the newer
    generic workspace/system routing would otherwise swallow are intercepted.
    All imports stay lazy so the Hub can boot before optional historical
    modules are exercised.
    """
    original_get = handler_cls.do_GET
    original_post = handler_cls.do_POST

    def legacy_get(self) -> bool:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = _query(parsed.query)

        if path == "/api/executive-workspaces":
            from common.executive_workspace import portfolio
            self._json(portfolio(include_archived=True)); return True
        if path == "/api/workspace/templates":
            from common.workspace_center import templates
            self._json(templates()); return True
        if path == "/api/context-contracts":
            from common.cross_app_context import registry, validate_registry
            self._json({"registry": registry(), "validation": validate_registry([a.get("id") for a in manifests_fn()])}); return True
        if path == "/api/context-compatibility":
            from common.cross_app_context import compatibility
            self._json(compatibility(str(query.get("from_app") or ""), str(query.get("to_app") or ""))); return True
        if path == "/api/handoff-context-review":
            from common.handoff_center import get
            from common.context_handoff import acceptance_review
            handoff = get(str(query.get("id") or ""))
            self._json(acceptance_review(handoff) if handoff else {"error": "Handoff no encontrado"}, 200 if handoff else 404); return True
        if path.startswith("/api/context-snapshots/"):
            from common.context_compiler import get_snapshot
            snap = get_snapshot(path.split("/api/context-snapshots/", 1)[1])
            self._json(snap or {"error": "Snapshot no encontrado"}, 200 if snap else 404); return True

        if path.startswith("/api/workspaces/"):
            parts = [x for x in path.split("/") if x]
            if len(parts) == 4 and parts[0] == "api" and parts[1] == "workspaces":
                wid, action = parts[2], parts[3]
                if action == "events":
                    from common.workspace_event_store import list_events
                    self._json({"schema": "sbia-workspace-events-1.0", "workspace_id": wid, "events": list_events(wid, limit=1000)}); return True
                if action == "timeline":
                    from common.workspace_event_store import list_events
                    self._json({"schema": "sbia-workspace-event-timeline-1.0", "workspace_id": wid, "events": list(reversed(list_events(wid, limit=1000)))}); return True
                if action == "inspector":
                    from common.workspace_event_store import inspector
                    self._json(inspector(wid)); return True
                if action == "graph":
                    from common.workspace_event_store import graph
                    try: limit = int(query.get("limit") or 300)
                    except Exception: limit = 300
                    self._json(graph(wid, app_id=query.get("app_id") or None, project_id=query.get("project_id") or None, event_type=query.get("event_type") or None, correlation_id=query.get("correlation_id") or None, limit=limit)); return True
                if action == "anomalies":
                    from common.workspace_event_store import anomalies
                    self._json(anomalies(wid)); return True
                if action == "integrity":
                    from common.workspace_event_store import integrity
                    self._json(integrity(wid)); return True
                if action == "adoption":
                    from common.adoption_center import summary, list_items, transitions
                    self._json({"summary": summary(wid), "items": list_items(wid, limit=1000), "transitions": transitions(workspace_id=wid, limit=1000)}); return True
                if action == "decision-center":
                    from common.approval_center import decision_center
                    self._json(decision_center(wid)); return True
                if action == "memory":
                    from common.project_memory import summary
                    self._json(summary(wid)); return True
                if action == "intelligence":
                    from common.project_intelligence import analyze
                    self._json(analyze(wid)); return True
                if action == "brief":
                    from common.project_intelligence import executive_brief
                    self._json(executive_brief(wid)); return True
                if action == "executive":
                    from common.executive_workspace import view
                    self._json(view(wid)); return True
                if action == "context-snapshots":
                    from common.context_compiler import snapshot_summary
                    self._json(snapshot_summary(wid)); return True
                if action == "context-lineage":
                    from common.context_lineage import stale_report
                    self._json(stale_report(wid, app_id=query.get("app_id") or None)); return True
                if action == "impact":
                    from common.impact_analysis import analyze
                    self._json(analyze(wid)); return True
                if action == "impact-queue":
                    from common.impact_analysis import queue
                    self._json(queue(wid, include_resolved=str(query.get("include_resolved") or "").lower() in {"1", "true", "yes"})); return True
                if action == "context-lineage-graph":
                    from common.context_lineage import graph
                    try: limit = int(query.get("limit") or 200)
                    except Exception: limit = 200
                    self._json(graph(wid, limit=limit)); return True
                if action == "context":
                    from common.context_compiler import compile_context
                    try: budget = int(query.get("budget_tokens") or 12000)
                    except Exception: budget = 12000
                    self._json(compile_context(wid, str(query.get("app_id") or ""), project_id=query.get("project_id") or None, budget_tokens=budget, persist=False)); return True
                if action == "handoff-preview":
                    from common.orchestrator import preview_handoff
                    try: budget = int(query.get("budget_tokens") or 12000)
                    except Exception: budget = 12000
                    self._json(preview_handoff(wid, str(query.get("from_app") or ""), str(query.get("to_app") or ""), budget_tokens=budget)); return True
        return False

    def do_GET(self):
        try:
            if legacy_get(self): return
        except Exception as exc:
            return self._json({"error": str(exc), "compatibility": "r23-r25"}, 500)
        return original_get(self)

    def do_POST(self):
        path = urlparse(self.path).path
        legacy_paths = {
            "/api/workspaces/adoption/propose",
            "/api/workspaces/adoption/transition",
            "/api/workspaces/adoption/bulk",
            "/api/workspaces/context/compile",
            "/api/workspaces/lineage/register",
            "/api/workspaces/impact/decide",
            "/api/workspaces/memory/create",
            "/api/workspaces/approvals/create",
            "/api/workspaces/approvals/decide",
            "/api/workflow-recovery/startup",
            "/api/workflow-runs/restore",
        }
        if path not in legacy_paths:
            return original_post(self)
        try:
            data = self._body()
            if path == "/api/workspaces/adoption/propose":
                from common.adoption_center import create
                return self._json(create(str(data.get("workspace_id") or ""), str(data.get("item_type") or "evidence"), str(data.get("title") or "Propuesta"), str(data.get("content") or ""), status=str(data.get("status") or "PROPOSED"), source_app=data.get("source_app"), source_entity_id=data.get("source_entity_id"), project_id=data.get("project_id"), evidence_ids=data.get("evidence_ids") if isinstance(data.get("evidence_ids"), list) else [], ref=data.get("ref"), confidence=data.get("confidence"), metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else {}, actor=str(data.get("actor") or "system"), reason=str(data.get("reason") or ""), idempotency_key=data.get("idempotency_key")))
            if path == "/api/workspaces/adoption/transition":
                from common.adoption_center import transition
                return self._json(transition(str(data.get("item_id") or ""), str(data.get("action") or ""), actor=str(data.get("actor") or "human"), reason=str(data.get("reason") or ""), supersedes_id=data.get("supersedes_id")))
            if path == "/api/workspaces/adoption/bulk":
                from common.adoption_center import bulk_transition
                return self._json(bulk_transition(data.get("item_ids") if isinstance(data.get("item_ids"), list) else [], str(data.get("action") or ""), actor=str(data.get("actor") or "human"), reason=str(data.get("reason") or "")))
            if path == "/api/workspaces/context/compile":
                from common.context_compiler import compile_context
                return self._json(compile_context(str(data.get("workspace_id") or ""), str(data.get("app_id") or ""), project_id=data.get("project_id"), budget_tokens=int(data.get("budget_tokens") or 12000), include_private=bool(data.get("include_private", False)), persist=bool(data.get("persist", True))))
            if path == "/api/workspaces/lineage/register":
                from common.context_lineage import register_output
                return self._json(register_output(str(data.get("workspace_id") or ""), str(data.get("title") or "Output"), output_type=str(data.get("output_type") or "artifact"), ref=data.get("ref"), app_id=data.get("app_id"), project_id=data.get("project_id"), run_id=data.get("run_id"), output_id=data.get("output_id"), context_snapshot_id=data.get("context_snapshot_id"), context_hash=data.get("context_hash"), metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else {}, idempotency_key=data.get("idempotency_key")))
            if path == "/api/workspaces/impact/decide":
                from common.impact_analysis import decide
                return self._json(decide(str(data.get("workspace_id") or ""), str(data.get("review_id") or ""), str(data.get("decision") or ""), actor=str(data.get("actor") or "human"), note=str(data.get("note") or "")))
            if path == "/api/workspaces/memory/create":
                from common.project_memory import create
                return self._json(create(str(data.get("workspace_id") or ""), str(data.get("memory_type") or "FACT"), str(data.get("title") or "Memoria"), str(data.get("content") or ""), status=str(data.get("status") or "PROPOSED"), scope=str(data.get("scope") or "WORKSPACE"), project_id=data.get("project_id"), source_app=data.get("source_app"), source_entity_id=data.get("source_entity_id"), evidence_ids=data.get("evidence_ids") if isinstance(data.get("evidence_ids"), list) else [], ref=data.get("ref"), confidence=data.get("confidence"), valid_from=data.get("valid_from"), valid_until=data.get("valid_until"), freshness_days=data.get("freshness_days"), source_quality=str(data.get("source_quality") or "UNVERIFIED"), semantic_key=data.get("semantic_key"), actor=str(data.get("actor") or "system"), reason=str(data.get("reason") or ""), idempotency_key=data.get("idempotency_key")))
            if path == "/api/workspaces/approvals/create":
                from common.approval_center import create
                return self._json(create(str(data.get("workspace_id") or ""), str(data.get("title") or "Aprobación requerida"), str(data.get("action_type") or "action"), entity_type=data.get("entity_type"), entity_id=data.get("entity_id"), project_id=data.get("project_id"), source_app=data.get("source_app"), risk_level=str(data.get("risk_level") or "R2"), details=data.get("details") if isinstance(data.get("details"), dict) else {}, required_role=str(data.get("required_role") or "project_owner")))
            if path == "/api/workspaces/approvals/decide":
                from common.approval_center import decide
                return self._json(decide(str(data.get("approval_id") or ""), str(data.get("action") or ""), actor=str(data.get("actor") or "human"), reason=str(data.get("reason") or "")))
            if path == "/api/workflow-recovery/startup":
                from common.workflow_checkpoint import startup_recovery
                return self._json(startup_recovery())
            if path == "/api/workflow-runs/restore":
                from common.workflow_composer import restore_run_from_checkpoint
                try: return self._json(restore_run_from_checkpoint(str(data.get("run_id") or "")))
                except FileNotFoundError as exc: return self._json({"error": str(exc)}, 404)
        except Exception as exc:
            return self._json({"error": str(exc), "compatibility": "r23-r25"}, 500)
        return original_post(self)

    handler_cls.do_GET = do_GET
    handler_cls.do_POST = do_POST
    return handler_cls
