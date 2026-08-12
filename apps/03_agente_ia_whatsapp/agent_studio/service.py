from __future__ import annotations
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path
import argparse, base64, json, mimetypes, os, sys, tempfile, traceback
APP_DIR=Path(__file__).resolve().parents[1]; UI=APP_DIR/'ui'
if str(APP_DIR.parents[1]) not in sys.path: sys.path.insert(0,str(APP_DIR.parents[1]))
from . import store, simulator, exporter
from common.ai_gateway import overview as ai_overview, save_settings as ai_save
from common import ai_adoption
from common import native_context_consumer as native_context
from common.secret_store import secret_status, set_secret, delete_secret
from common import project_center as global_project_center
from r26.r26_core.agent_training import import_training_file, csv_template, jsonl_template

SERVICE_ID_DEFAULT='binario-v0210-app-03-agente-ia-whatsapp'

def import_training_into_project(pr:dict,filename:str,raw:bytes)->dict:
    filename=Path(filename or 'training.txt').name
    if not filename or len(filename)>180:raise ValueError('Nombre de archivo inválido')
    if len(raw)>12*1024*1024:raise ValueError('Archivo de entrenamiento demasiado grande (máx. 12 MB)')
    global_row=global_project_center.get(pr['id']) or {}
    training_raw=((global_row.get('metadata') or {}).get('folders') or {}).get('training')
    training_dir=Path(str(training_raw)).expanduser() if training_raw else (store.project_dir(pr['id'])/'training')
    with tempfile.TemporaryDirectory(prefix='binario-agent-training-') as td:
        source=Path(td)/filename;source.write_bytes(raw)
        result=import_training_file(source,training_dir,agent_id=pr['id'])
    knowledge=pr.setdefault('knowledge',[])
    documents=pr.setdefault('knowledge_documents',[])
    for idx,row in enumerate(result.get('qa') or [],1):
        knowledge.append({'id':f"kb-{result['id']}-{idx}",'title':(' · '.join(row.get('tags') or []) or f'FAQ importada {idx}'),'question':row.get('question',''),'answer':row.get('answer',''),'enabled':True,'source':{'training_id':result['id'],'file':result.get('source_name'),'priority':row.get('priority','normal')}})
    for idx,row in enumerate(result.get('documents') or [],1):
        documents.append({'id':row.get('id') or f"doc-{result['id']}-{idx}",'title':f"{result.get('source_name') or 'Documento'} · bloque {idx}",'text':row.get('text',''),'enabled':False,'source':{'training_id':result['id'],'file':result.get('source_name')}})
    pr['current_step']='knowledge';store.save(pr);store.log_event(pr['id'],'training.imported',{'training_id':result['id'],'qa':len(result.get('qa') or []),'document_chunks':len(result.get('documents') or [])})
    return {'training':result,'project':pr,'added':{'qa':len(result.get('qa') or []),'document_chunks':len(result.get('documents') or [])},'documents_require_approval':bool(result.get('documents'))}

def body(handler):
    n=int(handler.headers.get('Content-Length','0') or 0)
    if not n:return {}
    return json.loads(handler.rfile.read(n).decode('utf-8'))
def segments(path):return [x for x in path.strip('/').split('/') if x]

def bootstrap()->dict:
    return {'schema':'sbia-agent-studio-bootstrap-1.0','release':'0.21.0 R21','cross_app_context':'R24.2-wave-b','journey':['business','knowledge','intents','flow','model','simulate','tests','channel','publish','observe'],'projects':store.list_projects(),'ai':ai_overview(['03-agente-ia-whatsapp']),'channel_secret':secret_status('whatsapp-cloud'),'ai_adoption':ai_adoption.overview(['03-agente-ia-whatsapp']),'workspace_context':native_context.view('03-agente-ia-whatsapp')}

class H(SimpleHTTPRequestHandler):
    server_version='BinarioAgentStudio/0.21.0'
    def log_message(self,*a):pass
    def _json(self,obj,status=200):
        raw=json.dumps(obj,ensure_ascii=False,default=str).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def _text(self,text,status=200,ctype='text/plain; charset=utf-8'):
        raw=text.encode();self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        p=urlparse(self.path).path
        try:
            if p=='/api/health':return self._json({'service_id':os.environ.get('BINARIO_SERVICE_ID',SERVICE_ID_DEFAULT),'release':'0.21.0 R21','app_id':'03-agente-ia-whatsapp','root':str(APP_DIR)})
            if p=='/api/bootstrap':return self._json(bootstrap())
            if p=='/api/context':return self._json(native_context.view('03-agente-ia-whatsapp'))
            if p=='/api/hub-url':return self._json({'url':os.environ.get('BINARIO_HUB_URL','http://127.0.0.1:8780/')})
            if p=='/api/projects':return self._json({'projects':store.list_projects()})
            if p=='/api/training/template.csv':return self._text(csv_template(),ctype='text/csv; charset=utf-8')
            if p=='/api/training/template.jsonl':return self._text(jsonl_template(),ctype='application/x-ndjson; charset=utf-8')
            s=segments(p)
            if len(s)>=3 and s[0]=='api' and s[1]=='projects':
                pid=s[2]; pr=store.get(pid)
                if not pr:return self._json({'error':'Proyecto no encontrado'},404)
                if len(s)==3:return self._json(pr)
                if s[3]=='versions':return self._json({'versions':store.list_versions(pid)})
                if s[3]=='activity':return self._json({'activity':store.activity(pid)})
            if p.startswith('/api/'):return self._json({'error':'API no encontrada'},404)
            rel='index.html' if p in {'/','/editor','/agent','/studio','/index.html'} else p.lstrip('/')
            fp=(UI/rel).resolve()
            if UI.resolve() not in fp.parents and fp!=UI.resolve():return self._text('Forbidden',403)
            if fp.is_file():
                data=fp.read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(str(fp))[0] or 'application/octet-stream');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            self.send_response(302);self.send_header('Location','/');self.end_headers()
        except Exception as exc:self._json({'error':f'{type(exc).__name__}: {exc}'},500)
    def do_POST(self):
        p=urlparse(self.path).path
        try:
            data=body(self)
            if p=='/api/projects':
                pr=store.default_project(data.get('name') or data.get('business_name') or 'Nuevo agente',data.get('business_name') or '');store.log_event(pr['id'],'project.created',{});return self._json(pr,201)
            if p=='/api/ai/adoption': ai_adoption.save(data); return self._json(ai_adoption.overview(['03-agente-ia-whatsapp']))
            if p=='/api/ai/profile':
                prof=str(data.get('profile') or 'balanced');ai_save({'app_profiles':{'03-agente-ia-whatsapp':prof}});return self._json(ai_overview(['03-agente-ia-whatsapp']))
            if p=='/api/channel/secret':
                if data.get('delete'):return self._json(delete_secret('whatsapp-cloud'))
                return self._json(set_secret('whatsapp-cloud',data.get('value','')))
            s=segments(p)
            if len(s)>=4 and s[0]=='api' and s[1]=='projects':
                pid=s[2];action=s[3];pr=store.get(pid)
                if not pr:return self._json({'error':'Proyecto no encontrado'},404)
                if action=='save':
                    patch=data.get('project') if isinstance(data.get('project'),dict) else data
                    for k in ['name','status','current_step','business','knowledge','knowledge_documents','intents','variables','guardrails','flow','model','channel','tests','publish','observations']:
                        if k in patch:pr[k]=patch[k]
                    if data.get('rebuild_flow'):pr['flow']=store.build_flow(pr)
                    store.save(pr);store.log_event(pid,'project.saved',{'step':pr.get('current_step')});return self._json(pr)
                if action=='training-import':
                    encoded=str(data.get('content_b64') or '')
                    if not encoded:raise ValueError('Falta contenido del archivo')
                    try:raw=base64.b64decode(encoded,validate=True)
                    except Exception as exc:raise ValueError('Archivo base64 inválido') from exc
                    return self._json(import_training_into_project(pr,str(data.get('filename') or 'training.txt'),raw),201)
                if action=='training-approve-docs':
                    enabled=bool(data.get('enabled',True))
                    for row in pr.setdefault('knowledge_documents',[]):row['enabled']=enabled
                    store.save(pr);store.log_event(pid,'training.documents.approval',{'enabled':enabled,'count':len(pr.get('knowledge_documents') or [])});return self._json({'ok':True,'enabled':enabled,'count':len(pr.get('knowledge_documents') or []),'project':pr})
                if action=='snapshot':return self._json(store.snapshot(pid,data.get('label') or 'manual'))
                if action=='simulate':
                    res=simulator.simulate(pr,data.get('message',''),data.get('history') or []);pr.setdefault('tests',{})['last_simulation']=res;pr['current_step']='simulate';pr['model']['last_route']=res.get('route');store.save(pr);store.log_event(pid,'simulation',{'intent':res.get('intent'),'handoff':res.get('handoff')});return self._json(res)
                if action=='tests':
                    cases=data.get('cases') if isinstance(data.get('cases'),list) else pr.get('tests',{}).get('cases',[])
                    results=[]
                    for c in cases:
                        got=simulator.simulate(pr,c.get('message',''))
                        expected=c.get('expected_intent');ok=(not expected or got.get('intent')==expected) and (not c.get('expect_handoff') or got.get('handoff'))
                        results.append({'case':c,'result':got,'passed':bool(ok)})
                    summary={'total':len(results),'passed_count':sum(1 for x in results if x['passed']),'failed_count':sum(1 for x in results if not x['passed']),'passed':bool(results) and all(x['passed'] for x in results),'results':results}
                    pr.setdefault('tests',{})['cases']=cases;pr['tests']['last_run']=summary;pr['current_step']='tests';store.save(pr);store.log_event(pid,'tests.run',{'passed':summary['passed'],'total':summary['total']});return self._json(summary)
                if action=='readiness':
                    r=exporter.readiness(pr);pr.setdefault('publish',{})['readiness']=r['score'];store.save(pr);return self._json(r)
                if action=='export':
                    r=exporter.export(pr);pr.setdefault('publish',{})['last_export']=r;pr['publish']['readiness']=r['readiness']['score'];pr['publish']['status']='exported';pr['current_step']='publish';store.save(pr);store.snapshot(pid,'export');store.log_event(pid,'export.created',{'zip':r['zip']});return self._json(r)
                if action=='channel':
                    ch=data.get('channel') or data
                    for k in ['type','phone_number_id','waba_id','webhook_url','centric_channel']:
                        if k in ch:pr.setdefault('channel',{})[k]=str(ch[k] or '')
                    token=secret_status('whatsapp-cloud').get('configured'); typ=pr['channel'].get('type','sandbox')
                    if typ=='sandbox':status='ready'
                    elif typ=='centric-flowbot':status='ready' if pr['channel'].get('centric_channel') else 'draft'
                    else:status='configured' if token and pr['channel'].get('phone_number_id') and pr['channel'].get('waba_id') else 'draft'
                    pr['channel']['status']=status;pr['current_step']='channel';store.save(pr);store.log_event(pid,'channel.updated',{'type':typ,'status':status});return self._json({'channel':pr['channel'],'secret':secret_status('whatsapp-cloud')})
                if action=='observe':
                    item={'timestamp':store.now(),'kind':data.get('kind') or 'note','text':str(data.get('text') or ''),'metric':data.get('metric')};pr.setdefault('observations',[]).append(item);pr['current_step']='observe';store.save(pr);store.log_event(pid,'observation.added',item);return self._json(item,201)
            return self._json({'error':'Ruta no encontrada'},404)
        except Exception as exc:
            traceback.print_exc();return self._json({'error':f'{type(exc).__name__}: {exc}'},500)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=8785);ap.add_argument('--no-browser',action='store_true');a=ap.parse_args()
    srv=ThreadingHTTPServer((a.host,a.port),H);print(f'Agent Studio R21 http://{a.host}:{a.port}',flush=True)
    try:srv.serve_forever()
    except KeyboardInterrupt:pass
    finally:srv.server_close()
if __name__=='__main__':main()
