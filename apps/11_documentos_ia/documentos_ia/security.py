from __future__ import annotations
from pathlib import Path
import re

SAFE_EXT={'.txt','.md','.csv','.json','.html','.htm','.docx','.pdf'}

def safe_filename(name:str)->str:
    name=Path(name).name
    name=re.sub(r'[^A-Za-z0-9._ -]+','_',name).strip(' .')
    return name[:160] or 'archivo'

def validate_upload(path:str|Path,max_mb=50):
    p=Path(path)
    if p.suffix.lower() not in SAFE_EXT: raise ValueError('Formato no permitido.')
    if p.stat().st_size > max_mb*1024*1024: raise ValueError(f'Archivo supera {max_mb} MB.')
    return True
