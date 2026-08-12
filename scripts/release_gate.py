#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

CANONICAL_APPS=(
"01_auditoria_negocio","02_cazador_webs","03_agente_ia_whatsapp","04_auditoria_youtube",
"05_editor_video_ia","06_auditoria_marca_personal","07_auditoria_ecommerce","08_creador_kits",
"09_propuestas_ia","10_investigador_ia","11_documentos_ia","12_app_factory_ia")
REQUIRED=("common","hub","runtime","r26","scripts","tests","config")


def main()->int:
 ap=argparse.ArgumentParser(description='Fail-closed release gate for BINARIO IA')
 ap.add_argument('--repo',type=Path,default=Path.cwd())
 args=ap.parse_args();root=args.repo.expanduser().resolve();fail=[]
 apps=root/'apps'
 missing_apps=[a for a in CANONICAL_APPS if not (apps/a).is_dir()]
 if missing_apps:fail.append({'gate':'12_apps_source_present','missing':missing_apps})
 missing_sections=[x for x in REQUIRED if not (root/x).exists()]
 if missing_sections:fail.append({'gate':'canonical_sections_present','missing':missing_sections})
 baseline=root/'config'/'R26_SOURCE_BASELINE_MAP.json'
 if not baseline.is_file():fail.append({'gate':'baseline_identity_map','missing':str(baseline)})
 blocker=root/'docs'/'BASELINE_R26.md'
 if not blocker.is_file():fail.append({'gate':'baseline_provenance','missing':str(blocker)})
 result={'ok':not fail,'release_allowed':not fail,'repo':str(root),'apps_expected':len(CANONICAL_APPS),'failures':fail}
 print(json.dumps(result,ensure_ascii=False,indent=2))
 return 0 if not fail else 2

if __name__=='__main__':raise SystemExit(main())
