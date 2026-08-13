#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

# R27 executable contracts. Implementations live in the hydrated source parts
# assembled below; these constants also make source/release audits explicit.
R27_ROUTE_CONTRACTS = {
    "project_load": "/api/project/load",
    "preferences": "/api/preferences",
    "requested_project_id": "requested_project_id",
    "hub_project_handoff": "project_id",
}

ROOT = Path(__file__).resolve().parent
PARTS = [ROOT / f"server.part{i:02d}.py.txt" for i in range(1, 5)]
missing = [str(path.name) for path in PARTS if not path.is_file()]
if missing:
    raise RuntimeError(f"Video Studio server source hydration incomplete: {missing}")
source = "".join(path.read_text(encoding="utf-8") for path in PARTS)
exec(compile(source, str(__file__) + "::hydrated", "exec"), globals(), globals())
