from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "hub"


def _assembled_hub_server() -> str:
    return "".join((HUB / f"server.part{i:02d}.py.txt").read_text(encoding="utf-8") for i in range(1, 7))


def test_hub_source_is_complete_and_compiles():
    src = _assembled_hub_server()
    assert len(src.encode("utf-8")) >= 50_000
    compile(src, "hydrated-hub-server", "exec")


def test_app05_is_canonical_r27_video_and_keeps_project_identity():
    src = _assembled_hub_server()
    assert 'app["id"]=="05-editor-video-ia"' in src
    assert 'r26.r26_video_studio.server' in src
    assert 'project={quote' in src
    assert 'BINARIO_HUB_URL' in src
    assert 'mode=simple' not in src


def test_projects_ui_uses_same_window_for_video():
    html = (HUB / "ui" / "projects.html").read_text(encoding="utf-8")
    assert "project_id:p.id" in html
    assert "if(a.id==='05-editor-video-ia')location.href=r.url" in html


def test_hub_has_whisper_and_project_root_actions():
    src = _assembled_hub_server()
    assert '/api/whisper/status' in src
    assert '/api/whisper/job/start' in src
    assert '/api/projects/root' in src
    assert '/api/open-projects-root' in src
