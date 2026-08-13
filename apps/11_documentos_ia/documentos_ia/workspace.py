from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json
from .models import DocumentSpec
from .revision import revision_hash

class Workspace:
    def __init__(self, root: str|Path):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True); (self.root/'revisions').mkdir(exist_ok=True); (self.root/'exports').mkdir(exist_ok=True)
    def save(self,spec:DocumentSpec,note=''):
        spec_path=self.root/'project.json'; spec.save(spec_path)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'); h=revision_hash(spec)
        rev=self.root/'revisions'/f'{stamp}_{h[:12]}.json'; spec.save(rev)
        meta={'hash':h,'note':note,'saved_at':stamp,'file':rev.name}
        with (self.root/'revisions.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(meta,ensure_ascii=False)+'\n')
        return meta
    def load(self): return DocumentSpec.from_json(self.root/'project.json')
    def history(self):
        p=self.root/'revisions.jsonl'
        return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()] if p.exists() else []
