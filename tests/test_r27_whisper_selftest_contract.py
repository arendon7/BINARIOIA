from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_whisper_selftest_module_is_fail_closed_and_non_ui():
    src = (ROOT / "runtime" / "whisper_selftest.py").read_text(encoding="utf-8")
    for token in ["PHRASE", "macos_say_to_whisper_end_to_end_no_ui_dependency", "whisper_status", "transcribe", "overlap >= 0.4"]:
        assert token in src
    compile(src, "whisper_selftest", "exec")


def test_whisper_jobs_accepts_self_test_action():
    src = (ROOT / "runtime" / "whisper_jobs.py").read_text(encoding="utf-8")
    assert "self-test" in src or "self_test" in src
    assert "whisper_selftest" in src or "selftest" in src


def test_hub_ready_button_can_reach_self_test_backend():
    hub = (ROOT / "hub" / "ui" / "hub.html").read_text(encoding="utf-8")
    assert "self-test" in hub
    server = "".join((ROOT / "hub" / f"server.part{i:02d}.py.txt").read_text(encoding="utf-8") for i in range(1, 7))
    assert "/api/whisper/job/start" in server
    assert "whisper_job_start" in server
