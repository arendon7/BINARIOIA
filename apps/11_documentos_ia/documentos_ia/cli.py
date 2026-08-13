from __future__ import annotations
import argparse,json
from pathlib import Path
from .models import DocumentSpec
from .pipeline import DocumentsPipeline
from .quality import evaluate

def main():
    ap=argparse.ArgumentParser(description='Binario IA · Documentos IA')
    ap.add_argument('project'); ap.add_argument('--quality',action='store_true'); ap.add_argument('--export-dir'); ap.add_argument('--draft',action='store_true')
    a=ap.parse_args(); spec=DocumentSpec.from_json(a.project); q=evaluate(spec)
    print(json.dumps(q.to_dict(),indent=2,ensure_ascii=False))
    if a.export_dir:
        paths=DocumentsPipeline().export_all(spec,a.export_dir,require_pass=not a.draft)
        print(json.dumps(paths,indent=2,ensure_ascii=False))
    return 0 if q.status=='pass' or a.draft else 2
if __name__=='__main__': raise SystemExit(main())
