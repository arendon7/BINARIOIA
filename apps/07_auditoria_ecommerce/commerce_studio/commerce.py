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

def add_html(pr,url,html):
 url=wi.normalize_url(url or pr.get('store',{}).get('url') or 'https://manual.local/');p=wi.parse_html(html,url);f={'url':url,'requested_url':url,'status':200,'content_type':'text/html','bytes':len(str(html).encode()),'elapsed_ms':None,'sha256':hashlib.sha256(str(html).encode()).hexdigest(),'source':'manual'};a=wi.audit_page(p,f);row={'url':url,'fetch':f,'parsed':p,'audit':a,'page_type':wi.classify_page(url,p),'captured_at':datetime.now(timezone.utc).isoformat(),'html':str(html)};pr['pages']=[x for x in pr.get('pages') or [] if x.get('url')!=url]+[row];pr['store']['url']=pr['store'].get('url') or url;pr['current_step']='crawl';store.save(pr);return {k:v for k,v in row.items() if k!='html'}
def crawl(pr,max_pages=None):
 url=wi.normalize_url(pr.get('store',{}).get('url'));n=int(max_pages or pr.get('store',{}).get('max_pages') or 8);pr['pages']=wi.crawl(url,n);pr['store']['max_pages']=n;pr['current_step']='crawl';store.snapshot(pr['id'],'crawl');store.save(pr);return {'pages':[{k:v for k,v in x.items() if k!='html'} for x in pr['pages']],'ok':sum(1 for x in pr['pages'] if not x.get('error'))}
def map_funnel(pr):
 stages={k:[] for k in ['home','category','product','cart','checkout']}
 for p in pr.get('pages') or []:
  t=p.get('page_type');
  if t in stages:stages[t].append(p.get('url'))
 leaks=[]
 if not stages['product']:leaks.append({'id':'no-product','stage':'product','severity':'high','title':'No se capturó una ficha de producto','action':'Añadir o rastrear una URL de producto real.'})
 if not stages['cart']:leaks.append({'id':'no-cart','stage':'cart','severity':'medium','title':'Carrito no observable en el crawl','action':'Validar manualmente fricción, persistencia y costos sorpresa del carrito.'})
 if not stages['checkout']:leaks.append({'id':'no-checkout','stage':'checkout','severity':'medium','title':'Checkout no observable en el crawl','action':'Validar pasos, campos, medios de pago, confianza y abandono del checkout.'})
 for p in pr.get('pages') or []:
  if p.get('audit') and p['audit'].get('score',100)<65:leaks.append({'id':f"weak-{len(leaks)+1}",'stage':p.get('page_type'),'severity':'high','title':f"Página débil: {p.get('page_type')}",'action':f"Corregir hallazgos en {p.get('url')}",'url':p.get('url')})
 pr['funnel']={'stages':stages,'leaks':leaks};pr['current_step']='journey';store.save(pr);return pr['funnel']
def audit(pr):
 pages=[x for x in pr.get('pages') or [] if x.get('audit')]
 if not pages:raise RuntimeError('Primero captura o rastrea la tienda.')
 if not pr.get('funnel',{}).get('stages'):map_funnel(pr)
 home=next((x for x in pages if x.get('page_type')=='home'),pages[0]);ctx=native_context.view('07-auditoria-ecommerce');ctx_text=native_context.text('07-auditoria-ecommerce',['FACT','RISK','CONSTRAINT','DECISION','PREFERENCE'],20);legacy=engine.run({'project_name':pr.get('name'),'url':home.get('url'),'html':home.get('html',''),'product':pr.get('store',{}).get('product'),'workspace_context':ctx_text})
 dims=['conversion','trust','accessibility','content','hierarchy'];webscores={d:round(sum(float(x['audit']['scores'].get(d,0)) for x in pages)/len(pages),1) for d in dims};scores=dict(legacy.get('scores') or {});scores.update({f'web_{k}':v for k,v in webscores.items()});issues=[]
 for p in pages:
  issues.extend([{**x,'url':p.get('url'),'page_type':p.get('page_type')} for x in p['audit'].get('issues') or []])
 for x in pr.get('funnel',{}).get('leaks') or []:issues.append({'id':x['id'],'title':x['title'],'severity':x['severity'],'why':x.get('stage'),'recommendation':x['action'],'url':x.get('url')})
 score=round(sum(float(v) for v in scores.values())/len(scores),1) if scores else 0;backlog=[]
 for i in issues:
  backlog.append({'id':f'ec-{len(backlog)+1:03d}','title':i.get('title'),'stage':i.get('page_type') or i.get('why'),'url':i.get('url'),'priority':'P0' if i.get('severity')=='high' else 'P1','action':i.get('recommendation'),'owner':'Por asignar','status':'planned'})
 pr['audit'].update({'status':'generated','score':score,'scores':scores,'issues':issues,'legacy':legacy,'reviewed':False,'workspace_context':native_context.metadata('07-auditoria-ecommerce'),'workspace_context_text':ctx_text});pr['backlog']=backlog[:24];pr['current_step']='leaks';store.save(pr);return pr['audit']
def rewrite_product(pr):
 if not pr.get('audit',{}).get('legacy'):audit(pr)
 d=next((x for x in pr['audit']['legacy'].get('deliverables') or [] if 'producto' in x.get('title','').lower()),None);text=(d or {}).get('content') or ''
 if not text:text=f"{pr.get('store',{}).get('product') or 'Producto'}\nPromesa principal verificable.\nBeneficios con evidencia.\nLogística, garantía y CTA claro."
 pr['product_rewrite']=text;pr['current_step']='rewrite';store.save(pr);return {'product':pr.get('store',{}).get('product'),'content':text}
def review(pr,notes=''):
 if not pr.get('audit',{}).get('legacy'):raise RuntimeError('Primero ejecuta la auditoría.')
 pr['audit']['reviewed']=True;pr['audit']['review_notes']=str(notes or '');pr['audit']['status']='reviewed';pr['current_step']='prioritize';store.snapshot(pr['id'],'audit-reviewed');store.save(pr);return pr['audit']
def compare(pr,url=None):
 u=wi.normalize_url(url or pr.get('store',{}).get('competitor_url'));f=wi.fetch_url(u);p=wi.parse_html(f['html'],f['url']);a=wi.audit_page(p,f);out={'url':u,'score':a['score'],'scores':a['scores'],'issues':a['issues'],'delta_vs_store':round(float(pr.get('audit',{}).get('score') or 0)-a['score'],1) if pr.get('audit',{}).get('score') else None};pr['store']['competitor_url']=u;pr['comparison']=out;store.save(pr);return out
def readiness(pr):
 a=pr.get('audit') or {};checks={'store':bool(pr.get('store',{}).get('url')),'pages':len(pr.get('pages') or [])>=1,'journey':bool(pr.get('funnel',{}).get('stages')),'audit':bool(a.get('legacy')),'rewrite':bool(pr.get('product_rewrite')),'reviewed':bool(a.get('reviewed')),'backlog':len(pr.get('backlog') or [])>=2};score=round(sum(checks.values())/len(checks)*100);out={'checks':checks,'score':score,'ready':score>=80 and checks['audit'] and checks['rewrite']};pr['audit']['readiness']=score;store.save(pr);return out
def handoff(pr,target):
 if target not in {'proposal','research','documents','app-factory'}:raise ValueError('Handoff no soportado')
 d=store.pdir(pr['id'])/'handoffs';d.mkdir(exist_ok=True);payload={'schema':'sbia-handoff-1.0','source_app':'07-auditoria-ecommerce','target':target,'project_id':pr['id'],'name':pr['name'],'store':pr.get('store'),'funnel':pr.get('funnel'),'audit':{k:v for k,v in (pr.get('audit') or {}).items() if k!='legacy'},'backlog':pr.get('backlog'),'product_rewrite':pr.get('product_rewrite'),'human_approval_required':True};p=d/f'{target}.json';p.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8');pr.setdefault('handoffs',{})[target]=str(p);store.save(pr);return {'target':target,'path':str(p),'payload':payload}
def export(pr):
 rd=readiness(pr);d=store.export_dir(pr['id']);d.mkdir(parents=True,exist_ok=True);md=d/'ecommerce-audit.md';js=d/'commerce-project.json';z=d/'commerce-intelligence-package.zip';a=pr.get('audit') or {};lines=[f"# Commerce Studio · {pr['name']}",'',f"**Tienda:** {pr.get('store',{}).get('url')}",f"**Producto:** {pr.get('store',{}).get('product')}",f"**Readiness:** {rd['score']}%",f"**Score:** {a.get('score','—')}/100",'', '## Buyer journey']+[f"- **{k}:** {len(v)} página(s)" for k,v in (pr.get('funnel',{}).get('stages') or {}).items()]+['','## Fugas']+[f"- **{x.get('priority')} · {x.get('title')}** — {x.get('action')}" for x in pr.get('backlog') or []]+['','## Ficha reescrita',pr.get('product_rewrite') or 'Pendiente'];md.write_text('\n'.join(lines)+'\n',encoding='utf-8');js.write_text(json.dumps(pr,indent=2,ensure_ascii=False),encoding='utf-8')
 with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zz:zz.write(md,md.name);zz.write(js,js.name)
 row={'created_at':datetime.now(timezone.utc).isoformat(),'markdown':str(md),'json':str(js),'zip':str(z),'readiness':rd};pr.setdefault('exports',[]).append(row);pr['current_step']='export';store.save(pr);return row
