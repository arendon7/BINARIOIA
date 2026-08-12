from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json, shutil
from .store import export_dir

def readiness(project:dict)->dict:
    checks={
      'business':bool(project.get('business',{}).get('name')),
      'knowledge':bool(project.get('knowledge') or [d for d in project.get('knowledge_documents',[]) if d.get('enabled')]),
      'intents':len(project.get('intents') or [])>=2,
      'flow':len(project.get('flow',{}).get('nodes') or [])>=4,
      'model':bool(project.get('model',{}).get('profile')),
      'simulation':bool(project.get('tests',{}).get('last_simulation')),
      'tests':bool((project.get('tests',{}).get('last_run') or {}).get('passed')),
      'handoff':bool(project.get('business',{}).get('handoff')),
    }
    score=round(sum(1 for v in checks.values() if v)/len(checks)*100)
    return {'score':score,'checks':checks,'ready':score>=75 and checks['simulation'] and checks['tests']}

def flowbot(project:dict)->dict:
    return {'schema':'sbia-flowbot-2.0','name':project.get('name'),'welcome':project.get('business',{}).get('welcome'),'nodes':project.get('flow',{}).get('nodes',[]),'edges':project.get('flow',{}).get('edges',[]),'knowledge':{'faq':project.get('knowledge',[]),'documents':project.get('knowledge_documents',[]),'hours':project.get('business',{}).get('hours','')},'intents':project.get('intents',[]),'variables':project.get('variables',[]),'guardrails':project.get('guardrails',[]),'handoff':project.get('business',{}).get('handoff'),'model':project.get('model',{}),'channel':{k:v for k,v in project.get('channel',{}).items() if k not in {'token','access_token'}}}

def export(project:dict)->dict:
    out=export_dir(project['id'])/datetime.now().strftime('%Y%m%d-%H%M%S');out.mkdir(parents=True,exist_ok=True)
    fb=flowbot(project);(out/'flowbot.json').write_text(json.dumps(fb,indent=2,ensure_ascii=False),encoding='utf-8')
    (out/'agent-project.json').write_text(json.dumps(project,indent=2,ensure_ascii=False),encoding='utf-8')
    guide=f"""# {project.get('name')}\n\n## Estado\nPaquete generado por Binario IA · Agent Studio R15.\n\n## Archivos\n- flowbot.json: definición portable del agente.\n- agent-project.json: proyecto completo para respaldo/revisión.\n\n## Publicación\nLa exportación no equivale a despliegue automático. Revisa canal, credenciales, políticas y pruebas antes de producción.\n"""
    (out/'README.md').write_text(guide,encoding='utf-8')
    r=readiness(project);(out/'readiness.json').write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8')
    zip_path=shutil.make_archive(str(out),'zip',root_dir=out)
    return {'folder':str(out),'zip':zip_path,'flowbot':str(out/'flowbot.json'),'readiness':r}
