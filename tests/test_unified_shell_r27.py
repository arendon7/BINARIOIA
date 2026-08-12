from __future__ import annotations
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_video_is_canonical_from_hub_and_same_window():
    server=(ROOT/"hub/server.py").read_text(encoding="utf-8")
    hub=(ROOT/"hub/ui/hub.html").read_text(encoding="utf-8")
    assert "r26.r26_video_studio.server" in server
    assert "project={quote" in server
    assert "mode=simple" not in server
    assert "if(a.id==='05-editor-video-ia')location.href=r.url" in hub


def test_simple_mode_is_persistent_outside_browser_origin(tmp_path,monkeypatch):
    monkeypatch.setenv("BINARIO_UI_PREFERENCES_FILE",str(tmp_path/"preferences.json"))
    from r26.r26_core.preferences import load_preferences,update_preferences
    assert load_preferences()["video_editing_mode"]=="simple"
    update_preferences({"video_editing_mode":"pro"})
    assert load_preferences()["video_editing_mode"]=="pro"


def test_legacy_project_bridge_creates_physical_project(tmp_path,monkeypatch):
    monkeypatch.setenv("BINARIO_PROJECTS_HOME",str(tmp_path/"Projects"))
    monkeypatch.setenv("BINARIO_PROJECTS_ROOT",str(tmp_path/"Projects"))
    from common.project_center import create
    from r26.r26_core.project_center import find_project
    row=create("Video desde Hub","05-editor-video-ia")
    physical=find_project(tmp_path/"Projects",row["id"])
    assert physical["id"]==row["id"]
    assert Path(physical["folders"]["assets"]).is_dir()
    assert Path(physical["folders"]["exports"]).is_dir()
