#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.request import Request, urlopen

SERVICE_ID = "binario-r27-hub"
DEFAULT_PORT = 8780


def app_root() -> Path:
    override = os.environ.get("BINARIO_IA_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


def logs_root() -> Path:
    p = Path.home() / "Library" / "Logs" / "Binario IA"
    p.mkdir(parents=True, exist_ok=True)
    return p


def projects_root() -> Path:
    p = Path.home() / "Documents" / "Binario IA" / "Projects"
    p.mkdir(parents=True, exist_ok=True)
    return p


def port_open(port: int) -> bool:
    sock = socket.socket()
    sock.settimeout(0.2)
    try:
        return sock.connect_ex(("127.0.0.1", int(port))) == 0
    finally:
        sock.close()


def hub_identity(port: int) -> bool:
    try:
        req = Request(f"http://127.0.0.1:{port}/api/apps", headers={"Cache-Control": "no-cache"})
        with urlopen(req, timeout=0.8) as response:
            data = json.loads(response.read().decode("utf-8"))
        return isinstance(data, list) and len(data) >= 12 and any(x.get("id") == "05-editor-video-ia" for x in data if isinstance(x, dict))
    except Exception:
        return False


def choose_port(preferred: int = DEFAULT_PORT) -> tuple[int, bool]:
    if hub_identity(preferred):
        return preferred, True
    if not port_open(preferred):
        return preferred, False
    for port in range(preferred + 1, preferred + 80):
        if hub_identity(port):
            return port, True
        if not port_open(port):
            return port, False
    raise RuntimeError("No encontré un puerto local disponible para Binario IA.")


def python_candidates(root: Path) -> list[Path]:
    rows: list[Path] = []
    override = os.environ.get("BINARIO_PYTHON", "").strip()
    if override:
        rows.append(Path(override).expanduser())
    active = Path.home() / "Library" / "Application Support" / "Binario IA" / "runtime" / "active.json"
    try:
        data = json.loads(active.read_text(encoding="utf-8"))
        rr = Path(str(data.get("runtime_root") or "")).expanduser()
        rows += [rr / ".venv" / "bin" / "python3", rr / ".venv" / "bin" / "python"]
    except Exception:
        pass
    rows += [root / ".venv" / "bin" / "python3", root / ".venv" / "bin" / "python", Path(sys.executable)]
    return rows


def choose_python(root: Path) -> Path:
    for candidate in python_candidates(root):
        try:
            p = candidate.resolve()
            if p.is_file() and os.access(p, os.X_OK):
                return p
        except Exception:
            continue
    raise RuntimeError("No encontré el runtime Python de Binario IA. Repara/reinstala el runtime antes de iniciar.")


def wait_hub(port: int, proc: subprocess.Popen | None, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if hub_identity(port):
            return True
        if proc is not None and proc.poll() is not None:
            return False
        time.sleep(0.15)
    return False


def launch(*, open_browser: bool = True, preferred_port: int = DEFAULT_PORT) -> dict:
    root = app_root()
    if not (root / "hub" / "server.py").is_file():
        raise RuntimeError(f"La instalación no contiene el Hub canónico: {root}")
    projects_root()
    port, reused = choose_port(preferred_port)
    url = f"http://127.0.0.1:{port}/"
    if reused:
        if open_browser:
            webbrowser.open(url)
        return {"ok": True, "status": "reused", "url": url, "port": port, "root": str(root)}

    python = choose_python(root)
    log_path = logs_root() / "hub-r27.log"
    env = os.environ.copy()
    env["BINARIO_IA_ROOT"] = str(root)
    env["BINARIO_HUB_URL"] = url
    env["BINARIO_PROJECTS_HOME"] = str(projects_root())
    env["PYTHONPATH"] = os.pathsep.join([str(root), env.get("PYTHONPATH", "")]).strip(os.pathsep)
    with log_path.open("a", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [str(python), "-m", "hub.server", "--host", "127.0.0.1", "--port", str(port)],
            cwd=str(root), env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
    if not wait_hub(port, proc):
        raise RuntimeError(f"El Hub no inició. Revisa {log_path}")
    if open_browser:
        webbrowser.open(url)
    return {"ok": True, "status": "started", "url": url, "port": port, "pid": proc.pid, "python": str(python), "root": str(root), "projects": str(projects_root()), "log": str(log_path)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Launcher canónico de Binario IA R27")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args()
    try:
        result = launch(open_browser=not args.no_browser, preferred_port=args.port)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
