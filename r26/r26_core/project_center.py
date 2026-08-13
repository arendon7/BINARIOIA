from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "binario-ia/project-center/v1"
PROJECT_DIRS = ("assets", "autosave", "exports", "training", "logs")


def canonical_projects_root() -> Path:
    override = os.environ.get("BINARIO_PROJECTS_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / "Documents" / "Binario IA" / "Projects").resolve()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._ -]+", "", value or "").strip().lower()
    value = re.sub(r"[\s._-]+", "-", value).strip("-")
    return value[:64] or "proyecto"


def _assert_inside(root: Path, path: Path) -> Path:
    root = root.expanduser().resolve(); path = path.expanduser().resolve()
    if path != root and root not in path.parents:
        raise ValueError("path outside managed projects root")
    return path


def _manifest_path(project_dir: Path) -> Path:
    return project_dir / "project.json"


def create_project(root: Path, *, name: str, project_type: str = "general", app_id: str | None = None) -> dict[str, Any]:
    root = root.expanduser().resolve(); root.mkdir(parents=True, exist_ok=True)
    project_id = f"prj_{uuid.uuid4().hex[:10]}"; directory = root / f"{slugify(name)}--{project_id[-6:]}"; directory.mkdir(parents=True, exist_ok=False)
    for child in PROJECT_DIRS: (directory / child).mkdir(parents=True, exist_ok=True)
    now = utc_now(); manifest = {"schema": SCHEMA,"id": project_id,"name": (name or "Proyecto").strip() or "Proyecto","type": project_type,"app_id": app_id,"created_at": now,"updated_at": now,"path": str(directory),"folders": {child: str(directory / child) for child in PROJECT_DIRS},"safety": {"preserve_on_uninstall": True}}
    _manifest_path(directory).write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"); return manifest


def load_project(directory: Path) -> dict[str, Any]:
    data = json.loads(_manifest_path(directory).read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA or not data.get("id"): raise ValueError("invalid project manifest")
    return data


def list_projects(root: Path) -> list[dict[str, Any]]:
    root = root.expanduser().resolve()
    if not root.exists(): return []
    projects=[]
    for manifest_path in root.glob("*/project.json"):
        try:
            project=load_project(manifest_path.parent); project["exists"]=True; projects.append(project)
        except Exception: continue
    return sorted(projects,key=lambda x:x.get("updated_at",""),reverse=True)


def find_project(root: Path, project_id: str) -> dict[str, Any]:
    for project in list_projects(root):
        if project["id"] == project_id: return project
    raise KeyError(project_id)


def project_target(root: Path, project_id: str, target: str = "root") -> Path:
    project=find_project(root,project_id); project_dir=_assert_inside(root,Path(project["path"]))
    if target == "root": return project_dir
    if target not in PROJECT_DIRS: raise ValueError("unsupported project target")
    return _assert_inside(root,project_dir/target)


def save_project_payload(root: Path, project_id: str, payload: dict[str, Any], *, filename: str = "project_state.json") -> Path:
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}",filename): raise ValueError("invalid filename")
    project=find_project(root,project_id); project_dir=_assert_inside(root,Path(project["path"])); target=project_dir/"autosave"/filename; tmp=target.with_suffix(target.suffix+".tmp"); tmp.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8"); os.replace(tmp,target)
    manifest_path=_manifest_path(project_dir); manifest=load_project(project_dir); manifest["updated_at"]=utc_now(); manifest_path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8"); return target


def open_in_file_manager(path: Path) -> dict[str, Any]:
    path=path.expanduser().resolve()
    if not path.exists(): raise FileNotFoundError(path)
    if sys.platform == "darwin": subprocess.Popen(["open",str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return {"ok":True,"platform":"macos","path":str(path)}
    if sys.platform.startswith("win"): os.startfile(str(path)); return {"ok":True,"platform":"windows","path":str(path)}  # type: ignore[attr-defined]
    try: subprocess.Popen(["xdg-open",str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); return {"ok":True,"platform":"linux","path":str(path)}
    except FileNotFoundError: return {"ok":False,"platform":sys.platform,"path":str(path),"reason":"file_manager_not_available"}


def search_project_files(root: Path, project_id: str, query: str = "", *, max_results: int = 250) -> list[dict[str, Any]]:
    project=find_project(root,project_id); project_dir=_assert_inside(root,Path(project["path"])); needle=(query or "").strip().lower(); results=[]
    for path in project_dir.rglob("*"):
        if path.name.startswith("."): continue
        safe=_assert_inside(root,path); rel=safe.relative_to(project_dir).as_posix()
        if needle and needle not in rel.lower(): continue
        try: stat=safe.stat()
        except OSError: continue
        results.append({"name":safe.name,"relative_path":rel,"kind":"folder" if safe.is_dir() else "file","size":0 if safe.is_dir() else stat.st_size,"modified":int(stat.st_mtime)})
        if len(results)>=max_results: break
    return sorted(results,key=lambda x:(x["kind"]!="folder",x["relative_path"].lower()))
