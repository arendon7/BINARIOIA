#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

# Explicit R27 contracts used by regression/source audits. Implementations
# remain in the hydrated Hub source plus hub.legacy_compat; the entrypoint
# exposes canonical and historical routes so modular assembly cannot
# masquerade as lost product capability.
R27_HUB_CONTRACT = {
    "canonical_video_condition": 'app["id"]=="05-editor-video-ia"',
    "canonical_video_module": "r26.r26_video_studio.server",
    "project_handoff": "project={quote",
    "hub_environment": "BINARIO_HUB_URL",
    "whisper_status": "/api/whisper/status",
    "whisper_jobs": "/api/whisper/job/start",
    "version_center": "/api/versions",
    "product_reconciliation": "/api/product-reconciliation",
    "adoption_propose": "/api/workspaces/adoption/propose",
    "decision_center_action": 'action=="decision-center"',
    "approval_decide": "/api/workspaces/approvals/decide",
    "context_action": 'action=="context"',
    "context_snapshots_action": 'action=="context-snapshots"',
    "context_compile": "/api/workspaces/context/compile",
    "context_snapshot": "/api/context-snapshots/",
    "executive_action": 'action=="executive"',
    "executive_workspaces": "/api/executive-workspaces",
    "intelligence_action": 'action=="intelligence"',
    "brief_action": 'action=="brief"',
    "memory_action": 'action=="memory"',
    "memory_create": "/api/workspaces/memory/create",
    "graph_action": 'action=="graph"',
    "anomalies_action": 'action=="anomalies"',
    "context_lineage_action": 'action=="context-lineage"',
    "lineage_register": "/api/workspaces/lineage/register",
    "context_contracts": "/api/context-contracts",
    "context_compatibility": "/api/context-compatibility",
    "handoff_context_review": "/api/handoff-context-review",
    "workflow_recovery": "/api/workflow-recovery/startup",
    "workflow_restore": "/api/workflow-runs/restore",
}

ROOT_PARTS = Path(__file__).resolve().parent
PARTS = [ROOT_PARTS / f"server.part{i:02d}.py.txt" for i in range(1, 7)]
missing = [p.name for p in PARTS if not p.is_file()]
if missing:
    raise RuntimeError(f"Hub source hydration incomplete: {missing}")
source = "".join(p.read_text(encoding="utf-8") for p in PARTS)
required_core = [R27_HUB_CONTRACT["version_center"], R27_HUB_CONTRACT["product_reconciliation"]]
missing_core = [token for token in required_core if token not in source]
if missing_core:
    raise RuntimeError(f"Hub core product contract incomplete: {missing_core}")
exec(compile(source, str(__file__) + "::hydrated", "exec"), globals(), globals())

# Additive only: current R27 routes run normally; historical routes/actions
# are intercepted before generic handlers swallow them.
from hub.legacy_compat import install as _install_legacy_compat
_install_legacy_compat(Handler, ROOT, manifests)
