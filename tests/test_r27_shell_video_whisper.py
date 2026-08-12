from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def test_single_canonical_launcher_targets_hub():
    legacy = (ROOT / "ABRIR_BINARIO_IA.command").read_text(encoding="utf-8")
    canonical = (ROOT / "ABRIR_BINARIO_IA_R26.command").read_text(encoding="utf-8")
    assert 'ABRIR_BINARIO_IA_R26.command' in legacy
    assert '-m hub.server' in canonical
    assert 'r26_suite_launcher' not in canonical
    assert 'BINARIO_PROJECTS_HOME' in canonical


def test_hub_app05_uses_r26_video_studio():
    text = (ROOT / "hub/server.py").read_text(encoding="utf-8")
    assert 'app["id"]=="05-editor-video-ia"' in text
    assert 'r26.r26_video_studio.server' in text
    assert 'project={quote' in text
    assert 'mode=simple' not in text
    assert 'BINARIO_HUB_URL' in text


def test_hub_is_clear_entry_and_exposes_whisper_and_projects():
    text = (ROOT / "hub/ui/hub.html").read_text(encoding="utf-8")
    assert "¿Qué quieres hacer?" in text
    assert "Editar video" in text
    assert "Abrir o continuar un proyecto" in text
    assert "/api/whisper/status" in text
    assert "/api/projects/root" in text
    assert "Abrir en Finder" in text


def test_simple_mode_is_persistent_and_keeps_core_flow_visible():
    js = (ROOT / "r26/r26_video_studio/video-studio.js").read_text(encoding="utf-8")
    css = (ROOT / "r26/r26_video_studio/video-studio.css").read_text(encoding="utf-8")
    assert "binario_video_r26_editing_mode" in js
    assert "persistEditingMode" in js
    assert "Importar → Transcribir → Clips → Renderizar" in js
    assert ".simple-mode .advanced-card" in css
    assert ".simple-mode .transcript-card,.simple-mode .clipper-card{display:block}" in css
    assert ".simple-mode .transcript-card,.simple-mode .clipper-card{display:none}" not in css


def test_project_center_bridges_legacy_record_to_physical_r26_project():
    from common import project_center as legacy
    from r26.r26_core.project_center import list_projects as r26_list
    with tempfile.TemporaryDirectory(prefix="binario-r27-project-") as td:
        old_home = os.environ.get("BINARIO_PROJECTS_HOME"); old_root = os.environ.get("BINARIO_PROJECTS_ROOT")
        os.environ["BINARIO_PROJECTS_HOME"] = td; os.environ["BINARIO_PROJECTS_ROOT"] = td
        try:
            project = legacy.create("Proyecto Video", "05-editor-video-ia"); folder = Path(project["metadata"]["project_path"])
            assert folder.is_dir()
            for name in ("assets", "autosave", "exports", "training", "logs"): assert (folder / name).is_dir()
            rows = r26_list(Path(td)); assert [r["id"] for r in rows] == [project["id"]]; assert (folder / "project.json").is_file()
        finally:
            if old_home is None: os.environ.pop("BINARIO_PROJECTS_HOME", None)
            else: os.environ["BINARIO_PROJECTS_HOME"] = old_home
            if old_root is None: os.environ.pop("BINARIO_PROJECTS_ROOT", None)
            else: os.environ["BINARIO_PROJECTS_ROOT"] = old_root


def test_whisper_gateway_uses_isolated_native_worker_contract():
    from runtime import whisper_gateway as gateway
    fake = {"ok": True,"machine": "arm64","packages": {"faster-whisper": "1.2.1", "av": "14", "ctranslate2": "4"},"model_cached": True}
    with mock.patch.object(gateway, "runtime_python", return_value="/runtime/.venv/bin/python3"), mock.patch.object(gateway, "hardware_architecture", return_value="arm64"), mock.patch.object(gateway, "_run_worker", return_value=fake), mock.patch.object(gateway.sys, "platform", "darwin"):
        status = gateway.status("small")
    assert status["ready"] is True; assert status["architecture_ok"] is True; assert status["runtime_python"] == "/runtime/.venv/bin/python3"; assert status["policy"] == "single_native_runtime_worker_no_optional_binary_import_in_ui_process"


def test_video_transcription_keeps_fail_safe_historical_contract():
    from r26.r26_video_studio import transcription_adapter as adapter
    with mock.patch.object(adapter, "runtime_whisper_status", return_value={"ready": False, "available": False, "error": "not prepared"}): status = adapter.transcription_status()
    assert status["nonfatal"] is True; assert "editor_never_depends_on_transcription" in status["policy"]; assert "architecture-certified persistent runtime" in status["contract"]


def test_video_preferences_persist_outside_browser_origin(tmp_path, monkeypatch):
    pref = tmp_path / "preferences.json"; monkeypatch.setenv("BINARIO_UI_PREFERENCES_FILE", str(pref))
    from r26.r26_core.preferences import load_preferences, update_preferences
    assert load_preferences()["video_editing_mode"] == "simple"; saved = update_preferences({"video_editing_mode": "pro"}); assert saved["video_editing_mode"] == "pro"; assert load_preferences()["video_editing_mode"] == "pro"


def test_video_handoff_loads_requested_hub_project(tmp_path, monkeypatch):
    monkeypatch.setenv("BINARIO_PROJECTS_HOME", str(tmp_path / "Projects")); monkeypatch.setenv("BINARIO_PROJECTS_ROOT", str(tmp_path / "Projects"))
    from common.project_center import create
    from r26.r26_core.project_center import find_project
    row = create("Proyecto Hub Video", "05-editor-video-ia"); physical = find_project(tmp_path / "Projects", row["id"])
    assert physical["id"] == row["id"]; assert physical["name"] == "Proyecto Hub Video"
    js = (ROOT / "r26/r26_video_studio/video-studio.js").read_text(encoding="utf-8"); server = (ROOT / "r26/r26_video_studio/server.py").read_text(encoding="utf-8")
    assert "attachRequestedProject" in js; assert "/api/project/load" in js; assert 'route == "/api/project/load"' in server; assert '"requested_project_id"' in server


def test_video_primary_navigation_stays_in_same_window():
    hub = (ROOT / "hub/ui/hub.html").read_text(encoding="utf-8"); projects = (ROOT / "hub/ui/projects.html").read_text(encoding="utf-8")
    assert "if(a.id==='05-editor-video-ia')location.href=r.url" in hub; assert "if(a.id==='05-editor-video-ia')location.href=r.url" in projects


def test_legacy_projects_are_migrated_to_physical_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("BINARIO_PROJECTS_HOME", str(tmp_path / "Projects")); from common import project_center
    root = tmp_path / "Projects"; root.mkdir(parents=True)
    legacy = {"schema": "sbia-project-2.0", "id": "prj-legacy001", "name": "Proyecto heredado", "app_id": "05-editor-video-ia", "status": "active", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z", "metadata": {}, "artifacts": [], "sources": [], "notes": [], "run_ids": [], "handoff_ids": []}
    (root / "prj-legacy001.json").write_text(__import__('json').dumps(legacy), encoding="utf-8"); result = project_center.repair_existing_projects()
    assert result["ok"] and result["repaired"] == ["prj-legacy001"]; row = project_center.get("prj-legacy001"); physical = __import__('pathlib').Path(row["metadata"]["project_path"])
    assert (physical / "project.json").is_file(); assert all((physical / d).is_dir() for d in ("assets","autosave","exports","training","logs"))


def test_whisper_missing_model_prepares_without_reinstalling_runtime(tmp_path):
    from runtime import whisper_gateway as gateway
    missing_model = {"ok": True, "machine": "arm64", "model_cached": False, "packages": {"faster-whisper": "1.2.1"}}; prepared = {"ok": True, "machine": "arm64", "model_cached": True, "prepared": True, "model": "small"}; calls = []
    def worker(action, **kwargs): calls.append(action); return prepared if action == "prepare" else missing_model
    with mock.patch.object(gateway, "runtime_python", return_value="/runtime/.venv/bin/python3"), mock.patch.object(gateway, "hardware_architecture", return_value="arm64"), mock.patch.object(gateway, "_run_worker", side_effect=worker), mock.patch.object(gateway.sys, "platform", "darwin"), mock.patch.object(gateway, "repair") as repair:
        result = gateway.prepare("small")
    assert result["ok"] is True; assert "prepare" in calls; repair.assert_not_called()


def test_macos_whisper_never_falls_back_to_ui_python(monkeypatch):
    from runtime import whisper_gateway as gateway
    monkeypatch.delenv('BINARIO_WHISPER_PYTHON',raising=False)
    with mock.patch.object(gateway,'_active_runtime_python',return_value=None), mock.patch.object(gateway,'_dedicated_runtime_python',return_value=None), mock.patch.object(gateway.sys,'platform','darwin'):
        assert gateway.runtime_python() is None; state=gateway.status('small')
    assert state['mode']=='runtime_missing'; assert state['runtime_python'] is None; assert 'never_ui_python' in state['runtime_policy']


def test_whisper_repair_bootstraps_dedicated_runtime_instead_of_installing_into_ui():
    from runtime import whisper_gateway as gateway
    import types
    prepared={'ok':True,'prepared':True,'model':'small'}; pip_ok=types.SimpleNamespace(returncode=0,stdout='',stderr='')
    with mock.patch.object(gateway,'runtime_python',return_value=None), mock.patch.object(gateway,'bootstrap_dedicated_runtime',return_value={'ok':True,'python':'/dedicated/.venv/bin/python3','created':True}), mock.patch.object(gateway.subprocess,'run',return_value=pip_ok) as run, mock.patch.object(gateway,'_run_worker',return_value=prepared), mock.patch.object(gateway,'status',return_value={'ready':True,'runtime_ok':True,'model_cached':True}):
        result=gateway.repair('small')
    assert result['ok'] is True; assert run.call_args.args[0][0]=='/dedicated/.venv/bin/python3'; assert run.call_args.args[0][0] != gateway.sys.executable


def test_whisper_macos_self_test_transcribes_system_voice(tmp_path):
    from runtime import whisper_gateway as gateway
    import types
    def fake_say(argv,**kwargs): Path(argv[argv.index('-o')+1]).write_bytes(b'aiff'); return types.SimpleNamespace(returncode=0,stdout='',stderr='')
    with mock.patch.object(gateway.sys,'platform','darwin'), mock.patch.object(gateway,'prepare',return_value={'ok':True}), mock.patch.object(gateway.subprocess,'run',side_effect=fake_say), mock.patch.object(gateway,'transcribe',return_value=[{'start':0,'end':1,'text':'Prueba de transcripción de Binario IA'}]), mock.patch.object(gateway,'status',return_value={'ready':True}):
        result=gateway.self_test('small')
    assert result['ok'] is True; assert 'Prueba de transcripción' in result['transcript']
