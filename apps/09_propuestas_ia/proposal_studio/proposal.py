from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import json,zipfile,re,sys,hashlib
APP_DIR=Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:sys.path.insert(0,str(APP_DIR))
import engine
from . import store
from common import ai_adoption
from common import native_context_consumer as native_context

def recalc(pr):
    p=pr['pricing'];sub=max(0,float(p.get('subtotal') or 0));disc=max(0,float(p.get('discount') or 0));tax=max(0,float(p.get('tax') or 0));net=max(0,sub-disc);p['total']=round(net+tax,2);store.save(pr);return p
def add_source(pr,title,content,source='manual'):
    c=str(content or '').strip()
    if not c:raise ValueError('La fuente está vacía.')
    row={'id':f"src-{len(pr.get('sources') or [])+1:03d}",'title':str(title or 'Fuente'),'source':source,'content':c,'sha256':hashlib.sha256(c.encode()).hexdigest(),'added_at':datetime.now(timezone.utc).isoformat()};pr.setdefault('sources',[]).append(row);store.save(pr);return row
def generate(pr):
    s=pr['scope'];p=pr['pricing'];payload={'client':pr.get('client'),'project_name':pr.get('name'),'problem':pr.get('brief',{}).get('problem'),'objective':pr.get('brief',{}).get('objective'),'deliverables':s.get('deliverables'),'timeline':p.get('timeline'),'price':f"{p.get('currency','COP')} {p.get('total',0):,.0f}",'assumptions':s.get('assumptions'),'phases':pr.get('solution',{}).get('phases')}
    r=engine.run(payload);md=(r.get('metadata') or {}).get('proposal_markdown') or ((r.get('deliverables') or [{}])[0].get('content') if r.get('deliverables') else '')
    exclusions=s.get('exclusions') or []
    if exclusions:md += '\n\n## Fuera de alcance\n'+'\n'.join(f'- {x}' for x in exclusions)
    if p.get('terms'):md += '\n\n## Condiciones comerciales\n'+str(p.get('terms'))
    context_sources=native_context.source_rows('09-propuestas-ia',['FACT','DECISION','CONSTRAINT','RISK','OPEN_QUESTION','DELIVERABLE'],20)
    facts={'client':pr.get('client'),'problem':pr.get('brief',{}).get('problem'),'objective':pr.get('brief',{}).get('objective'),'scope':s,'solution':pr.get('solution'),'pricing':p,'sources':[{'title':x.get('title'),'content':x.get('content'),'source':x.get('source')} for x in pr.get('sources',[])[:12]],'workspace_context':context_sources}
    prompt='HECHOS Y RESTRICCIONES\n'+json.dumps(facts,ensure_ascii=False,indent=2)+'\n\nBORRADOR DETERMINÍSTICO\n'+md+'\n\nMejora redacción, estructura y claridad comercial. Devuelve Markdown completo. No cambies cifras, alcance, exclusiones, fuentes ni promesas.'
    adoption=ai_adoption.run('09-propuestas-ia','proposal-draft',prompt,local_text=md,system='Eres editor de propuestas de Binario IA. No inventes cifras, fechas, entregables o capacidades. Conserva la sustancia aprobada.',project_id=pr.get('id'))
    md=adoption.get('text') or md
    pr['draft']={'markdown':md,'status':'generated','generated_at':datetime.now(timezone.utc).isoformat(),'engine_result':r,'ai_adoption':adoption,'workspace_context':native_context.metadata('09-propuestas-ia')};pr['current_step']='draft';pr['approval']['status']='draft';store.save(pr);return pr['draft']
def review(pr,notes=''):
    if not pr.get('draft',{}).get('markdown'):raise RuntimeError('Primero genera la propuesta.')
    pr['approval'].update({'status':'reviewed','notes':str(notes or '')});pr['draft']['status']='reviewed';pr['current_step']='review';store.snapshot(pr['id'],'reviewed');store.save(pr);return pr['approval']
def approve(pr,approved_by,notes=''):
    if pr.get('approval',{}).get('status')!='reviewed':raise RuntimeError('La propuesta debe estar revisada antes de aprobarse.')
    pr['approval'].update({'status':'approved','approved_by':str(approved_by or 'Aprobador'),'notes':str(notes or pr['approval'].get('notes') or ''),'approved_at':datetime.now(timezone.utc).isoformat()});pr['draft']['status']='approved';pr['current_step']='approve';store.snapshot(pr['id'],'approved');store.save(pr);return pr['approval']
def add_followup(pr,note,status='pending'):
    row={'id':f"follow-{len(pr.get('followups') or [])+1:03d}",'note':str(note or ''),'status':status,'created_at':datetime.now(timezone.utc).isoformat()};pr.setdefault('followups',[]).append(row);pr['current_step']='followup';store.save(pr);return row
def readiness(pr):
    s=pr.get('scope') or {};p=pr.get('pricing') or {};checks={'client':bool(pr.get('client')),'problem':bool(pr.get('brief',{}).get('problem')),'deliverables':len(s.get('deliverables') or [])>=1,'pricing':float(p.get('total') or 0)>0,'draft':bool(pr.get('draft',{}).get('markdown')),'reviewed':pr.get('approval',{}).get('status') in {'reviewed','approved'}};score=round(sum(checks.values())/len(checks)*100);return {'checks':checks,'score':score,'ready':score>=80 and checks['draft'] and checks['reviewed']}
def document_spec(pr):
    d=store.pdir(pr['id'])/'handoffs';d.mkdir(exist_ok=True);p=d/'document-spec.json';spec={'schema':'sbia-document-spec-1.0','title':pr.get('name'),'objective':f"Propuesta comercial/técnica para {pr.get('client')}",'blocks':[{'type':'markdown','title':'Propuesta','content':pr.get('draft',{}).get('markdown','')}],'sources':pr.get('sources') or [],'metadata':{'source_app':'09-propuestas-ia','project_id':pr['id'],'approval':pr.get('approval'),'pricing':pr.get('pricing')}};p.write_text(json.dumps(spec,indent=2,ensure_ascii=False),encoding='utf-8');return {'path':str(p),'spec':spec}
def export(pr):
    rd=readiness(pr);d=store.export_dir(pr['id']);d.mkdir(parents=True,exist_ok=True);md=d/'propuesta.md';js=d/'propuesta.json';z=d/'propuesta-package.zip';md.write_text(pr.get('draft',{}).get('markdown') or '',encoding='utf-8');js.write_text(json.dumps(pr,indent=2,ensure_ascii=False),encoding='utf-8');ds=document_spec(pr)
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zz:zz.write(md,md.name);zz.write(js,js.name);zz.write(ds['path'],'handoffs/document-spec.json')
    row={'created_at':datetime.now(timezone.utc).isoformat(),'markdown':str(md),'json':str(js),'zip':str(z),'document_spec':ds['path'],'readiness':rd};pr.setdefault('exports',[]).append(row);pr['current_step']='export';store.save(pr)
    lineage=native_context.record_output('09-propuestas-ia',pr.get('name') or 'Propuesta',output_type='proposal',ref=str(z),output_id=f"proposal:{pr.get('id')}:{len(pr.get('exports') or [])}",metadata={'readiness':rd,'approval':(pr.get('approval') or {}).get('status')},idempotency_key=f"proposal-export:{pr.get('id')}:{len(pr.get('exports') or [])}")
    if lineage:row['context_lineage']=lineage
    return row
