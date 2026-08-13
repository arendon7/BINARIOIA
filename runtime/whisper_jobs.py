from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from runtime import whisper_selftest
from runtime.whisper_gateway import prepare, repair, status

_LOCK = threading.RLock()
_JOBS: dict[str, dict[str, Any]] = {}
_LATEST: str | None = None


def _public(job: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in job.items() if not k.startswith('_')}


def get(job_id: str | None = None) -> dict[str, Any]:
    with _LOCK:
        target = job_id or _LATEST
        if not target or target not in _JOBS:
            return {"ok": True, "status": "idle", "job_id": None, "progress": 0, "message": "Sin preparación en curso"}
        return _public(dict(_JOBS[target]))


def start(action: str = "prepare", model: str = "small") -> dict[str, Any]:
    global _LATEST
    action = str(action or "prepare").strip().lower()
    if action not in {"prepare", "repair", "self-test"}:
        raise ValueError("action must be prepare, repair or self-test")
    model = str(model or "small").strip() or "small"
    with _LOCK:
        if _LATEST and _LATEST in _JOBS and _JOBS[_LATEST].get("status") in {"queued", "running"}:
            return _public(dict(_JOBS[_LATEST]))
        job_id = f"whisper-{uuid.uuid4().hex[:12]}"
        now = time.time()
        queued_message = "Auto-prueba de Whisper en cola" if action == "self-test" else "Preparación de Whisper en cola"
        job = {"ok": True, "job_id": job_id, "action": action, "model": model, "status": "queued", "stage": "queued", "progress": 2, "message": queued_message, "started_at": now, "updated_at": now, "result": None, "error": None}
        _JOBS[job_id] = job
        _LATEST = job_id

    def run() -> None:
        def update(**patch: Any) -> None:
            with _LOCK:
                current = _JOBS.get(job_id)
                if not current:
                    return
                current.update(patch)
                current["updated_at"] = time.time()
        try:
            update(status="running", stage="probe", progress=10, message="Verificando runtime y arquitectura")
            before = status(model)
            if before.get("ready") and action == "prepare":
                update(status="done", stage="ready", progress=100, message="Whisper ya estaba listo", result={"ok": True, "status": before})
                return

            if action == "self-test":
                if not before.get("ready"):
                    update(stage="prepare", progress=30, message="Preparando Whisper antes de la auto-prueba")
                    prepared = prepare(model)
                    if not prepared.get("ok"):
                        update(
                            status="failed",
                            stage=str(prepared.get("stage") or "prepare"),
                            progress=100,
                            message="Whisper no pudo quedar listo para la auto-prueba",
                            result=prepared,
                            error=str(prepared.get("error") or prepared),
                        )
                        return
                update(stage="self-test", progress=60, message="Generando audio de prueba y transcribiendo")
                result = whisper_selftest.run(model)
                success_message = "Auto-prueba Whisper OK" + ((" · " + str(result.get("transcript"))) if result.get("transcript") else "")
            else:
                if before.get("runtime_ok"):
                    update(stage="model", progress=35, message="Preparando modelo Whisper")
                else:
                    update(stage="runtime", progress=20, message="Reparando runtime nativo de Whisper")
                result = repair(model) if action == "repair" else prepare(model)
                success_message = "Whisper listo para transcribir"

            if result.get("ok"):
                update(status="done", stage="ready", progress=100, message=success_message, result=result)
            else:
                update(status="failed", stage=str(result.get("stage") or "failed"), progress=100, message="Whisper no pudo quedar listo", result=result, error=str(result.get("error") or result))
        except Exception as exc:
            update(status="failed", stage="failed", progress=100, message="Falló la preparación de Whisper", error=f"{type(exc).__name__}: {exc}")

    thread = threading.Thread(target=run, name=f"BinarioWhisper-{job_id}", daemon=True)
    with _LOCK:
        _JOBS[job_id]["_thread"] = thread
    thread.start()
    return get(job_id)
