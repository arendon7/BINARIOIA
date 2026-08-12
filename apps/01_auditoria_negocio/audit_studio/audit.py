from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import json,zipfile,hashlib,re,sys
APP_DIR=Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:sys.path.insert(0,str(APP_DIR))
import engine
from . import store
from common import native_context_consumer as native_context

def _lines(v):
    if isinstance(v,list):return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in re.split(r'[\n;]+',str(v or '')) if x.strip()]
def add_evidence(pr,title,content,source='manual',confidence=1.0):
    content=str(content or '').strip()
    if not content:raise ValueError('La evidencia está vacía.')
    row={"id":f"ev-{len(pr.get('evidence') or [])+1:03d}","title":str(title or 'Evidencia'),"source":str(source or 'manual'),"content":content,"sha256":hashlib.sha256(content.encode()).hexdigest(),"confidence":max(0,min(1,float(confidence or 0))),"captured_at":datetime.now(timezone.utc).isoformat()}
    pr.setdefault('evidence',[]).append(row);pr['current_step']='evidence';store.save(pr);return row
def diagnose(pr):
    i=pr.get('intake') or {}; ev='\n'.join(f"[{x.get('title')}] {x.get('content')}" for x in pr.get('evidence') or [])
    ctx=native_context.text('01-auditoria-negocio',['FACT','CONSTRAINT','RISK','OPEN_QUESTION'],20)
    description=str(i.get('description') or '')+("\nEvidencia adicional:\n"+ev if ev else '')
    if ctx:description += "\nContexto canónico adoptado del Workspace (solo apoyo; no sustituye evidencia del proyecto):\n"+ctx
    payload={"business_name":pr.get('name'),"description":description,"processes":i.get('processes') or [],"pains":i.get('pains') or [],"tools":i.get('tools') or [],"goals":i.get('goals') or ''}
    r=engine.run(payload); d=pr['diagnosis'];d.update({"status":"generated","scores":r.get('scores') or {},"opportunities":r.get('findings') or [],"risks":r.get('warnings') or [],"summary":r.get('summary') or '',"raw":r,"reviewed":False,"workspace_context":native_context.metadata('01-auditoria-negocio')});pr['current_step']='diagnosis';store.save(pr);return d
def review(pr,notes=''):
    if not pr.get('diagnosis',{}).get('raw'):raise RuntimeError('Primero ejecuta el diagnóstico.')
    pr['diagnosis']['review_notes']=str(notes or '');pr['diagnosis']['reviewed']=True;pr['diagnosis']['status']='reviewed';pr['current_step']='opportunities';store.snapshot(pr['id'],'diagnosis-reviewed');store.save(pr);return pr['diagnosis']
def build_roadmap(pr):
    if not pr.get('diagnosis',{}).get('raw'):raise RuntimeError('Primero ejecuta el diagnóstico.')
    opps=pr['diagnosis'].get('opportunities') or []
    rows=[]
    phases=[('0–30 días','Descubrir y medir'),('31–60 días','Implementar pilotos'),('61–90 días','Escalar y gobernar')]
    for ix,(window,theme) in enumerate(phases):
        o=opps[ix%len(opps)] if opps else {"title":"Mejora prioritaria","recommendation":"Validar el proceso y definir un piloto medible."}
        rows.append({"id":f"rm-{ix+1:02d}","window":window,"theme":theme,"action":o.get('recommendation') or o.get('title'),"opportunity":o.get('title'),"owner":"Por asignar","kpi":"Definir línea base y objetivo","status":"planned","priority":"alta" if ix==0 else 'media'})
    pr['roadmap']=rows;pr['current_step']='roadmap';store.save(pr);return rows
def readiness(pr):
    i=pr.get('intake') or {}; d=pr.get('diagnosis') or {}
    checks={"intake":bool(pr.get('name') and i.get('description')),"processes":len(i.get('processes') or [])>=1,"evidence":len(pr.get('evidence') or [])>=1,"diagnosis":bool(d.get('raw')),"reviewed":bool(d.get('reviewed')),"roadmap":len(pr.get('roadmap') or [])>=3}
    score=round(sum(checks.values())/len(checks)*100); out={"checks":checks,"score":score,"ready":score>=80 and checks['diagnosis'] and checks['roadmap']};pr['diagnosis']['readiness']=score;store.save(pr);return out
def handoff(pr,target):
    target=str(target)
    if target not in {'research','proposal','app-factory','documents'}:raise ValueError('Handoff no soportado')
    d=store.pdir(pr['id'])/'handoffs';d.mkdir(exist_ok=True)
    payload={"schema":"sbia-handoff-1.0","source_app":"01-auditoria-negocio","target":target,"project_id":pr['id'],"name":pr['name'],"summary":pr.get('diagnosis',{}).get('summary'),"scores":pr.get('diagnosis',{}).get('scores'),"opportunities":pr.get('diagnosis',{}).get('opportunities'),"roadmap":pr.get('roadmap'),"evidence":pr.get('evidence'),"human_approval_required":True}
    p=d/f'{target}.json';p.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8');pr.setdefault('handoffs',{})[target]=str(p);store.save(pr);return {"target":target,"path":str(p),"payload":payload}
def export(pr):
    rd=readiness(pr); d=store.export_dir(pr['id']);d.mkdir(parents=True,exist_ok=True)
    md=d/'auditoria.md'; js=d/'auditoria.json'; z=d/'auditoria-package.zip'
    diag=pr.get('diagnosis') or {}
    lines=[f"# Auditoría de Negocio · {pr['name']}","",f"**Readiness:** {rd['score']}%","",'## Resumen',diag.get('summary') or 'Pendiente','', '## Madurez']
    lines += [f"- **{k}:** {v}/100" for k,v in (diag.get('scores') or {}).items()]
    lines += ['', '## Oportunidades']+[f"- **{x.get('title')}** · {x.get('recommendation') or x.get('detail','')}" for x in diag.get('opportunities') or []]
    lines += ['', '## Roadmap 90 días']+[f"- **{x['window']} · {x['theme']}:** {x['action']} · KPI: {x['kpi']}" for x in pr.get('roadmap') or []]
    lines += ['', '## Evidencia']+[f"- {x['title']} · {x['source']} · SHA-256 `{x['sha256'][:12]}…`" for x in pr.get('evidence') or []]
    md.write_text('\n'.join(lines)+'\n',encoding='utf-8');js.write_text(json.dumps(pr,indent=2,ensure_ascii=False),encoding='utf-8')
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zz:
        zz.write(md,md.name);zz.write(js,js.name)
        for hp in (store.pdir(pr['id'])/'handoffs').glob('*.json') if (store.pdir(pr['id'])/'handoffs').exists() else []:zz.write(hp,f'handoffs/{hp.name}')
    row={"created_at":datetime.now(timezone.utc).isoformat(),"markdown":str(md),"json":str(js),"zip":str(z),"readiness":rd};pr.setdefault('exports',[]).append(row);pr['current_step']='export';store.save(pr);return row
