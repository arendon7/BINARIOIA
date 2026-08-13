#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, plistlib, shutil, stat, tempfile, zipfile
from pathlib import Path

BASE_SHA='87b36e06e896fbbb07309e9947a4113771515cb534cfa6e525446b7a21f97c46'
BASE_ROOT='BINARIO_IA_v0.26.0_R26_FULL_MAC'
OUT_ROOT='BINARIO_IA_v0.27.0_R27_FULL_MAC_UAT'
OUT_ZIP=OUT_ROOT+'.zip'
OLD_PAYLOAD='Binario IA v0.25.1-a1'; NEW_PAYLOAD='Binario IA R27 UAT'
OLD_APP='INSTALAR BINARIO IA R26 FULL.app'; NEW_APP='INSTALAR BINARIO IA R27 UAT.app'
CMD='INSTALAR_BINARIO_IA_R27_FULL_MAC_UAT.command'
OVERLAY_DIRS=('apps','common','hub','r26','runtime','config','scripts','tests','docs')
ROOT_OVERLAY_FILES=('ABRIR_KNOWLEDGE_OBSIDIAN.command','EMPIEZA_AQUI.md','README.md')
CHECKSUM_PREFIXES=('apps','common','hub','runtime','workflow','config','scripts')

def sha(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def merge(src:Path,dst:Path):
 if not src.exists():return
 if src.is_dir():
  dst.mkdir(parents=True,exist_ok=True)
  for p in src.iterdir():
   if p.name not in {'.git','__pycache__','.DS_Store','.pytest_cache'}:merge(p,dst/p.name)
 else:
  dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)

def overlay_checksums(repo:Path)->dict[str,str]:
 out={}
 for name in OVERLAY_DIRS:
  base=repo/name
  if not base.exists():continue
  for p in sorted(base.rglob('*')):
   if not p.is_file() or any(x in {'__pycache__','.pytest_cache','.git'} for x in p.parts) or p.name=='.DS_Store' or p.suffix=='.pyc':continue
   out[p.relative_to(repo).as_posix()]=sha(p)
 for name in ROOT_OVERLAY_FILES:
  p=repo/name
  if p.is_file():out[p.relative_to(repo).as_posix()]=sha(p)
 return out

def write_package_checksums(payload:Path)->int:
 files={}
 for name in CHECKSUM_PREFIXES:
  base=payload/name
  if not base.exists():continue
  for p in sorted(base.rglob('*')):
   if not p.is_file() or any(x in {'__pycache__','.pytest_cache','.git'} for x in p.parts) or p.name=='.DS_Store' or p.suffix=='.pyc':continue
   rp=p.relative_to(payload).as_posix()
   if rp=='config/certified_checksums.json':continue
   files[rp]=sha(p)
 target=payload/'config'/'certified_checksums.json';target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps({'schema':'sbia-certified-checksums-2.0','release':'0.27.0-r27-uat','files_count':len(files),'files':files},indent=2,ensure_ascii=False),encoding='utf-8')
 return len(files)

def executable(p:Path):p.chmod(p.stat().st_mode|stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)

def patch_installer(p:Path):
 s=p.read_text(encoding='utf-8')
 repl={
  "PAYLOAD=PACKAGE/'payload'/'Binario IA v0.25.1-a1'":"PAYLOAD=PACKAGE/'payload'/'Binario IA R27 UAT'",
  "DEFAULT_TARGET=HOME/'Applications'/'Binario IA v0.25.1-a1'":"DEFAULT_TARGET=HOME/'Applications'/'Binario IA R27 UAT'",
  "DEFAULT_APP_WRAPPER=HOME/'Applications'/'Binario IA v0.25.1-a1.app'":"DEFAULT_APP_WRAPPER=HOME/'Applications'/'Binario IA R27 UAT.app'",
  "DEFAULT_VS_WRAPPER=HOME/'Applications'/'Binario IA v0.25.1-a1 - VS Code.app'":"DEFAULT_VS_WRAPPER=HOME/'Applications'/'Binario IA R27 UAT - VS Code.app'",
  "El paquete está incompleto: falta payload/Binario IA v0.25.1-a1.":"El paquete está incompleto: falta payload/Binario IA R27 UAT.",
  "Copiando Binario IA v0.25.1-a1 FULL STANDALONE…":"Copiando Binario IA R27 UAT FULL MAC…",
  "'CFBundleVersion':'25.0.1','CFBundleShortVersionString':'0.25.0'":"'CFBundleVersion':'27.0.0','CFBundleShortVersionString':'0.27.0-uat'",
  "standalone-v0251a1-":"standalone-r27-uat-",
  "BINARIO IA v0.25.1-a1 R25 Product Reconciliation + Social Clipper · instalación nativa con runtime por arquitectura/ABI":"BINARIO IA v0.27.0 R27 UAT · instalación FULL MAC con runtime nativo por arquitectura/ABI",
  "'release':'0.25.1-a1'":"'release':'0.27.0-r27-uat'",
  "SIMULACIÓN v0.25.1-a1 LISTA":"SIMULACIÓN R27 UAT LISTA",
  "INSTALACIÓN v0.25.1-a1 LISTA":"INSTALACIÓN R27 UAT LISTA",
  "INSTALACIÓN v0.25.1-a1 BLOQUEADA":"INSTALACIÓN R27 UAT BLOQUEADA",
  "ERROR v0.25.1-a1":"ERROR R27 UAT",
 }
 for a,b in repl.items():s=s.replace(a,b)
 start=s.index('def prepare_whisper(');end=s.index('\ndef install_brew_dependencies',start)
 fn="""def prepare_whisper(target,py,env,fh,model='small'):\n    log(f'Validando Whisper R27 {model} con runtime nativo aislado…',fh)\n    code=(\"import os,sys,json; \"+f\"sys.path.insert(0,{str(target)!r}); \"+\"os.environ['BINARIO_WHISPER_PYTHON']=sys.executable; from runtime.whisper_gateway import prepare,status; from runtime.whisper_selftest import run as selftest; \"+f\"p=prepare({model!r}); s=status({model!r}); t=selftest({model!r}); \"+\"print(json.dumps({'prepare':p,'status':s,'selftest':t},ensure_ascii=False)); raise SystemExit(0 if p.get('ok') and s.get('ready') and t.get('ok') else 7)\")\n    cp=run([py,'-c',code],cwd=target,env=env,fh=fh,timeout=3600,capture=True)\n    detail=((cp.stdout or '')+(cp.stderr or ''))[-8000:]\n    if detail:log(detail,fh)\n    if cp.returncode!=0:raise RuntimeError('Whisper R27 no pasó preparación + auto-prueba end-to-end. '+detail[-2200:])\n    return {'status':'ready','model':model,'smoke':'pass','contract':'runtime.whisper_gateway+runtime.whisper_selftest','python':py}\n"""
 s=s[:start]+fn+s[end:]
 s=s.replace("'Binario IA v0.25.1-a1','com.sistemabinario.binarioia.v0251a1'","'Binario IA R27 UAT','com.sistemabinario.binarioia.r27.uat'")
 s=s.replace("'Binario IA v0.25.1-a1 - VS Code','com.sistemabinario.binarioia.v0251a1.vscode'","'Binario IA R27 UAT - VS Code','com.sistemabinario.binarioia.r27.uat.vscode'")
 p.write_text(s,encoding='utf-8');compile(s,str(p),'exec')

def plist(path:Path):
 d={'CFBundleName':'Instalar Binario IA R27 UAT','CFBundleDisplayName':'Instalar Binario IA R27 UAT','CFBundleIdentifier':'com.sistemabinario.binarioia.r27.uat.installer','CFBundleVersion':'27.0.0','CFBundleShortVersionString':'0.27.0-uat','CFBundlePackageType':'APPL','CFBundleExecutable':'launch','LSMinimumSystemVersion':'12.0'}
 with path.open('wb') as f:plistlib.dump(d,f,sort_keys=True)

def meta(source_sha,overlay):return {'schema':'sbia-r27-uat-build-1.1','product':'Binario IA','version':'0.27.0','cycle':'R27','channel':'uat','source_repository':'arendon7/BINARIOIA','source_sha':source_sha,'baseline_sha256':BASE_SHA,'overlay_policy':'r26_certified_baseline_plus_sha256_attested_r27_files','overlay_checksums':overlay,'install_target':'~/Applications/Binario IA R27 UAT','stable_install_preserved':'~/Applications/Binario IA R26 FULL','projects_preserved':'~/Documents/Binario IA/Projects','shared_runtime':'~/Library/Application Support/Binario IA/runtime/v2','release_status':'UAT_ONLY_PENDING_PHYSICAL_MAC_SMOKE'}

def zipdet(root:Path,out:Path):
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(root.rglob('*'),key=lambda x:x.as_posix()):
   if p.is_dir():continue
   q=zipfile.ZipInfo((Path(root.name)/p.relative_to(root)).as_posix(),(2026,8,13,0,0,0));q.external_attr=(p.stat().st_mode&0xffff)<<16;q.compress_type=zipfile.ZIP_DEFLATED;z.writestr(q,p.read_bytes())

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--dist',type=Path,required=True);ap.add_argument('--source-sha',required=True);a=ap.parse_args()
 repo=a.repo.resolve();base=a.baseline.resolve();dist=a.dist.resolve();dist.mkdir(parents=True,exist_ok=True)
 if sha(base)!=BASE_SHA:raise SystemExit('baseline SHA mismatch')
 templates=repo/'release'/'r27_uat';overlay=overlay_checksums(repo);build_meta=meta(a.source_sha,overlay)
 with tempfile.TemporaryDirectory(prefix='r27-uat-') as td:
  w=Path(td);zipfile.ZipFile(base).extractall(w);old=w/BASE_ROOT;root=w/OUT_ROOT;old.rename(root)
  (root/OLD_APP).rename(root/NEW_APP);(root/'payload'/OLD_PAYLOAD).rename(root/'payload'/NEW_PAYLOAD);payload=root/'payload'/NEW_PAYLOAD
  for n in OVERLAY_DIRS:merge(repo/n,payload/n)
  for n in ROOT_OVERLAY_FILES:merge(repo/n,payload/n)
  for name in ('ABRIR_BINARIO_IA_R27.command','DESINSTALAR_BINARIO_IA_R27_UAT.command'):
   shutil.copy2(templates/name,payload/name);executable(payload/name)
  (payload/'ABRIR_BINARIO_IA.command').write_text('#!/bin/zsh\nROOT="$(cd "$(dirname "$0")" && pwd)"\nexec "$ROOT/ABRIR_BINARIO_IA_R27.command" "$@"\n');executable(payload/'ABRIR_BINARIO_IA.command')
  (payload/'ABRIR_BINARIO_IA_R26.command').write_text('#!/bin/zsh\n# Alias de compatibilidad del candidato R27 UAT.\nROOT="$(cd "$(dirname "$0")" && pwd)"\nexec "$ROOT/ABRIR_BINARIO_IA_R27.command" "$@"\n');executable(payload/'ABRIR_BINARIO_IA_R26.command')
  (payload/'.release-blocked').write_text('R27 UAT: promoción a estable bloqueada únicamente hasta completar smoke físico en Mac.\nGates de código: fuente R27 + baseline R26 certificada + overlay SHA-256.\nPendiente físico: Hub, Video Studio, FFmpeg y Whisper end-to-end.\n')
  checks=write_package_checksums(payload);build_meta['certified_payload_files']=checks
  (payload/'R27_UAT_BUILD.json').write_text(json.dumps(build_meta,indent=2,ensure_ascii=False),encoding='utf-8')
  patch_installer(root/'installer'/'install_standalone.py')
  shutil.copy2(templates/CMD,root/CMD);executable(root/CMD)
  (root/'R27_UAT_BUILD.json').write_text(json.dumps(build_meta,indent=2,ensure_ascii=False),encoding='utf-8')
  (root/'ABRE_ESTE_ARCHIVO.txt').write_text('BINARIO IA v0.27.0 · R27 FULL MAC UAT\n\n1. Descomprime el ZIP completo.\n2. Abre: INSTALAR BINARIO IA R27 UAT.app\n3. Se instala al lado de R26; no lo reemplaza.\n4. Se preservan ~/Documents/Binario IA/Projects.\n5. Prueba Inicio → Video Studio → Importar → Transcribir → Clips → Renderizar.\n6. Ejecuta Probar Whisper en Inicio.\n7. UAT no es estable hasta superar el smoke físico.\n')
  app=root/NEW_APP;resources=app/'Contents'/'Resources'/'package';shutil.rmtree(resources);resources.mkdir(parents=True)
  merge(root/'installer',resources/'installer');merge(root/'payload',resources/'payload');shutil.copy2(root/CMD,resources/CMD);executable(resources/CMD)
  shutil.copy2(templates/'installer_app_launch.command',app/'Contents'/'MacOS'/'launch');executable(app/'Contents'/'MacOS'/'launch');plist(app/'Contents'/'Info.plist')
  for legacy in ('INSTALAR_BINARIO_IA_R26_FULL_MAC.command','INSTALAR_BINARIO_IA_v0.25.1-a1_FULL_MAC.command'):
   p=root/legacy
   if p.exists():p.unlink()
  required=[payload/'apps'/'11_documentos_ia',payload/'hub'/'server.py',payload/'runtime'/'runtime_manager.py',payload/'runtime'/'whisper_gateway.py',payload/'runtime'/'whisper_selftest.py',payload/'config'/'apps.json',payload/'scripts'/'verify_all.py',payload/'r26'/'r26_video_studio'/'video-studio.js',payload/'ABRIR_BINARIO_IA_R27.command',root/'installer'/'install_standalone.py',app/'Contents'/'MacOS'/'launch',resources/'payload'/NEW_PAYLOAD/'runtime'/'whisper_gateway.py']
  miss=[str(p.relative_to(root)) for p in required if not p.exists()]
  if miss:raise SystemExit('package incomplete: '+', '.join(miss))
  out=dist/OUT_ZIP;zipdet(root,out);digest=sha(out);(dist/(OUT_ZIP+'.sha256.txt')).write_text(f'{digest}  {OUT_ZIP}\n');print(json.dumps({'ok':True,'artifact':str(out),'sha256':digest,'overlay_files':len(overlay),'certified_payload_files':checks},indent=2))
 return 0

if __name__=='__main__':raise SystemExit(main())
