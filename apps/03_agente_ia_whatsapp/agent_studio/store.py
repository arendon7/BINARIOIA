from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, os, re, shutil
from common import project_center
from common import native_context_consumer as native_context

APP_ID="03-agente-ia-whatsapp"

def now(): return datetime.now(timezone.utc).isoformat()
def data_root()->Path:
    override=os.environ.get("BINARIO_AGENT_STUDIO_HOME")
    p=Path(override).expanduser() if override else Path.home()/"Documents"/"Binario IA"/"Agent Studio"
    p.mkdir(parents=True,exist_ok=True); return p

def _safe(pid:str)->str:
    if not re.fullmatch(r"prj-[a-f0-9]{12}",str(pid or "")): raise ValueError("project_id inválido")
    return str(pid)
def project_dir(pid:str)->Path: p=data_root()/_safe(pid); p.mkdir(parents=True,exist_ok=True); return p
def project_path(pid:str)->Path: return project_dir(pid)/"project.json"

def default_project(name:str="Nuevo agente", business_name:str="")->dict:
    base=native_context.claim_runtime_project(APP_ID)
    if base and project_path(base["id"]).exists():base=None
    if base:project_center.update(base["id"],{"name":name or "Nuevo agente","metadata":{**(base.get("metadata") or {}),"studio":"agent-studio-r15"}})
    else:base=project_center.create(name or "Nuevo agente",APP_ID,metadata={"studio":"agent-studio-r15"})
    pid=base["id"]
    row={
      "schema":"sbia-agent-studio-2.0","id":pid,"global_project_id":pid,"name":name or "Nuevo agente","status":"draft",
      "current_step":"business","created_at":now(),"updated_at":now(),
      "business":{"name":business_name or name or "Negocio","purpose":"Atender, orientar y escalar conversaciones de forma segura.","audience":"","tone":"cercano-profesional","hours":"","welcome":f"Hola, soy el asistente de {business_name or name or 'este negocio'}. ¿En qué te ayudo?","handoff":"Te conectaré con una persona del equipo."},
      "knowledge":[],
      "knowledge_documents":[],
      "intents":[
        {"id":"info","label":"Información","examples":["información","qué hacen","servicios"],"response":"Puedo orientarte con la información disponible.","action":"knowledge"},
        {"id":"sales","label":"Ventas","examples":["precio","cotización","comprar"],"response":"Cuéntame qué necesitas y te ayudo a avanzar.","action":"collect"},
        {"id":"support","label":"Soporte","examples":["ayuda","problema","soporte"],"response":"Cuéntame el problema para orientarte o escalarlo.","action":"collect"},
        {"id":"human","label":"Hablar con persona","examples":["asesor","humano","persona"],"response":"Te conectaré con una persona.","action":"handoff"}
      ],
      "variables":[{"id":"nombre","label":"Nombre","type":"text","required":False,"prompt":"¿Cómo te llamas?"}],
      "guardrails":["No inventar precios, disponibilidad o políticas.","Escalar reclamaciones, pagos, datos sensibles o solicitudes explícitas de una persona.","Responder solo con conocimiento aprobado cuando la respuesta dependa del negocio."],
      "flow":{"nodes":[],"edges":[]},
      "model":{"profile":"balanced","task":"conversation","last_route":None},
      "channel":{"type":"sandbox","status":"draft","phone_number_id":"","waba_id":"","webhook_url":"","centric_channel":""},
      "tests":{"cases":[],"last_run":None},"publish":{"status":"draft","last_export":None,"readiness":0},"observations":[],"versions":[]
    }
    row["flow"]=build_flow(row)
    save(row,snapshot=False); snapshot(pid,"created")
    return row

def build_flow(row:dict)->dict:
    nodes=[{"id":"start","type":"message","label":"Bienvenida","text":row.get("business",{}).get("welcome","" )},{"id":"router","type":"intent_router","label":"Router de intención"}]
    edges=[{"from":"start","to":"router"}]
    for it in row.get("intents",[]):
        nodes.append({"id":it["id"],"type":it.get("action","message"),"label":it.get("label",it["id"]),"text":it.get("response","")})
        edges.append({"from":"router","to":it["id"],"label":it.get("label","")})
    nodes += [{"id":"fallback","type":"message","label":"Fallback","text":"No estoy seguro de haber entendido. Puedo orientarte o conectarte con una persona."},{"id":"handoff","type":"handoff","label":"Humano","text":row.get("business",{}).get("handoff","")}]
    edges += [{"from":"router","to":"fallback","label":"sin match"},{"from":"fallback","to":"router"}]
    return {"nodes":nodes,"edges":edges}

def save(row:dict,snapshot:bool=False)->dict:
    pid=_safe(row["id"]); row["updated_at"]=now(); p=project_path(pid); tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps(row,indent=2,ensure_ascii=False),encoding='utf-8'); tmp.replace(p)
    try: project_center.update(pid,{"name":row.get("name"),"status":"active" if row.get("status")!="archived" else "archived","current_step":row.get("current_step"),"metadata":{"studio":"agent-studio-r15","readiness":row.get("publish",{}).get("readiness",0)}})
    except Exception: pass
    if snapshot: globals()["snapshot"](pid,"save")
    return row

def get(pid:str)->dict|None:
    p=project_path(pid)
    try:return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None
    except Exception:return None

def list_projects()->list[dict]:
    out=[]
    for p in data_root().glob('prj-*/project.json'):
        try:r=json.loads(p.read_text(encoding='utf-8'))
        except Exception:continue
        out.append({"id":r.get("id"),"name":r.get("name"),"status":r.get("status"),"current_step":r.get("current_step"),"updated_at":r.get("updated_at"),"readiness":r.get("publish",{}).get("readiness",0)})
    out.sort(key=lambda x:x.get('updated_at') or '',reverse=True);return out

def snapshot(pid:str,label:str="snapshot")->dict:
    row=get(pid)
    if not row: raise FileNotFoundError(pid)
    vdir=project_dir(pid)/'versions';vdir.mkdir(exist_ok=True)
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    path=vdir/f'{stamp}-{re.sub(r"[^a-z0-9-]+","-",label.lower()).strip("-") or "snapshot"}.json'
    path.write_text(json.dumps(row,indent=2,ensure_ascii=False),encoding='utf-8')
    meta={"id":path.stem,"label":label,"created_at":now(),"path":str(path)}
    versions=list(row.get('versions') or []);versions.append(meta);row['versions']=versions[-50:]
    save(row,snapshot=False);return meta

def list_versions(pid:str)->list[dict]:
    row=get(pid); return list(reversed((row or {}).get('versions') or []))

def log_event(pid:str,event:str,detail:dict|None=None)->dict:
    row={"timestamp":now(),"event":event,"detail":detail or {}}
    p=project_dir(pid)/'activity.jsonl'
    with p.open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    return row

def activity(pid:str,limit:int=100)->list[dict]:
    p=project_dir(pid)/'activity.jsonl'; rows=[]
    if p.exists():
      for line in p.read_text(encoding='utf-8',errors='ignore').splitlines():
        try:rows.append(json.loads(line))
        except Exception:pass
    return rows[-limit:]
