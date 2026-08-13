from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, os, re, uuid

PROJECT_DIRS=("assets","autosave","exports","training","logs")
R26_PROJECT_SCHEMA="binario-ia/project-center/v1"

def _root()->Path:
    override=os.environ.get("BINARIO_PROJECTS_HOME")
    p=Path(override).expanduser() if override else Path.home()/"Documents"/"Binario IA"/"Projects"
    p.mkdir(parents=True,exist_ok=True);return p

def _now():return datetime.now(timezone.utc).isoformat()
def _safe_id(v:str)->str:
    if not re.fullmatch(r"[A-Za-z0-9._-]{4,128}",str(v or "")):raise ValueError("project_id inválido")
    return str(v)
def _path(pid:str)->Path:return _root()/f"{_safe_id(pid)}.json"

def _slug(value:str)->str:
    value=re.sub(r"[^A-Za-z0-9._ -]+","",str(value or "")).strip().lower()
    value=re.sub(r"[\s._-]+","-",value).strip("-")
    return value[:64] or "proyecto"

def _inside(root:Path,path:Path)->bool:
    try:
        root=root.resolve();path=path.resolve();return path==root or root in path.parents
    except Exception:return False

def _sync_workspace(row:dict)->dict:
    """Bridge the historical flat project record with the canonical R26 physical project folder."""
    root=_root();meta=dict(row.get("metadata") or {})
    existing=meta.get("project_path")
    directory=Path(str(existing)).expanduser() if existing else root/f"{_slug(row.get('name'))}--{str(row.get('id') or '')[-6:]}"
    if not _inside(root,directory):
        directory=root/f"{_slug(row.get('name'))}--{str(row.get('id') or '')[-6:]}"
    directory.mkdir(parents=True,exist_ok=True)
    folders={}
    for child in PROJECT_DIRS:
        target=directory/child;target.mkdir(parents=True,exist_ok=True);folders[child]=str(target.resolve())
    meta["project_path"]=str(directory.resolve());meta["folders"]=folders;meta["preserve_on_uninstall"]=True
    row["metadata"]=meta
    manifest={
        "schema":R26_PROJECT_SCHEMA,"id":row.get("id"),"name":row.get("name"),"type":meta.get("project_type","general"),
        "app_id":row.get("app_id"),"created_at":row.get("created_at"),"updated_at":row.get("updated_at"),
        "path":str(directory.resolve()),"folders":folders,"safety":{"preserve_on_uninstall":True},
        "legacy_record":str(_path(str(row.get("id"))).resolve()),
    }
    (directory/"project.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    return row

def create(name:str,app_id:str,status:str="active",metadata:dict|None=None)->dict:
    pid=f"prj-{uuid.uuid4().hex[:12]}";now=_now()
    row={"schema":"sbia-project-2.0","id":pid,"name":str(name or "Nuevo proyecto").strip() or "Nuevo proyecto","app_id":str(app_id),"status":status,"current_step":None,"created_at":now,"updated_at":now,"metadata":metadata or {},"artifacts":[],"sources":[],"notes":[],"run_ids":[],"handoff_ids":[]}
    row=_sync_workspace(row)
    _path(pid).write_text(json.dumps(row,indent=2,ensure_ascii=False),encoding="utf-8")
    try:
        from common.workspace_event_bridge import project_event
        project_event("project.created",row,summary=f"Proyecto creado · {row['name']}")
    except Exception:pass
    return row

def get(pid:str)->dict|None:
    p=_path(pid)
    try:return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    except Exception:return None


def repair_existing_projects()->dict:
    repaired=[]; unchanged=[]; failed=[]
    for p in _root().glob("prj-*.json"):
        try:
            row=json.loads(p.read_text(encoding="utf-8"))
            meta=row.get("metadata") if isinstance(row.get("metadata"),dict) else {}
            project_path=Path(str(meta.get("project_path") or "")).expanduser() if meta.get("project_path") else None
            manifest_ok=bool(project_path and _inside(_root(),project_path) and (project_path/"project.json").is_file())
            if manifest_ok:
                unchanged.append(str(row.get("id") or p.stem));continue
            row=_sync_workspace(row)
            p.write_text(json.dumps(row,indent=2,ensure_ascii=False),encoding="utf-8")
            repaired.append(str(row.get("id") or p.stem))
        except Exception as exc:
            failed.append({"file":str(p),"error":f"{type(exc).__name__}: {exc}"})
    return {"ok":not failed,"repaired":repaired,"unchanged":unchanged,"failed":failed,"root":str(_root())}

def list_projects(app_id:str|None=None,include_archived:bool=False)->list[dict]:
    rows=[]
    for p in _root().glob("prj-*.json"):
        try:r=json.loads(p.read_text(encoding="utf-8"))
        except Exception:continue
        if app_id and r.get("app_id")!=app_id:continue
        if not include_archived and r.get("status")=="archived":continue
        rows.append(r)
    rows.sort(key=lambda x:x.get("updated_at","") ,reverse=True);return rows

def update(pid:str,patch:dict)->dict:
    row=get(pid)
    if not row:raise FileNotFoundError(pid)
    before=dict(row)
    allowed={"name","status","current_step","metadata","artifacts","sources","notes","run_ids","handoff_ids"}
    for k,v in patch.items():
        if k not in allowed:continue
        if k=="metadata" and isinstance(v,dict):
            # Studio metadata is additive. Never discard canonical physical
            # project_path/folders/workspace linkage when an App updates its
            # own status fields; changing those paths strands autosave state.
            row["metadata"]={**(row.get("metadata") if isinstance(row.get("metadata"),dict) else {}),**v}
        else:row[k]=v
    row["updated_at"]=_now();row=_sync_workspace(row);_path(pid).write_text(json.dumps(row,indent=2,ensure_ascii=False),encoding="utf-8")
    try:
        from common.workspace_event_bridge import project_event
        project_event("project.updated",row,summary=f"Proyecto actualizado · {row.get('name')}",before=before)
    except Exception:pass
    return row

def add_run(pid:str,run_id:str)->dict|None:
    row=get(pid)
    if not row:return None
    ids=list(row.get("run_ids") or [])
    if run_id not in ids:ids.append(run_id)
    return update(pid,{"run_ids":ids})

def archive(pid:str)->dict:return update(pid,{"status":"archived"})


def add_handoff(pid:str,handoff_id:str)->dict|None:
    row=get(pid)
    if not row:return None
    ids=list(row.get("handoff_ids") or [])
    if handoff_id not in ids:ids.append(handoff_id)
    return update(pid,{"handoff_ids":ids})
