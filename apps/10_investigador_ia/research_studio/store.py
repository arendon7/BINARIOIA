from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, os, re
from common import project_center, project_storage
from common import native_context_consumer as native_context

APP_ID = "10-investigador-ia"

def now(): return datetime.now(timezone.utc).isoformat()

def legacy_root() -> Path:
    return Path(os.environ.get("BINARIO_RESEARCH_STUDIO_HOME") or (Path.home()/"Documents"/"Binario IA"/"Research Studio")).expanduser()

def data_root() -> Path:
    """Compatibility alias. Active state lives in canonical Project Storage."""
    return legacy_root()

def _safe(pid: str) -> str:
    if not re.fullmatch(r"prj-[a-f0-9]{12}", str(pid or "")):
        raise ValueError("project_id inválido")
    return str(pid)

def project_dir(pid):
    pid=_safe(pid);target=project_storage.app_state_dir(pid,APP_ID);legacy=legacy_root()/pid
    if legacy.is_dir() and legacy.resolve()!=target.resolve():project_storage.migrate_legacy_state(pid,APP_ID,legacy)
    return target

def export_dir(pid): return project_storage.app_export_dir(_safe(pid),APP_ID)

def project_path(pid): return project_dir(pid)/"project.json"

def create(name="Nueva investigación", question="") -> dict:
    base=native_context.claim_runtime_project(APP_ID)
    if base and project_path(base["id"]).exists():base=None
    if base:project_center.update(base["id"],{"name":name or "Nueva investigación","metadata":{**(base.get("metadata") or {}),"studio":"research-studio-r16","storage":"canonical-project"}})
    else:base=project_center.create(name or "Nueva investigación", APP_ID, metadata={"studio":"research-studio-r16","storage":"canonical-project"})
    row={
      "schema":"sbia-research-studio-2.0","id":base["id"],"global_project_id":base["id"],
      "name":name or "Nueva investigación","status":"active","current_step":"question","created_at":now(),"updated_at":now(),
      "question":question or "","scope":{"decision":"","depth":"standard","languages":["es"],"recency":"any"},
      "discovery":{"queries":[],"provider":"duckduckgo-html","last_run":None,"results":[]},
      "sources":[],"evidence":[],"claims":[],"contradictions":[],
      "synthesis":{"summary":"","confidence":0,"status":"draft","review_notes":""},
      "ai":{"profile":"balanced","last_route":None},"exports":[],"versions":[]
    }
    save(row); snapshot(row["id"],"created"); return row

def save(row):
    row["updated_at"]=now(); p=project_path(row["id"]); tmp=p.with_suffix(".tmp")
    tmp.write_text(json.dumps(row,indent=2,ensure_ascii=False),encoding="utf-8"); tmp.replace(p)
    try:
        project_center.update(row["id"],{"name":row.get("name"),"status":row.get("status","active"),"current_step":row.get("current_step"),"metadata":{"studio":"research-studio-r16","storage":"canonical-project","sources":len(row.get("sources",[])),"confidence":row.get("synthesis",{}).get("confidence",0)}})
    except Exception: pass
    return row

def get(pid):
    p=project_path(pid)
    try: return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    except Exception: return None

def list_projects():
    out=[]
    for global_row in project_center.list_projects(APP_ID):
        try:r=get(global_row.get('id'))
        except Exception:r=None
        if not r:continue
        out.append({"id":r.get("id"),"name":r.get("name"),"status":r.get("status"),"current_step":r.get("current_step"),"updated_at":r.get("updated_at"),"sources":len(r.get("sources",[])),"confidence":r.get("synthesis",{}).get("confidence",0)})
    return sorted(out,key=lambda x:x.get("updated_at") or "",reverse=True)

def source_file(pid,source_id): return project_dir(pid)/"sources"/f"{source_id}.txt"

def put_source_text(pid,source_id,text):
    p=source_file(pid,source_id); p.parent.mkdir(exist_ok=True); p.write_text(text or "",encoding="utf-8"); return str(p)

def source_text(pid,source):
    p=Path(source.get("content_path") or "")
    try: return p.read_text(encoding="utf-8",errors="ignore") if p.is_file() else source.get("text","")
    except Exception: return source.get("text","")

def snapshot(pid,label="snapshot"):
    row=get(pid)
    if not row: raise FileNotFoundError(pid)
    d=project_dir(pid)/"versions"; d.mkdir(exist_ok=True)
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S-%f"); safe=re.sub(r"[^a-z0-9-]+","-",label.lower()).strip("-") or "snapshot"
    p=d/f"{stamp}-{safe}.json"; p.write_text(json.dumps(row,indent=2,ensure_ascii=False),encoding="utf-8")
    meta={"id":p.stem,"label":label,"created_at":now(),"path":str(p)}; row["versions"]=(row.get("versions") or [])[-49:]+[meta]; save(row); return meta
