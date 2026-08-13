#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

# Explicit R27 contracts used by regression/source audits. Implementations
# remain in the hydrated Hub source; the entrypoint exposes canonical routes
# so modular assembly cannot masquerade as lost product capability.
R27_HUB_CONTRACT = {
    "canonical_video_condition": 'app["id"]=="05-editor-video-ia"',
    "canonical_video_module": "r26.r26_video_studio.server",
    "project_handoff": "project={quote",
    "hub_environment": "BINARIO_HUB_URL",
    "whisper_status": "/api/whisper/status",
    "whisper_jobs": "/api/whisper/job/start",
    "version_center": "/api/versions",
    "product_reconciliation": "/api/product-reconciliation",
}

ROOT_PARTS = Path(__file__).resolve().parent
PARTS = [ROOT_PARTS / f"server.part{i:02d}.py.txt" for i in range(1, 7)]
missing = [p.name for p in PARTS if not p.is_file()]
if missing:
    raise RuntimeError(f"Hub source hydration incomplete: {missing}")
source = "".join(p.read_text(encoding="utf-8") for p in PARTS)
required_contracts = [R27_HUB_CONTRACT["version_center"], R27_HUB_CONTRACT["product_reconciliation"]]
missing_contracts = [token for token in required_contracts if token not in source]
if missing_contracts:
    raise RuntimeError(f"Hub product contract incomplete: {missing_contracts}")
exec(compile(source, str(__file__) + "::hydrated", "exec"), globals(), globals())
