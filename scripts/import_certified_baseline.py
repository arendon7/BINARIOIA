#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, shutil, tempfile, zipfile
from pathlib import Path

EXPECTED_SHA256="87b36e06e896fbbb07309e9947a4113771515cb534cfa6e525446b7a21f97c46"
CANONICAL_APPS=(
"01_auditoria_negocio","02_cazador_webs","03_agente_ia_whatsapp","04_auditoria_youtube",
"05_editor_video_ia","06_auditoria_marca_personal","07_auditoria_ecommerce","08_creador_kits",
"09_propuestas_ia","10_investigador_ia","11_documentos_ia","12_app_factory_ia")
TOP_LEVEL=("apps","common","hub","runtime","r26","scripts","tests","config")
IGNORE={"__pycache__",".pytest_cache",".DS_Store","platform_r26"}


def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()


def find_payload(root:Path)->Path:
 candidates=[]
 for p in root.rglob('apps'):
  parent=p.parent
  if all((p/a).is_dir() for a in CANONICAL_APPS): candidates.append(parent)
 if not candidates: raise RuntimeError('No se encontró un payload con las 12 Apps canónicas.')
 candidates.sort(key=lambda p:len(p.parts))
 return candidates[0]


def copy_tree(src:Path,dst:Path):
 for item in src.rglob('*'):
  rel=item.relative_to(src)
  if any(part in IGNORE for part in rel.parts):continue
  target=dst/rel
  if item.is_dir():target.mkdir(parents=True,exist_ok=True)
  elif item.is_file():
   target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(item,target)


def main()->int:
 ap=argparse.ArgumentParser(description='Importa el R26 FULL certificado al repo canónico sin aceptar otro ZIP.')
 ap.add_argument('zip',type=Path);ap.add_argument('--repo',type=Path,default=Path.cwd());ap.add_argument('--apply',action='store_true')
 args=ap.parse_args();archive=args.zip.expanduser().resolve();repo=args.repo.expanduser().resolve()
 actual=sha256(archive)
 report={'archive':str(archive),'expected_sha256':EXPECTED_SHA256,'actual_sha256':actual,'sha_ok':actual==EXPECTED_SHA256,'apply':args.apply}
 if actual!=EXPECTED_SHA256:
  print(json.dumps(report,indent=2,ensure_ascii=False));return 2
 with tempfile.TemporaryDirectory(prefix='binario-r26-import-') as td:
  temp=Path(td)
  with zipfile.ZipFile(archive) as z:z.extractall(temp)
  payload=find_payload(temp);report['payload']=str(payload)
  apps=sorted(x.name for x in (payload/'apps').iterdir() if x.is_dir() and x.name in CANONICAL_APPS)
  report['apps']=apps;report['apps_ok']=apps==list(CANONICAL_APPS)
  if not report['apps_ok']:
   print(json.dumps(report,indent=2,ensure_ascii=False));return 3
  if args.apply:
   for name in TOP_LEVEL:
    src=payload/name
    if src.exists():copy_tree(src,repo/name)
   for name in ('ABRIR_BINARIO_IA.command','ABRIR_BINARIO_IA_R26.command','EMPIEZA_AQUI.md','VERIFICAR_TODO.command'):
    src=payload/name
    if src.is_file():shutil.copy2(src,repo/name)
   report['imported']=True
  else:report['imported']=False
 print(json.dumps(report,indent=2,ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
