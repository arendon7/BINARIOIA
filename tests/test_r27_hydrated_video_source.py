from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "r26" / "r26_video_studio"


def _assembled_js() -> str:
    names = [
        "video-studio.part01.js.txt", "video-studio.part02.js.txt", "video-studio.part03.js.txt", "video-studio.part04.js.txt",
        "video-studio.part05.js.txt", "video-studio.part06.js.txt", "video-studio.part07a.js.txt", "video-studio.part07b.js.txt",
        "video-studio.part07c.js.txt", "video-studio.part08.js.txt",
    ]
    return "".join((VIDEO / name).read_text(encoding="utf-8") for name in names)


def _assembled_server() -> str:
    return "".join((VIDEO / f"server.part{i:02d}.py.txt").read_text(encoding="utf-8") for i in range(1, 5))


def test_video_ui_hydration_is_complete_and_deep():
    src = _assembled_js()
    assert len(src.encode("utf-8")) >= 89_000
    for token in [
        "persistEditingMode", "restoreEditingMode", "attachRequestedProject",
        "quickImportInput", "quickTranscribeBtn", "quickClipsBtn", "quickRenderBtn",
        "detectScenesPrimary", "detectSilencesPrimary", "applyRippleCuts",
        "generateClipCandidates", "renderAllClips", "createProxyById",
        "analyzeLoudnessById", "addAudioKeyframe", "applyColorPreset",
    ]:
        assert token in src, token


def test_simple_mode_keeps_transcription_and_clipper_visible():
    css = (VIDEO / "video-studio.part02.css").read_text(encoding="utf-8")
    assert ".simple-mode .advanced-card{display:none}" in css
    assert ".simple-mode .transcript-card,.simple-mode .clipper-card{display:block}" in css
    assert ".simple-mode .transcript-card,.simple-mode .clipper-card{display:none}" not in css


def test_video_server_hydration_compiles_and_contains_physical_project_contract():
    src = _assembled_server()
    compile(src, "hydrated-video-server", "exec")
    for token in [
        "/api/project/load", "requested_project_id", "/api/preferences",
        "/api/project/create", "/api/project/save", "/api/project/open-folder",
        "/api/transcript/transcribe", "/api/social-clips/candidates",
        "/api/render/start", "/api/render/batch",
    ]:
        assert token in src, token


def test_video_product_shell_is_not_a_light_replacement():
    html = (VIDEO / "index.html").read_text(encoding="utf-8")
    for token in [
        "Binario IA · Video Studio", "Flujo rápido", "Transcripción", "Social Clipper",
        "Audio profesional", "Rendimiento", "Silencios / ripple", "Acciones inteligentes",
        "timelineEditMode", "publishPresetSelect", "renderAllClipsBtn",
    ]:
        assert token in html, token
