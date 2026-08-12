from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import json,os,re
from common import project_center, project_storage
from common import native_context_consumer as native_context
APP_ID='02-cazador-webs'
def now():return datetime.now(timezone.utc).isoformat()
def legacy_root():
 p=Path(os.environ.get('BINARIO_WEB_STUDIO_HOME') or (Path.home()/'Documents'/'Binario IA'/'Web Studio')).expanduser();p.mkdir(parents=True,exist_ok=True);return p
def data_root():
 # Compatibility alias only; active state lives in canonical Project Storage.
 return legacy_root()
def _safe(pid):
 if not re.fullmatch(r'prj-[a-f0-9]{12}',str(pid or '')):raise ValueError('project_id inválido')
 return str(pid)
def pdir(pid):
 pid=_safe(pid);target=project_storage.app_state_dir(pid,APP_ID);legacy=legacy_root()/pid
 if legacy.is_dir() and legacy.resolve()!=target.resolve():project_storage.migrate_legacy_state(pid,APP_ID,legacy)
 return target
def export_dir(pid):return project_storage.app_export_dir(_safe(pid),APP_ID)
def path(pid):return pdir(pid)/'project.json'
def create(name='Nuevo sitio',url=''):
 b=native_context.claim_runtime_project(APP_ID)
 if b and path(b['id']).exists():b=None
 if b:project_center.update(b['id'],{'name':name,'metadata':{**(b.get('metadata') or {}),'studio':'web-studio-r18','storage':'canonical-project'}})
 else:b=project_center.create(name,APP_ID,metadata={'studio':'web-studio-r18','storage':'canonical-project'})
 r={'schema':'sbia-web-studio-2.0','id':b['id'],'global_project_id':b['id'],'name':name,'status':'active','current_step':'target','created_at':now(),'updated_at':now(),'target':{'url':url,'max_pages':6,'competitor_url':''},'pages':[],'screenshots':[],'audit':{'status':'draft','scores':{},'issues':[],'summary':'','legacy':None,'reviewed':False,'review_notes':'','readiness':0},'backlog':[],'comparison':None,'handoffs':{},'exports':[],'versions':[]};save(r);snapshot(r['id'],'created');return r
def save(r):
 r['updated_at']=now();p=path(r['id']);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8');tmp.replace(p)
 try:project_center.update(r['id'],{'name':r.get('name'),'status':r.get('status','active'),'current_step':r.get('current_step'),'metadata':{'studio':'web-studio-r18','storage':'canonical-project','pages':len(r.get('pages') or []),'audit_status':r.get('audit',{}).get('status')}})
 except Exception:pass
 return r
def get(pid):
 p=path(pid)
 try:return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None
 except Exception:return None
def list_projects():
 out=[]
 for global_row in project_center.list_projects(APP_ID):
  try:r=get(global_row.get('id'))
  except Exception:r=None
  if not r:continue
  out.append({'id':r.get('id'),'name':r.get('name'),'url':r.get('target',{}).get('url'),'pages':len(r.get('pages') or []),'score':r.get('audit',{}).get('score'),'updated_at':r.get('updated_at')})
 return sorted(out,key=lambda x:x.get('updated_at') or '',reverse=True)
def snapshot(pid,label='snapshot'):
 r=get(pid)
 if not r:raise FileNotFoundError(pid)
 d=pdir(pid)/'versions';d.mkdir(exist_ok=True);stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f');safe=re.sub(r'[^a-z0-9-]+','-',label.lower()).strip('-') or 'snapshot';p=d/f'{stamp}-{safe}.json';p.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8');m={'id':p.stem,'label':label,'created_at':now(),'path':str(p)};r['versions']=(r.get('versions') or [])[-49:]+[m];save(r);return m
