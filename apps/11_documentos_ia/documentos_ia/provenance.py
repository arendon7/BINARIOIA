from __future__ import annotations
from pathlib import Path
import hashlib
from .models import SourceRef

def sha256_file(path: str | Path) -> str:
    p=Path(path)
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def source_from_file(path: str | Path, source_type='file', notes='') -> SourceRef:
    p=Path(path)
    return SourceRef(id=f'src-{sha256_file(p)[:12]}', title=p.name, source_type=source_type,
                     locator=str(p), hash_sha256=sha256_file(p), notes=notes)
