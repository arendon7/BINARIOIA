from __future__ import annotations
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import argparse,json,os,sys
from urllib.parse import urlparse
from .models import DocumentSpec
from .quality import evaluate
from .pipeline import DocumentsPipeline
BINARIO_ROOT=Path(__file__).resolve().parents[3]
if str(BINARIO_ROOT) not in sys.path:sys.path.insert(0,str(BINARIO_ROOT))
from common import native_context_consumer as native_context
APP_ID="11-documentos-ia"

def attach_workspace_context(spec:DocumentSpec,out:Path)->dict:
    meta=native_context.metadata(APP_ID);rows=native_context.source_rows(APP_ID,["FACT","DECISION","CONSTRAINT","DELIVERABLE","PREFERENCE","RISK","OPEN_QUESTION"],40)
    spec.metadata=dict(spec.metadata or {})
    spec.metadata["workspace_context"]=meta
    sidecar=out/"workspace-context.json"
    sidecar.write_text(json.dumps({"schema":"sbia-documents-workspace-context-1.0","metadata":meta,"items":rows},indent=2,ensure_ascii=False),encoding="utf-8")
    return {"metadata":meta,"items":rows,"sidecar":str(sidecar)}

class Handler(SimpleHTTPRequestHandler):
    root:Path=Path('.')
    project_path:Path=Path('examples/sample_project.json')
    def _json(self,data,status=200):
        raw=json.dumps(data,ensure_ascii=False,indent=2).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        p=urlparse(self.path).path
        if p=='/api/health': return self._json({'service_id':os.environ.get('BINARIO_SERVICE_ID','binario-app-11-documentos-ia'),'release':'1.1 / v0.12.0 R12','cross_app_context':'R24.2-wave-d'})
        if p=='/api/context': return self._json(native_context.view(APP_ID))
        if p=='/api/project': return self._json(DocumentSpec.from_json(self.project_path).to_dict())
        if p=='/api/quality': return self._json(evaluate(DocumentSpec.from_json(self.project_path)).to_dict())
        if p=='/': self.path='/ui/documentos_ia.html'
        return super().do_GET()
    def do_POST(self):
        p=urlparse(self.path).path; n=int(self.headers.get('Content-Length','0')); data=json.loads(self.rfile.read(n) or b'{}')
        if p=='/api/project':
            self.project_path.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8'); return self._json({'ok':True})
        if p=='/api/export':
            spec=DocumentSpec.from_json(self.project_path); q=evaluate(spec)
            if q.status!='pass': return self._json({'ok':False,'quality':q.to_dict()},422)
            out=self.project_path.parent/'exports'; out.mkdir(parents=True,exist_ok=True);ctx=attach_workspace_context(spec,out);paths=DocumentsPipeline().export_all(spec,out);paths['workspace_context']=ctx['sidecar']
            primary=paths.get('docx') or paths.get('pdf') or paths.get('html') or paths.get('markdown')
            lineage=native_context.record_output(APP_ID,spec.title or 'Documento',output_type='document',ref=str(primary) if primary else None,output_id=f"document:{getattr(spec,'id',None) or self.project_path.stem}",metadata={'quality':q.status,'formats':sorted(paths.keys())},idempotency_key=f"document-export:{getattr(spec,'id',None) or self.project_path.stem}:{ctx['metadata'].get('snapshot_id')}")
            return self._json({'ok':True,'paths':paths,'quality':q.to_dict(),'workspace_context':ctx['metadata'],'context_lineage':lineage})
        return self._json({'error':'not found'},404)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default=str(Path(__file__).resolve().parents[1])); ap.add_argument('--project',default=None); ap.add_argument('--port',type=int,default=0); a=ap.parse_args()
    root=Path(a.root).resolve(); os.chdir(root); Handler.root=root; Handler.project_path=Path(a.project).resolve() if a.project else root/'examples/sample_project.json'
    server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler); actual=server.server_address[1]
    print(f'Documentos IA: http://127.0.0.1:{actual}/')
    server.serve_forever()
if __name__=='__main__': main()
