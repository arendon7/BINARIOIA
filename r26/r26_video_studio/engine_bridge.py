from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from .integration_adapter import inspect_target


def bridge_status() -> dict[str, Any]:
    root_raw = os.environ.get("BINARIO_R25_ROOT", "").strip()
    render_cmd = os.environ.get("BINARIO_R25_RENDER_CMD", "").strip()
    root_report = inspect_target(Path(root_raw)) if root_raw and Path(root_raw).exists() else {"eligible": False, "root": root_raw or None, "evidence": {}}
    return {
        "r25_root": root_report,
        "r25_render_command": bool(render_cmd),
        "native_ffmpeg": bool(shutil.which("ffmpeg") and shutil.which("ffprobe")),
        "preferred_order": ["r25_render_command", "native_ffmpeg"],
        "env": {"root": "BINARIO_R25_ROOT", "render": "BINARIO_R25_RENDER_CMD"},
    }


def run_external_r25(plan_path: Path, output_path: Path, *, progress: Callable[[float], None] | None = None) -> dict[str, Any]:
    template = os.environ.get("BINARIO_R25_RENDER_CMD", "").strip()
    if not template:
        raise RuntimeError("BINARIO_R25_RENDER_CMD not configured")
    command = template.format(plan=shlex.quote(str(plan_path)), output=shlex.quote(str(output_path)))
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0 or not output_path.is_file():
        raise RuntimeError((stderr or stdout or "R25 render failed")[-2400:])
    if progress:
        progress(1.0)
    return {"ok": True, "engine": "r25_external", "path": str(output_path), "size": output_path.stat().st_size}
