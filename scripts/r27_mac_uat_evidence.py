#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "sbia-r27-mac-uat-evidence-1.0"
REQUIRED_PROJECT_DIRS = ("assets", "autosave", "exports", "training", "logs")
PROVIDER_VARS = (
    "BINARIO_OPENAI_API_KEY",
    "BINARIO_ANTHROPIC_API_KEY",
    "BINARIO_GEMINI_API_KEY",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_arch(value: str) -> str:
    value = str(value or "").strip().lower()
    return "arm64" if value in {"arm64", "aarch64"} else value


def command(cmd: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "ok": cp.returncode == 0,
            "returncode": cp.returncode,
            "stdout": (cp.stdout or "")[-5000:],
            "stderr": (cp.stderr or "")[-5000:],
        }
    except Exception as exc:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}


def result(name: str, status: str, **detail: Any) -> dict[str, Any]:
    return {"name": name, "status": status, **detail}


def load_build_provenance(root: Path) -> dict[str, Any]:
    path = root / "R27_UAT_BUILD.json"
    if not path.is_file():
        return result("build_provenance", "FAIL", path=str(path), error="R27_UAT_BUILD.json no existe")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return result("build_provenance", "FAIL", path=str(path), error=f"{type(exc).__name__}: {exc}")
    source_sha = str(data.get("source_sha") or "")
    valid_sha = bool(re.fullmatch(r"[0-9a-f]{40}", source_sha))
    valid_cycle = data.get("cycle") == "R27" and data.get("channel") == "uat"
    status = "PASS" if valid_sha and valid_cycle else "FAIL"
    return result(
        "build_provenance",
        status,
        path=str(path),
        source_sha=source_sha,
        baseline_sha256=data.get("baseline_sha256"),
        release_status=data.get("release_status"),
        schema=data.get("schema"),
        error=None if status == "PASS" else "Provenance R27 UAT inválida o incompleta",
    )


def platform_check() -> dict[str, Any]:
    system = platform.system().lower()
    os_arch = normalize_arch(platform.machine())
    py_arch = normalize_arch(platform.machine())
    mac_version = platform.mac_ver()[0]
    status = "PASS" if system == "darwin" and os_arch in {"arm64", "x86_64"} else "FAIL"
    return result(
        "platform",
        status,
        system=system,
        macos=mac_version,
        os_arch=os_arch,
        python_arch=py_arch,
        native_arch_match=os_arch == py_arch,
        python=sys.executable,
        python_version=platform.python_version(),
    )


def launcher_check(root: Path) -> dict[str, Any]:
    launcher = root / "ABRIR_BINARIO_IA_R27.command"
    hub = root / "hub" / "server.py"
    ok = launcher.is_file() and os.access(launcher, os.X_OK) and hub.is_file()
    return result(
        "launcher_hub",
        "PASS" if ok else "FAIL",
        launcher=str(launcher),
        launcher_executable=bool(launcher.is_file() and os.access(launcher, os.X_OK)),
        hub_server=str(hub),
        hub_present=hub.is_file(),
    )


def project_storage_check(projects_root: Path) -> dict[str, Any]:
    projects_root = projects_root.expanduser().resolve()
    projects = []
    if projects_root.is_dir():
        projects = sorted(
            p for p in projects_root.iterdir()
            if p.is_dir() and not p.name.startswith("_") and not p.name.startswith(".")
        )
    inspected = []
    complete = []
    for p in projects[:50]:
        dirs = {name: (p / name).is_dir() for name in REQUIRED_PROJECT_DIRS}
        row = {"project": p.name, "path": str(p), "dirs": dirs}
        inspected.append(row)
        if all(dirs.values()):
            complete.append(row)
    if not projects_root.is_dir():
        status = "FAIL"
        note = "La raíz canónica de proyectos no existe"
    elif not projects:
        status = "PENDING"
        note = "No hay proyecto de usuario para validar estructura física en Finder"
    elif not complete:
        status = "PENDING"
        note = "Hay proyectos, pero ninguno expone todavía las cinco carpetas canónicas"
    else:
        status = "PASS"
        note = "Existe al menos un proyecto con estructura canónica completa"
    return result(
        "project_storage",
        status,
        projects_root=str(projects_root),
        project_count=len(projects),
        complete_project_count=len(complete),
        inspected=inspected,
        note=note,
    )


def _tool_candidates(root: Path, name: str) -> list[Path]:
    out: list[Path] = []
    runtime = os.environ.get("BINARIO_RUNTIME_ROOT")
    if runtime:
        out.append(Path(runtime).expanduser() / "bin" / name)
    out.extend([
        root / "runtime" / "bin" / name,
        Path.home() / "Library" / "Application Support" / "Binario IA" / "runtime" / "v2" / "bin" / name,
    ])
    found = shutil.which(name)
    if found:
        out.append(Path(found))
    unique: list[Path] = []
    seen = set()
    for p in out:
        key = str(p)
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def find_tool(root: Path, name: str) -> Path | None:
    for p in _tool_candidates(root, name):
        if p.is_file() and os.access(p, os.X_OK):
            return p
    runtime_base = Path.home() / "Library" / "Application Support" / "Binario IA" / "runtime" / "v2"
    if runtime_base.is_dir():
        for p in sorted(runtime_base.glob(f"macos-*/bin/{name}")):
            if p.is_file() and os.access(p, os.X_OK):
                return p
    return None


def ffmpeg_check(root: Path) -> dict[str, Any]:
    ffmpeg = find_tool(root, "ffmpeg")
    ffprobe = find_tool(root, "ffprobe")
    if not ffmpeg or not ffprobe:
        return result(
            "ffmpeg",
            "FAIL",
            ffmpeg=str(ffmpeg) if ffmpeg else None,
            ffprobe=str(ffprobe) if ffprobe else None,
            error="FFmpeg/FFprobe no disponibles",
        )
    ver = command([str(ffmpeg), "-version"])
    probe = command([str(ffprobe), "-version"])
    enc = command([str(ffmpeg), "-hide_banner", "-encoders"])
    videotoolbox = "h264_videotoolbox" in (enc.get("stdout") or "")
    ok = ver["ok"] and probe["ok"]
    first_line = (ver.get("stdout") or "").splitlines()
    return result(
        "ffmpeg",
        "PASS" if ok else "FAIL",
        ffmpeg=str(ffmpeg),
        ffprobe=str(ffprobe),
        version=first_line[0] if first_line else None,
        videotoolbox_encoder=videotoolbox,
        software_fallback_allowed=True,
        ffmpeg_rc=ver.get("returncode"),
        ffprobe_rc=probe.get("returncode"),
    )


def whisper_check(root: Path, run_selftest: bool) -> dict[str, Any]:
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(root))
        from runtime.whisper_gateway import status as whisper_status
        from runtime.whisper_selftest import run as whisper_selftest

        state = whisper_status("small")
        ready = bool(state.get("ready"))
        if not run_selftest:
            return result(
                "whisper",
                "PASS" if ready else "PENDING",
                ready=ready,
                status_detail=state,
                selftest="not_requested",
            )
        test = whisper_selftest("small", "es")
        ok = ready and bool(test.get("ok"))
        return result(
            "whisper",
            "PASS" if ok else "FAIL",
            ready=ready,
            status_detail=state,
            selftest=test,
        )
    except Exception as exc:
        return result("whisper", "FAIL", error=f"{type(exc).__name__}: {exc}")
    finally:
        sys.path[:] = old_path


def keychain_check() -> dict[str, Any]:
    security = Path("/usr/bin/security")
    if not security.is_file():
        return result("keychain", "FAIL", security=str(security), error="macOS security no disponible")
    configured = []
    for var in PROVIDER_VARS:
        service = "com.sistemabinario.binarioia." + var.lower()
        cp = command([str(security), "find-generic-password", "-a", var, "-s", service], timeout=10)
        if cp["ok"]:
            configured.append(var)
    return result(
        "keychain",
        "PASS" if configured else "PENDING",
        security=str(security),
        configured_provider_variables=configured,
        secret_values_exposed=False,
        note="PASS solo confirma presencia de una credencial; la llamada real del proveedor sigue siendo UAT manual" if configured else "No se detectó credencial de proveedor configurada",
    )


def manual_steps() -> list[dict[str, str]]:
    return [
        {"id": "hub_project_continuity", "status": "PENDING", "step": "Abrir Hub, abrir proyecto existente y confirmar el mismo project_id al entrar/salir de Video Studio."},
        {"id": "finder_project", "status": "PENDING", "step": "Abrir la ruta física desde Hub en Finder y verificar assets/autosave/exports/training/logs y preservación legacy."},
        {"id": "video_real_render", "status": "PENDING", "step": "Importar video real, editar y renderizar H.264/AAC; comprobar reproducción del archivo exportado."},
        {"id": "video_modes", "status": "PENDING", "step": "Cambiar Simple ↔ Pro, reiniciar y confirmar persistencia."},
        {"id": "whisper_real_media", "status": "PENDING", "step": "Transcribir un audio/video real corto del usuario y revisar texto resultante."},
        {"id": "provider_real_call", "status": "PENDING", "step": "Probar un proveedor habilitado desde Hub y confirmar que la clave permanece en Keychain, no en JSON/proyecto."},
        {"id": "failure_isolation", "status": "PENDING", "step": "Forzar/observar fallo de Whisper y confirmar que edición/render continúan operativos."},
    ]


def summarize(checks: list[dict[str, Any]], manual: list[dict[str, str]]) -> str:
    statuses = {c.get("status") for c in checks}
    if "FAIL" in statuses:
        return "PRECHECK_FAIL"
    if "PENDING" in statuses or any(x.get("status") != "PASS" for x in manual):
        return "PRECHECK_PASS_MANUAL_PENDING"
    return "UAT_PASS"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# BINARIO IA · R27 Mac UAT Evidence",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Overall: **{report['overall']}**",
        f"- Root: `{report['root']}`",
        "",
        "## Automatic checks",
    ]
    for row in report["checks"]:
        lines.append(f"- **{row['status']}** · {row['name']}")
    lines += ["", "## Manual gates"]
    for row in report["manual_steps"]:
        lines.append(f"- **{row['status']}** · {row['id']}: {row['step']}")
    lines += [
        "",
        "## Release rule",
        "",
        "`UAT_PASS` solo es válido cuando no existe ningún FAIL/PENDING y la evidencia corresponde al `source_sha` registrado en `R27_UAT_BUILD.json`.",
        "La existencia de este reporte no elimina `.release-blocked` automáticamente.",
        "",
    ]
    return "\n".join(lines)


def run(root: Path, projects_root: Path, run_whisper_selftest: bool) -> dict[str, Any]:
    root = root.expanduser().resolve()
    checks = [
        load_build_provenance(root),
        platform_check(),
        launcher_check(root),
        project_storage_check(projects_root),
        ffmpeg_check(root),
        whisper_check(root, run_whisper_selftest),
        keychain_check(),
    ]
    manual = manual_steps()
    return {
        "schema": SCHEMA,
        "generated_at": now(),
        "root": str(root),
        "projects_root": str(projects_root.expanduser().resolve()),
        "checks": checks,
        "manual_steps": manual,
        "overall": summarize(checks, manual),
        "release_blocked": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect reproducible R27 physical Mac UAT preflight evidence.")
    ap.add_argument("--root", type=Path, default=Path(os.environ.get("BINARIO_FULL_ROOT") or Path.cwd()))
    ap.add_argument("--projects-root", type=Path, default=Path(os.environ.get("BINARIO_PROJECTS_HOME") or (Path.home()/"Documents"/"Binario IA"/"Projects")))
    ap.add_argument("--output", type=Path)
    ap.add_argument("--whisper-selftest", action="store_true", help="Run the real macOS say -> Whisper end-to-end self-test.")
    args = ap.parse_args()

    report = run(args.root, args.projects_root, args.whisper_selftest)
    output = args.output or (Path.home()/"Desktop"/f"BINARIO_IA_R27_UAT_EVIDENCE_{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    output = output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output/"r27-mac-uat-evidence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (output/"r27-mac-uat-evidence.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"overall": report["overall"], "evidence_dir": str(output)}, ensure_ascii=False, indent=2))
    return 2 if report["overall"] == "PRECHECK_FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
