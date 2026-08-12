from __future__ import annotations
from urllib.parse import urlencode, urlparse, parse_qs, unquote
from urllib.request import Request, urlopen
from html.parser import HTMLParser
from pathlib import Path
import hashlib, ipaddress, json, os, socket, uuid, zipfile
from common.webtools import fetch_url, analyze_html, PageParser
from common.research_engine import run_research
from common.ai_gateway import resolve_route
from common import ai_adoption
from common import native_context_consumer as native_context
from . import store

class DDGParser(HTMLParser):
    def __init__(self): super().__init__(); self.rows=[]; self.href=None; self.buf=[]; self.capture=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="a" and ("result__a" in a.get("class","") or "result-link" in a.get("class","")):
            self.href=a.get("href",""); self.buf=[]; self.capture=True
    def handle_data(self,data):
        if self.capture: self.buf.append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.capture:
            title=" ".join("".join(self.buf).split()); url=self.href or ""
            if "uddg=" in url:
                try: url=unquote(parse_qs(urlparse(url).query).get("uddg",[""])[0]) or url
                except Exception: pass
            if title and url: self.rows.append({"title":title,"url":url})
            self.capture=False

def parse_discovery_html(text):
    p=DDGParser(); p.feed(text or ""); out=[]; seen=set()
    for x in p.rows:
        u=x["url"]
        if u.startswith("//"): u="https:"+u
        if not u.startswith("http") or u in seen: continue
        seen.add(u); out.append({"title":x["title"],"url":u})
    return out[:20]

def _public_url(url):
    u=urlparse(url if "://" in url else "https://"+url)
    if u.scheme not in {"http","https"} or not u.hostname: return False
    if os.environ.get("BINARIO_RESEARCH_ALLOW_PRIVATE")=="1": return True
    try:
        for _,_,_,_,addr in socket.getaddrinfo(u.hostname,u.port or 443,type=socket.SOCK_STREAM):
            ip=ipaddress.ip_address(addr[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast: return False
    except Exception: return True
    return True

def discover(query,provider="duckduckgo-html"):
    q=" ".join(str(query or "").split())
    if not q: return {"status":"blocked","query":q,"results":[],"error":"Consulta vacía"}
    if provider!="duckduckgo-html": return {"status":"blocked","query":q,"provider":provider,"results":[],"error":"Proveedor no configurado"}
    url="https://html.duckduckgo.com/html/?"+urlencode({"q":q})
    try:
        req=Request(url,headers={"User-Agent":"Mozilla/5.0 BinarioIA ResearchStudio/0.16"})
        with urlopen(req,timeout=12) as r: text=r.read(1_500_000).decode("utf-8","replace")
        rows=parse_discovery_html(text)
        return {"status":"pass" if rows else "degraded","query":q,"provider":provider,"results":rows,"error":None if rows else "El proveedor no devolvió resultados utilizables."}
    except Exception as exc:
        return {"status":"degraded","query":q,"provider":provider,"results":[],"error":f"{type(exc).__name__}: {exc}"}

def ingest_url(project,url,title=""):
    if not _public_url(url): raise ValueError("URL privada/local bloqueada por seguridad.")
    f=fetch_url(url,timeout=15,max_bytes=3_000_000); a=analyze_html(f["html"],f["final_url"]); parser=PageParser(); parser.feed(f["html"]); text=" ".join(parser.text)[:200000] or a.get("text_excerpt") or ""
    if len(text)<40: raise ValueError("La URL no produjo texto suficiente para investigación.")
    sid="src-"+uuid.uuid4().hex[:10]; path=store.put_source_text(project["id"],sid,text)
    row={"id":sid,"kind":"url","title":title or a.get("title") or f["final_url"],"url":f["final_url"],"sha256":f["sha256"],"bytes":f["bytes"],"content_path":path,"captured_at":store.now(),"status":"ready","metadata":{"word_count":a.get("word_count",0),"description":a.get("description","")}}
    project.setdefault("sources",[]).append(row); project["current_step"]="ingest"; store.save(project); return row

def ingest_text(project,text,title="Texto aportado"):
    clean=str(text or "").strip()
    if len(clean)<20: raise ValueError("El texto es demasiado corto.")
    sid="src-"+uuid.uuid4().hex[:10]; path=store.put_source_text(project["id"],sid,clean)
    row={"id":sid,"kind":"text","title":title or "Texto aportado","url":"","sha256":hashlib.sha256(clean.encode()).hexdigest(),"bytes":len(clean.encode()),"content_path":path,"captured_at":store.now(),"status":"ready","metadata":{}}
    project.setdefault("sources",[]).append(row); project["current_step"]="ingest"; store.save(project); return row

def analyze(project):
    sources=[]
    for s in project.get("sources",[]):
        txt=store.source_text(project["id"],s)
        if txt: sources.append({"title":s.get("title"),"url":s.get("url"),"text":txt})
    context_rows=native_context.source_rows('10-investigador-ia',['FACT','DECISION','CONSTRAINT','RISK','OPEN_QUESTION','DELIVERABLE'],20)
    if context_rows:
        context_text='\n'.join(f"[{x.get('memory_type')}] {x.get('title')}: {x.get('content')}" for x in context_rows if x.get('content'))
        if context_text:sources.append({"title":"Contexto canónico adoptado del Workspace","url":f"workspace://{native_context.metadata('10-investigador-ia').get('snapshot_id') or 'runtime'}","text":context_text})
    result=run_research({"question":project.get("question") or project.get("name"),"sources":sources})
    meta=result.get("metadata") or {}; project["evidence"]=result.get("evidence") or []; project["claims"]=meta.get("claims") or []; project["contradictions"]=meta.get("contradictions") or []
    synth=next((x.get("content") for x in result.get("deliverables",[]) if x.get("title")=="Síntesis basada en evidencia"),"")
    canonical_claims=[{k:v for k,v in x.items() if k in {"source_id","source","text","relevance"}} for x in project.get("claims",[])[:20]]
    ai_prompt=("PREGUNTA\n"+str(project.get('question') or project.get('name'))+"\n\nCLAIMS CANÓNICOS EXTRAÍDOS\n"+json.dumps(canonical_claims,ensure_ascii=False,indent=2)+"\n\nCONTRADICCIONES\n"+json.dumps(project.get('contradictions',[]),ensure_ascii=False,indent=2)+"\n\nSÍNTESIS LOCAL\n"+synth+"\n\nRedacta una síntesis ejecutiva. Usa exclusivamente los claims listados, atribuye incertidumbre y no agregues fuentes ni hechos.")
    adoption=ai_adoption.run('10-investigador-ia','research-synthesis',ai_prompt,local_text=synth,system='Eres sintetizador de evidencia. Está prohibido crear hechos, fuentes, citas o números que no aparezcan en los claims canónicos.',project_id=project.get('id'))
    synth=adoption.get('text') or synth
    project["synthesis"]={"summary":synth,"confidence":round(float(meta.get("confidence",0))*100,1),"status":"needs-review" if project["contradictions"] else "review-ready","review_notes":project.get("synthesis",{}).get("review_notes",""),"ai_adoption":adoption,"workspace_context":native_context.metadata('10-investigador-ia')}
    project["ai"]["last_route"]=resolve_route("10-investigador-ia","research-synthesis"); project["current_step"]="synthesis"; store.save(project)
    return {"result":result,"project":project}

def resolve_contradiction(project,index,note,status="resolved"):
    arr=project.get("contradictions") or []
    if index<0 or index>=len(arr): raise IndexError("Contradicción no encontrada")
    arr[index]["resolution"]={"status":status,"note":str(note or ""),"resolved_at":store.now()}; store.save(project); return arr[index]

def readiness(project):
    blockers=[]
    if not str(project.get("question") or "").strip(): blockers.append("question_missing")
    if not project.get("sources"): blockers.append("sources_missing")
    if not project.get("claims"): blockers.append("analysis_missing")
    unresolved=[x for x in project.get("contradictions",[]) if (x.get("resolution") or {}).get("status")!="resolved"]
    if unresolved: blockers.append("contradictions_unresolved")
    return {"score":max(0,100-25*len(blockers)),"ready":not blockers,"blockers":blockers,"unresolved_contradictions":len(unresolved),"sources":len(project.get("sources",[])),"claims":len(project.get("claims",[]))}

def export(project):
    rd=readiness(project); d=store.export_dir(project["id"]); d.mkdir(parents=True,exist_ok=True); stamp=store.now().replace(":","-").replace("+","_")
    base=d/f"researchm{project['id']}-{stamp[:19]}"; base.mkdir(exist_ok=True)
    (base/"project.json").write_text(json.dumps(project,indent=2,ensure_ascii=False),encoding="utf-8")
    (base/"evidence.json").write_text(json.dumps({"sources":project.get("sources",[]),"claims":project.get("claims",[]),"contradictions":project.get("contradictions",[])},indent=2,ensure_ascii=False),encoding="utf-8")
    lines=[f"# {project.get('name')}","",f"**Pregunta:** {project.get('question')}","",f"**Confianza:** {project.get('synthesis',{}).get('confidence',0)}%","","## Síntesis",project.get("synthesis",{}).get("summary") or "Sin síntesis.","","## Fuentes"]
    for i,s in enumerate(project.get("sources",[]),1): lines.append(f"{i}. {s.get('title')} — {s.get('url') or 'texto aportado'} — SHA256 `{s.get('sha256')}`")
    if project.get("contradictions"):
        lines += ["","## Contradicciones"]
        for i,c in enumerate(project["contradictions"],1): lines.append(f"{i}. {c.get('a')} ↔ {c.get('b')} · resolución: {(c.get('resolution') or {}).get('status','pendiente')}")
    (base/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    z=base.with_suffix(".zip")
    with zipfile.ZipFile(z,"w",zipfile.ZIP_DEFLATED) as zz:
        for p in base.rglob("*"):
            if p.is_file(): zz.write(p,arcname=str(base.name+"/"+str(p.relative_to(base))))
    meta={"created_at":store.now(),"dir":str(base),"zip":str(z),"readiness":rd}; project.setdefault("exports",[]).append(meta); store.save(project); store.snapshot(project["id"],"export"); return meta
