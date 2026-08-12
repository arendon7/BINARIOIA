from __future__ import annotations
from unittest import mock


def test_native_worker_requires_matching_architecture_and_cached_model():
    from runtime import whisper_gateway as gateway
    fake={"ok":True,"machine":"arm64","model_cached":True,"packages":{"faster-whisper":"1.2.1","av":"14","ctranslate2":"4"}}
    with mock.patch.object(gateway,"runtime_python",return_value="/runtime/.venv/bin/python3"), mock.patch.object(gateway,"hardware_architecture",return_value="arm64"), mock.patch.object(gateway,"_run_worker",return_value=fake), mock.patch.object(gateway.sys,"platform","darwin"):
        state=gateway.status("small")
    assert state["runtime_ok"] is True
    assert state["model_cached"] is True
    assert state["ready"] is True
    assert state["runtime_machine"] == "arm64"


def test_missing_model_prepares_without_reinstalling_packages():
    from runtime import whisper_gateway as gateway
    missing={"ok":True,"machine":"arm64","model_cached":False,"packages":{"faster-whisper":"1.2.1"}}
    prepared={"ok":True,"machine":"arm64","model_cached":True,"prepared":True,"model":"small"}
    def worker(action,**kwargs):
        return prepared if action=="prepare" else missing
    with mock.patch.object(gateway,"runtime_python",return_value="/runtime/.venv/bin/python3"), mock.patch.object(gateway,"hardware_architecture",return_value="arm64"), mock.patch.object(gateway,"_run_worker",side_effect=worker), mock.patch.object(gateway.sys,"platform","darwin"), mock.patch.object(gateway,"repair") as repair:
        result=gateway.prepare("small")
    assert result["ok"] is True
    repair.assert_not_called()


def test_architecture_mismatch_never_reports_ready():
    from runtime import whisper_gateway as gateway
    fake={"ok":True,"machine":"x86_64","model_cached":True}
    with mock.patch.object(gateway,"runtime_python",return_value="/runtime/.venv/bin/python3"), mock.patch.object(gateway,"hardware_architecture",return_value="arm64"), mock.patch.object(gateway,"_run_worker",return_value=fake), mock.patch.object(gateway.sys,"platform","darwin"):
        state=gateway.status("small")
    assert state["architecture_ok"] is False
    assert state["runtime_ok"] is False
    assert state["ready"] is False
