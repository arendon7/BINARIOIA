from __future__ import annotations
from dataclasses import asdict
import hashlib, json, difflib
from .models import DocumentSpec

def revision_hash(spec: DocumentSpec) -> str:
    raw=json.dumps(spec.to_dict(),sort_keys=True,ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

def diff_specs(before: DocumentSpec, after: DocumentSpec) -> str:
    a=json.dumps(before.to_dict(),indent=2,ensure_ascii=False,sort_keys=True).splitlines()
    b=json.dumps(after.to_dict(),indent=2,ensure_ascii=False,sort_keys=True).splitlines()
    return '\n'.join(difflib.unified_diff(a,b,fromfile='before',tofile='after',lineterm=''))
