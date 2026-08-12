from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_hub_loads_r27_visual_layer():
    html = (ROOT / "hub" / "ui" / "hub.html").read_text(encoding="utf-8")
    assert 'href="/assets/style.css"' in html
    assert 'href="/assets/r27.css"' in html
    css = (ROOT / "hub" / "ui" / "assets" / "r27.css").read_text(encoding="utf-8")
    for token in (".start-grid", ".start-card", ".save-location", ".recent-projects", ".home-health-list"):
        assert token in css


def test_home_has_one_primary_video_entry_and_projects_entry():
    html = (ROOT / "hub" / "ui" / "hub.html").read_text(encoding="utf-8")
    assert "¿Qué quieres hacer?" in html
    assert "Editar video" in html
    assert "Abrir o continuar un proyecto" in html
    assert "Ver las 12 Apps" in html
    assert "Dónde queda tu trabajo" in html


def test_whisper_self_test_is_exposed_without_terminal():
    html = (ROOT / "hub" / "ui" / "hub.html").read_text(encoding="utf-8")
    assert "Probar Whisper" in html
    assert "self-test" in html
    assert "/api/whisper/job/start" in html


def test_app05_is_marked_as_canonical_video_editor():
    html = (ROOT / "hub" / "ui" / "hub.html").read_text(encoding="utf-8")
    assert "EDITOR PRINCIPAL" in html
    assert "canonical-video" in html
    assert "Video Studio R26/R27" in html
