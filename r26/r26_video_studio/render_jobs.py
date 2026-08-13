from __future__ import annotations

import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class RenderJobManager:
    def __init__(self, workers: int = 1):
        self._executor = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="binario-render")
        self._lock = threading.Lock()
        self._jobs: dict[str, dict[str, Any]] = {}

    def start(self, fn: Callable[[Callable[[float], None]], dict[str, Any]], *, label: str) -> dict[str, Any]:
        job_id = f"render_{uuid.uuid4().hex[:10]}"
        job = {"id": job_id, "label": label, "status": "queued", "progress": 0.0, "created_at": _now(), "started_at": None, "finished_at": None, "result": None, "error": None}
        with self._lock:
            self._jobs[job_id] = job

        def update(value: float):
            with self._lock:
                if job_id in self._jobs:
                    self._jobs[job_id]["progress"] = max(0.0, min(1.0, float(value)))

        def runner():
            with self._lock:
                self._jobs[job_id]["status"] = "running"; self._jobs[job_id]["started_at"] = _now()
            try:
                result = fn(update)
                with self._lock:
                    self._jobs[job_id].update({"status": "completed", "progress": 1.0, "result": result, "finished_at": _now()})
            except Exception as exc:
                with self._lock:
                    self._jobs[job_id].update({"status": "failed", "error": str(exc), "trace": traceback.format_exc(limit=8), "finished_at": _now()})

        self._executor.submit(runner)
        return dict(job)

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return dict(self._jobs[job_id])

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(x) for x in sorted(self._jobs.values(), key=lambda j: j["created_at"], reverse=True)[:30]]
