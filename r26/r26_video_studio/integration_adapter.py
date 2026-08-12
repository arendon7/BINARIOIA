from __future__ import annotations

from pathlib import Path
import json

EXPECTED_R25_VIDEO_HINTS = (
    "apps/05_editor_video_ia/video_editor_v2/editor_server.py",
    "apps/05_editor_video_ia/video_editor_v2/ffmpeg_compiler.py",
    "apps/05_editor_video_ia/video_editor_v2/audio_enhancement.py",
)


def inspect_target(root: Path) -> dict:
    root = root.resolve()
    hits = {}
    for rel in EXPECTED_R25_VIDEO_HINTS:
        matches = list(root.rglob(Path(rel).name))
        hits[rel] = [str(p.relative_to(root)) for p in matches[:10]]
    eligible = all(hits[k] for k in hits)
    return {"eligible": eligible, "root": str(root), "evidence": hits}


def write_overlay_manifest(target_root: Path, output: Path) -> dict:
    report = inspect_target(target_root)
    manifest = {
        "overlay": "R26 Video Studio Timeline",
        "mode": "non_destructive",
        "target": report,
        "rules": [
            "Never delete or replace R25 ffmpeg/audio/reframe engines.",
            "Add R26 project/timeline schema alongside existing engine.",
            "Map key-idea/lower-third overlays to key_ideas track and disable by default.",
            "Expose asset deletion as an explicit cascading operation with confirmation.",
            "Render through existing R25 compiler after translating R26 render plan.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
