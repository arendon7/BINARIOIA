from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, zipfile, sys
APP_DIR=Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:sys.path.insert(0,str(APP_DIR))
import engine
from common import content_intelligence as ci
from common import native_context_consumer as native_context
from . import store

def add_item(pr,d):
    x=ci.normalize_item(d,d.get('source') or 'manual');pr['content']=[i for i in pr.get('content',[]) if i.get('id')!=x['id']]+[x];pr['current_step']='evidence';store.save(pr);return x
def analyze(pr):
    items=pr.get('content') or [];p=pr['profile']
    if not items:raise RuntimeError('Añade al menos una pieza o evidencia de contenido.')
    ag=ci.aggregate(items);ctx=native_context.text('06-auditoria-marca-personal',['FACT','PREFERENCE','DECISION','CONSTRAINT'],20);posts='\n'.join((x.get('title') or x.get('text') or '')[:250] for x in items[:25]);legacy=engine.run({'brand_name':p.get('brand_name') or pr['name'],'positioning':p.get('positioning') or '','audience':p.get('audience') or '','proof':p.get('proof') or '','channels':p.get('channels') or '','posts':posts,'offer':p.get('offer') or '','cta':p.get('cta') or ''})
    pr['analysis'].update({'status':'generated','scores':ag['scores'],'pillars':ag['pillars'],'keywords':ag['keywords'],'items':ag['items'],'legacy':legacy,'reviewed':False,'workspace_context':native_context.metadata('06-auditoria-marca-personal'),'workspace_context_text':ctx});pr['ideas']=ci.ideas(ag['pillars'],p.get('audience',''),p.get('offer',''),18)
    local_brief='Pilares: '+', '.join(x.get('name','') for x in ag.get('pillars',[]))+' · Ideas locales: '+ '; '.join(x.get('title','') for x in pr.get('ideas',[])[:6])+((' · Contexto Workspace: '+ctx) if ctx else '')
    pr['analysis']['ai_strategy']=ci.ai_strategy('06-auditoria-marca-personal',pr,ag,local_brief)
    pr['current_step']='content-system';store.save(pr);return pr['analysis']
def build_calendar(pr,days=30,cadence=4):
    if not pr.get('ideas'):raise RuntimeError('Primero genera el sistema de contenido.')
    pr['calendar"]=ci.calendar(pr['ideas'],days=int(days),cadence=int(cadence));pr['current_step']='calendar';store.save(pr);return pr['calendar']
def review(pr,notes=''):
    if not pr.get('analysis',{}).get('legacy'):raise RuntimeError('Primero ejecuta la auditoría.')
    pr['analysis'].update({'reviewed':True,'review_notes':str(notes or ''),'status':'reviewed'});store.snapshot(pr['id'],'reviewed');store.save(pr);return pr['analysis']
def add_experiment(pr,d):
    x=ci.experiment(d.get('name') or 'Experimento',d.get('hypothesis') or '',d.get('metric') or 'engagement_rate');pr['experiments'].append(x);store.save(pr);return x
def log_performance(pr,d):
    row={'id':f"perf-{len(pr.get('performance') or [])+1:03d}",'content_id':d.get('content_id'),'date':d.get('date') or datetime.now(timezone.utc).date().isoformat(),'metrics':d.get('metrics') if isinstance(d.get('metrics'),dict) else {},'notes':d.get('notes','')};pr['performance'].append(row);store.save(pr);return row
def readiness(pr):
    a=pr['analysis'];checks={'positioning':bool(pr['profile'].get('positioning')),'content':len(pr.get('content') or [])>=2,'analyzed':bool(a.get('legacy')),'reviewed':bool(a.get('reviewed')),'pillars':len(a.get('pillars') or [])>=1,'calendar':len(pr.get('calendar') or [])>=3};score=round(sum(checks.values())/len(checks)*100);out={'checks':checks,'score':score,'ready':score>=80 and checks['analyzed'] and checks['reviewed']};a['readiness']=score;store.save(pr);return out
def handoff(pr,target):
    if target not in {'video','research','documents','proposal'}:raise ValueError('Handoff no soportado')
    d=store.pdir(pr['id'])/'handoffs';d.mkdir(exist_ok=True);payload={'schema':'sbia-handoff-1.0','source_app':'06-auditoria-marca-personal','target':target,'project_id':pr['id'],'profile':pr.get('profile'),'pillars':pr['analysis'].get('pillars'),'ideas':pr.get('ideas'),'calendar':pr.get('calendar'),'human_approval_required':True};p=d/f'{target}.json';p.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8');pr['handoffs'][target]=str(p);store.save(pr);return {'target':target,'path':str(p),'payload':payload}
def export(pr):
    rd=readiness(pr);d=store.export_dir(pr['id']);d.mkdir(parents=True,exist_ok=True);md=d/'brand-content-system.md';js=d/'brand-project.json';z=d/'brand-content-package.zip';a=pr['analysis'];lines=[f"# Brand Studio · {pr['name']}",'',f"**Readiness:** {rd['score']}%",'', '## Pilares']+[f"- {x.get('name')} · evidencia {x.get('evidence_items')}" for x in a.get('pillars') or []]+['','## Ideas']+[f"- {x.get('title')} · {x.get('format')}" for x in pr.get('ideas') or []]+['','## Calendario']+[f"- {x.get('date')} · {x.get('title')}" for x in pr.get('calendar') or []];md.write_text('\n'.join(lines)+'\n',encoding='utf-8');js.write_text(json.dumps(pr,indent=2,ensure_ascii=False),encoding='utf-8')
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zz:zz.write(md,md.name);zz.write(js,js.name)
    row={'created_at':datetime.now(timezone.utc).isoformat(),'markdown':str(md),'json':str(js),'zip':str(z),'readiness':rd};pr['exports'].append(row);pr['current_step']='export';store.save(pr);return row
