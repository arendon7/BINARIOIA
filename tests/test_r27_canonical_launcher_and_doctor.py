from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_launcher_is_hub_first_and_reuses_existing_service():
    src = (ROOT / "scripts" / "launch_binario.py").read_text(encoding="utf-8")
    compile(src, "launch_binario", "exec")
    for token in [
        "binario-r27-hub", "hub_identity", "choose_port", "BINARIO_HUB_URL",
        "Documents", "Binario IA", "Projects", "hub.server", "reused",
    ]:
        assert token in src, token
    assert "video_editor_v2.editor_server" not in src
    assert "r26_suite_launcher" not in src


def test_launcher_requires_canonical_hub_before_starting():
    src = (ROOT / "scripts" / "launch_binario.py").read_text(encoding="utf-8")
    assert 'root / "hub" / "server.py"' in src
    assert "La instalación no contiene el Hub canónico" in src


def test_whisper_doctor_reports_architecture_runtime_model_and_selftest():
    src = (ROOT / "scripts" / "doctor_whisper.py").read_text(encoding="utf-8")
    compile(src, "doctor_whisper", "exec")
    for token in [
        "hardware_arch", "runtime_machine", "architecture_ok", "runtime_python",
        "runtime_ok", "model_cached", "ffmpeg", "ffprobe", "say", "self_test",
        "runtime_architecture_mismatch", "model_not_prepared",
    ]:
        assert token in src, token


def test_release_is_still_blocked_until_mac_uat():
    assert (ROOT / ".release-blocked").is_file()
