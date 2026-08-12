from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import json,zipfile,hashlib,sys
APP_DIR=Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:sys.path.insert(0,str(APP_DIR))
import engine
from common import web_intelligence as wi
from common import native_context_consumer as native_context
from . import store

def _public_page(row):
 r={k:v for k,v in row.items() if k!='html'};return r

def add_html(pr,url,html,label='manual'):
 url=wi.normalize_url(url or pr.get('target',{}).get('url') or 'https://manual.local/');parsed=wi.parse_html(html,url);fetch={'url':url,'requested_url':url,'status':200,'content_type':'text/html','bytes':len(str(html).encode()),'elapsed_ms':None,'sha256':hashlib.sha256(str(html).encode()).hexdigest(),'source':label};audit=wi.audit_page(parsed,fetch);row={'url':url,'fetch':fetch,'parsed':parsed,'audit':audit,'page_type':wi.classify_page(url,parsed),'captured_at':datetime.now(timezone.utc).isoformat(),'html':str(html)}
 pr['pages']=[x for x in pr.get('pages',[]) if x.get('url')!=url]+[row];pr['target']['url']=pr['target'].get('url') or url;pr['current_step']='evidence';store.save(pr);return _public_page(row)

def crawl(pr,max_pages=None):
 url=wi.normalize_url(pr.get('target',{}).get('url'));n=int(max_pages or pr.get('target',{}).get('max_pages') or 6);rows=wi.crawl(url,n);clean=[]
 for row in rows:
  if row.get('html') is not None:clean.append(row)
  else:clean.append(row)
 pr['pages']=clean;pr['target']['max_pages']=n;pr['current_step']='crawl';store.snapshot(pr['id'],'crawl');store.save(pr);return {'pages':[_public_page(x) for x in clean],'ok':sum(1 for x in clean if not x.get('error')),'failed':sum(1 for x in clean if x.get('error'))}

def analyze(pr):
 pages=[x for x in pr.get('pages') or [] if x.get('audit')]
 if not pages:raise RuntimeError('Primero captura o rastrea al menos una página.')
 dims=['hierarchy','content','conversion','accessibility','trust'];scores={d:round(sum(float(x['audit']['scores'].get(d,0)) for x in pages)/len(pages),1) for d in dims};issues=[]
 for pg in pages:
  for i in pg['audit'].get('issues') or []:issues.append({**i,'url':pg.get('url'),'page_type':pg.get('page_type')})
 severity={'high':0,'medium':1,'low':2};issues.sort(key=lambda x:(severity.get(x.get('severity'),9),x.get('title','')))
 home=next((x for x in pages if x.get('page_type')=='home'),pages[0]);ctx=native_context.view('02-cazador-webs');ctx_text=native_context.text('02-cazador-webs',['FACT','CONSTRAINT','RISK','DECISION','PREFERENCE'],20);legacy=engine.run({'project_name':pr.get('name'),'url':home.get('url'),'html':home.get('html',''),'workspace_context':ctx_text})
 backlog=[];seen=set()
 for i in issues:
  key=(i.get('id'),i.get('url'))
  if key in seen:continue
  seen.add(key);backlog.append({'id':f'wb-{len(backlog)+1:03d}','title':i.get('title'),'url':i.get('url'),'severity':i.get('severity'),'priority':'P0' if i.get('severity')=='high' else 'P1','action':i.get('recommendation'),'status':'planned','owner':'Por asignar'})
 for f in legacy.get('findings') or []:
  if len(backlog)>=18:break
  backlog.append({'id':f'wb-{len(backlog)+1:03d}','title':f.get('title'),'url':home.get('url'),'severity':f.get('severity','opportunity'),'priority':'P1','action':f.get('recommendation') or f.get('detail'),'status':'planned','owner':'Por asignar'})
 score=round(sum(scores.values())/len(scores),1);pr['audit'].update({'status':'generated','score':score,'scores':scores,'issues':issues,'summary':f'Auditoría de {len(pages)} páginas con score observable {score}/100.','legacy':legacy,'reviewed':False,'workspace_context':native_context.metadata('02-cazador-webs'),'workspace_context_text':ctx_text});pr['backlog']=backlog;pr['current_step']='audit';store.save(pr);return pr['audit']

def review(pr,notes=''):
 if not pr.get('audit',{}).get('legacy'):raise RuntimeError('Primero ejecuta la auditoría.')
 pr['audit']['reviewed']=True;pr['audit']['review_notes']=str(notes or '');pr['audit']['status']='reviewed';pr['current_step']='backlog';store.snapshot(pr['id'],'audit-reviewed');store.save(pr);return pr['audit']

def compare(pr,url=None):
 target=wi.normalize_url(url or pr.get('target',{}).get('competitor_url'))
 f=wi.fetch_url(target);p=wi.parse_html(f['html'],f['url']);a=wi.audit_page(p,f);base=float(pr.get('audit',{}).get('score') or 0);out={'url':target,'score':a['score'],'scores':a['scores'],'issues':a['issues'],'delta_vs_project':round(base-a['score'],1) if base else None,'captured_at':datetime.now(timezone.utc).isoformat()};pr['target']['competitor_url']=target;pr['comparison']=out;store.save(pr);return out

def screenshot(pr):
 url=wi.normalize_url(pr.get('target',{}).get('url'));d=store.pdir(pr['id'])/'screenshots';p=d/f"capture-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png";r=wi.capture_screenshot(url,p)
 if r.get('ok'):pr.setdefault('screenshots',[]).append({'path':r['path'],'url':url,'created_at':datetime.now(timezone.utc).isoformat()});store.save(pr)
 return r

def readiness(pr):
 a=pr.get('audit') or {};checks={'target':bool(pr.get('target',{}).get('url')),'pages':len(pr.get('pages') or [])>=1,'audit':bool(a.get('legacy')),'reviewed':bool(a.get('reviewed')),'backlog':len(pr.get('backlog') or [])>=3};score=round(sum(checks.values())/len(checks)*100);out={'checks':checks,'score':score,'ready':score>=80 and checks['audit'] and checks['reviewed'] and checks['backlog']};pr['audit']['readiness']=score;store.save(pr);return out

def handoff(pr,target):
 if target not in {'proposal','app-factory','documents','research'}:raise ValueError('Handoff no soportado')
 d=store.pdir(pr['id'])/'handoffs';d.mkdir(exist_ok=True);payload={'schema':'sbia-handoff-1.0','source_app':'02-cazador-webs','target':target,'project_id':pr['id'],'name':pr['name'],'target_url':pr.get('target',{}).get('url'),'audit':{k:v for k,v in (pr.get('audit') or {}).items() if k!='legacy'},'backlog':pr.get('backlog'),'pages':[{'url':x.get('url'),'page_type':x.get('page_type'),'audit':x.get('audit'),'sha256':x.get('fetch',{}).get('sha256')} for x in pr.get('pages') or []],'human_approval_required':True};p=d/f'{target}.json';p.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8');pr.setdefault('handoffs',{})[target]=str(p);store.save(pr);return {'target':target,'path':str(p),'payload':payload}

def export(pr):
 rd=readiness(pr);d=store.export_dir(pr['id']);d.mkdir(parents=True,exist_ok=True);md=d/'web-audit.md';js=d/'web-project.json';z=d/'web-intelligence-package.zip';a=pr.get('audit') or {};lines=[f"# Web Studio · {pr['name']}",'',f"**URL:** {pr.get('target',{}).get('url')}",f"**Readiness:** {rd['score']}%",f"**Score:** {a.get('score','—')}/100",'', '## Dimensiones']+[f"- **{k}:** {v}/100" for k,v in (a.get('scores') or {}).items()]+['','## Páginas']+[f"- {x.get('page_type')} · {x.get('url')} · score {x.get('audit',{}).get('score','—')}" for x in pr.get('pages') or []]+['','## Backlog']+[f"- **{x.get('priority')} · {x.get('title')}** — {x.get('action')}" for x in pr.get('backlog') or []];md.write_text('\n'.join(lines)+'\n',encoding='utf-8');js.write_text(json.dumps(pr,indent=2,ensure_ascii=False),encoding='utf-8')
 with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zz:
  zz.write(md,md.name);zz.write(js,js.name)
  for x in pr.get('screenshots') or []:
   p=Path(x.get('path',''))
   if p.is_file():zz.write(p,f'screenshots/{p.name}')
 row={'created_at':datetime.now(timezone.utc).isoformat(),'markdown':str(md),'json':str(js),'zip':str(z),'readiness':rd};pr.setdefault('exports',[]).append(row);pr['current_step']='export';store.save(pr);return row
