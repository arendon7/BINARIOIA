from __future__ import annotations
from pathlib import Path
import hashlib,json,py_compile,re,shutil,subprocess,sys,zipfile
from common.core import slugify
from common import native_context_consumer as native_context
from . import store

def _list(v,default):
    if isinstance(v,list): return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v,str): return [x.strip() for x in re.split(r"[\n,]+",v) if x.strip()]
    return list(default)
def _safe_skill(s): return slugify(s) or "skill"
def materialize(project):
    spec=project.get("spec") or {}; name=project.get("name") or "Nuevo kit"; purpose=project.get("purpose") or "Resolver un flujo específico."; ctx=native_context.view("08-creador-kits"); ctx_text=native_context.text("08-creador-kits",["FACT","DECISION","CONSTRAINT","DELIVERABLE","PREFERENCE","RISK"],30); inputs=_list(spec.get("inputs"),["objetivo"]); outputs=_list(spec.get("outputs"),["resultado.json"]); skills=_list(spec.get("skills"),["intake","analysis","quality","export"]); kid=slugify(name)
    root=store.pdir(project["id"])/"build"/kid
    if root.exists(): shutil.rmtree(root)
    for d in ["skills","docs","contracts","evals","security","ui","tests","examples"]: (root/d).mkdir(parents=True,exist_ok=True)
    manifest={"schema":"sbia-kit-2.0","id":kid,"name":name,"version":"1.0.0","purpose":purpose,"inputs":inputs,"outputs":outputs,"skills":skills,"entrypoint":"engine.py","ui":"ui/index.html","workspace_context":{"available":bool(ctx.get("available")),"snapshot_id":ctx.get("snapshot_id"),"context_hash":ctx.get("context_hash"),"contract_status":ctx.get("status")},"native_pro_2":{"project":True,"journey":True,"quality_gate":True,"traceability":True,"tests":True,"security":True}}
    (root/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    engine = "from __future__ import annotations\n" + f"REQUIRED={inputs!r}\nOUTPUTS={outputs!r}\n" + "def run(payload:dict)->dict:\n    missing=[x for x in REQUIRED if payload.get(x) in (None,'',[])]\n    if missing:return {'status':'blocked','missing':missing}\n    return {'status':'pass','summary':'Ejecución del kit', 'input':payload,'outputs':OUTPUTS,'trace':{'stages':['intake','analysis','quality','export']}}\n"
    (root/"engine.py").write_text(engine,encoding="utf-8")
    sample={x:f"ejemplo-{x}" for x in inputs}
    test="import unittest\nfrom engine import run\nclass GeneratedKitTest(unittest.TestCase):\n    def test_valid(self):\n        self.assertEqual(run(%r)['status'],'pass')\n    def test_missing(self):\n        self.assertEqual(run({})['status'],'blocked')\nif __name__=='__main__':unittest.main()\n" % sample
    (root/"tests/test_engine.py").write_text(test,encoding="utf-8")
    for i,s in enumerate(skills,1): (root/f"skills/{i:02d}_{_safe_skill(s)}.md").write_text(f"# {s}\n\n## Objetivo\nCapacidad ejecutable del kit.\n\n## Quality gate\nDebe producir evidencia verificable y no ocultar fallos.\n",encoding="utf-8")
    (root/"skills/skills.json").write_text(json.dumps({"skills":[{"id":s,"enabled":True} for s in skills]},indent=2,ensure_ascii=False),encoding="utf-8")
    (root/"contracts/input.schema.json").write_text(json.dumps({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","required":inputs,"properties":{x:{"type":"string"} for x in inputs}},indent=2),encoding="utf-8")
    (root/"contracts/output.schema.json").write_text(json.dumps({"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","required":["status","summary","trace"]},indent=2),encoding="utf-8")
    (root/"contracts/run.schema.json").write_text(json.dumps({"schema":"sbia-run-2.0","required":["status","summary","trace"]},indent=2),encoding="utf-8")
    (root/"contracts/trace.schema.json").write_text(json.dumps({"schema":"sbia-trace-1.0","required":["stages"]},indent=2),encoding="utf-8")
    (root/"evals/cases.json").write_text(json.dumps({"cases":[{"name":"happy-path","input":sample,"expect_status":"pass"},{"name":"missing-input","input":{},"expect_status":"blocked"}]},indent=2,ensure_ascii=False),encoding="utf-8")
    (root/"evals/rubric.json").write_text(json.dumps({"threshold":80,"dimensions":{"functionality":30,"traceability":20,"security":20,"documentation":15,"tests":15}},indent=2),encoding="utf-8")
    (root/"evals/acceptance.md").write_text("# Acceptance\n\n- Happy path PASS.\n- Missing required input is blocked.\n- No secrets or runtime caches in distribution.\n",encoding="utf-8")
    (root/"security/POLICY.md").write_text("# Seguridad\n\n- No incluir secretos.\n- Validar entradas.\n- No escribir fuera del workspace sin confirmación.\n- Fail closed para publish/deploy.\n",encoding="utf-8")
    (root/"security/DATA_HANDLING.md").write_text("# Data handling\n\nMinimiza datos, evita credenciales y documenta toda persistencia.\n",encoding="utf-8")
    (root/"security/THREAT_MODEL.md").write_text("# Threat model\n\nRiesgos: path traversal, secretos, inputs maliciosos, publish no autorizado. Controles: allowlists, workspace aislado, QA y aprobación humana.\n",encoding="utf-8")
    (root/"docs/ARCHITECTURE.md").write_text(f"# Arquitectura · {name}\n\nMotor: `engine.py`\n\nEntradas: {', '.join(inputs)}\n\nSalidas: {', '.join(outputs)}\n",encoding="utf-8")
    (root/"docs/METHODOLOGY.md").write_text("# Metodología\n\n1. Intake\n2. Análisis\n3. Quality gate\n4. Exportación\n",encoding="utf-8")
    (root/"docs/OPERATIONS.md").write_text("# Operación\n\nImporta `run` desde `engine.py` y ejecuta pruebas antes de empaquetar.\n",encoding="utf-8")
    (root/"docs/QUALITY.md").write_text("# Quality\n\nEl kit requiere compilación, tests, JSON válido, seguridad y archivos mínimos antes de empaquetar.\n",encoding="utf-8")
    (root/"docs/TRACEABILITY.md").write_text("# Traceability\n\nCada ejecución debe conservar etapas y estado; toda evolución del kit debe versionarse.\n",encoding="utf-8")
    (root/"docs/DELIVERABLES.md").write_text("# Deliverables\n\nEngine, UI, skills, contratos, evals, seguridad, docs, tests, ejemplos y ZIP validado.\n",encoding="utf-8")
    (root/"docs/USER_GUIDE.md").write_text("# User guide\n\nConfigura entradas y ejecuta el engine. Revisa quality gate antes de distribuir.\n",encoding="utf-8")
    (root/"docs/KNOWLEDGE.md").write_text("# Knowledge\n\nDocumenta aquí las fuentes y reglas de dominio propias del kit.\n",encoding="utf-8")
    (root/"docs/WORKSPACE_CONTEXT.md").write_text("# Contexto del Workspace\n\n"+(ctx_text or "Sin contexto de Workspace disponible.")+"\n",encoding="utf-8")
    (root/"README.md").write_text(f"# {name}\n\n{purpose}\n\nGenerado por Kit Studio R16 · Native PRO 2.0.\n",encoding="utf-8")
    (root/"examples/input.json").write_text(json.dumps(sample,indent=2,ensure_ascii=False),encoding="utf-8")
    (root/"ui/index.html").write_text(f"<!doctype html><html><meta charset='utf-8'><title>{name}</title><body><h1>{name}</h1><p>{purpose}</p><p>Kit Native PRO 2.0.</p></body></html>",encoding="utf-8")
    project["build"]={"status":"materialized","dir":str(root),"validation":None,"zip":None,"handoff":None}; project["current_step"]="generate"; store.save(project)
    return {"kit_dir":str(root),"manifest":manifest,"files":sum(1 for p in root.rglob("*") if p.is_file()),"workspace_context":native_context.metadata("08-creador-kits")}

def validate(project):
    raw_dir=project.get("build",{}).get("dir"); blockers=[]; checks={}
    if not raw_dir: return {"passed":False,"score":0,"blockers":["kit_not_materialized"],"checks":{}}
    root=Path(raw_dir)
    if not root.is_dir(): return {"passed":False,"score":0,"blockers":["kit_not_materialized"],"checks":{}}
    req=["manifest.json","engine.py","README.md","skills/skills.json","contracts/input.schema.json","contracts/output.schema.json","evals/cases.json","security/POLICY.md","tests/test_engine.py","ui/index.html"]
    missing=[x for x in req if not (root/x).is_file()]; checks["required_files"]={"passed":not missing,"missing":missing}; blockers += [f"missing:{x}" for x in missing]
    try: py_compile.compile(str(root/"engine.py"),doraise=True); checks["python_compile"]={"passed":True}
    except Exception as e: checks["python_compile"]={"passed":False,"error":str(e)}; blockers.append("python_compile_failed")
    bad_json=[]
    for p in root.rglob("*.json"):
        try: json.loads(p.read_text(encoding="utf-8"))
        except Exception: bad_json.append(str(p.relative_to(root)))
    checks["json"]={"passed":not bad_json,"bad":bad_json}; blockers += ["invalid_json:"+x for x in bad_json]
    cp=subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-p","test_*.py"],cwd=root,text=True,capture_output=True,timeout=60); checks["tests"]={"passed":cp.returncode==0,"returncode":cp.returncode,"output":(cp.stdout+cp.stderr)[-3000:]}
    if cp.returncode: blockers.append("tests_failed")
    # Validation itself may generate bytecode caches; remove them before distribution scan.
    for d in list(root.rglob("__pycache__")):
        shutil.rmtree(d,ignore_errors=True)
    for f in list(root.rglob("*.pyc")):
        try:f.unlink()
        except Exception:pass
    forbidden=[]; secret_patterns=[re.compile(r"sk-[A-Za-z0-9_-]{20,}"),re.compile(r"AIza[0-9A-Za-z_-]{20,}")]
    for p in root.rglob("*"):
        if p.is_dir() and p.name in {".git",".venv","node_modules","__pycache__"}: forbidden.append(str(p.relative_to(root)))
        if p.is_file() and p.stat().st_size<500000:
            try:t=p.read_text(encoding="utf-8",errors="ignore")
            except Exception:t=""
            if any(r.search(t) for r in secret_patterns): forbidden.append("secret:"+str(p.relative_to(root)))
    checks["distribution"]={"passed":not forbidden,"forbidden":forbidden}; blockers += forbidden
    result={"passed":not blockers,"score":max(0,100-20*len(blockers)),"blockers":blockers,"checks":checks,"files":sum(1 for p in root.rglob("*") if p.is_file())}; project["build"]["validation"]=result; project["build"]["status"]="validated" if result["passed"] else "blocked"; project["current_step"]="test"; store.save(project); return result

def package(project):
    val=validate(project)
    if not val["passed"]: raise RuntimeError("El kit no supera validación; no se empaqueta.")
    root=Path(project["build"]["dir"]); out=store.export_dir(project["id"]); out.mkdir(parents=True,exist_ok=True); z=out/f"{root.name}-v1.0.0.zip"
    with zipfile.ZipFile(z,"w",zipfile.ZIP_DEFLATED) as zz:
        for p in root.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith(".pyc"): zz.write(p,arcname=str(Path(root.name)/p.relative_to(root)))
    handoff={"schema":"sbia-app-factory-handoff-1.0","source_app":"08-creador-kits","project_id":project["id"],"kit_name":project["name"],"kit_dir":str(root),"kit_zip":str(z),"purpose":project.get("purpose"),"requested_action":"evolve-kit-or-promote-to-app","human_approval_required":True}
    hp=out/"app_factory_handoff.json"; hp.write_text(json.dumps(handoff,indent=2,ensure_ascii=False),encoding="utf-8")
    sha=hashlib.sha256(z.read_bytes()).hexdigest(); meta={"zip":str(z),"sha256":sha,"bytes":z.stat().st_size,"handoff":str(hp),"validation":val}; project["build"].update({"status":"packaged","zip":str(z),"handoff":str(hp)}); project["current_step"]="package"; store.save(project); store.snapshot(project["id"],"package"); return meta
