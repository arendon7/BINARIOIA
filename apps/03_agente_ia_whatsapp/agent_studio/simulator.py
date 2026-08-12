from __future__ import annotations
import re, unicodedata
from common.ai_gateway import resolve_route
from common import ai_adoption
from common import native_context_consumer as native_context

def _norm(s:str)->str:
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    return ' '.join(re.findall(r'[a-z0-9]+',s))
def _tokens(s):return set(_norm(s).split())
def score_text(a,b):
    x,y=_tokens(a),_tokens(b)
    if not x or not y:return 0.0
    return len(x&y)/max(1,len(x|y))

def classify(project:dict,text:str)->dict:
    n=_norm(text)
    if any(x in n.split() for x in ['humano','asesor','persona','agente']):
        it=next((x for x in project.get('intents',[]) if x.get('id')=='human'),None)
        if it:return {"intent":it,"confidence":0.99}
    best=None;bs=0.0
    for it in project.get('intents',[]):
        scores=[score_text(text,e) for e in (it.get('examples') or [])]+[score_text(text,it.get('label',''))]
        s=max(scores or [0])
        if s>bs:best,bs=it,s
    return {"intent":best,"confidence":round(bs,3)}

def knowledge_match(project:dict,text:str)->dict|None:
    best=None;bs=0.0
    for k in project.get('knowledge',[]):
        if k.get('enabled',True) is False:continue
        s=max(score_text(text,k.get('question','')),score_text(text,k.get('title','')))
        if s>bs:best,bs=k,s
    for d in project.get('knowledge_documents',[]):
        if d.get('enabled',False) is False:continue
        s=max(score_text(text,d.get('title','')),score_text(text,d.get('text','')))
        if s>bs:best,bs={'id':d.get('id'),'title':d.get('title'),'question':d.get('title'),'answer':d.get('text'),'enabled':True,'source':d.get('source'),'document':True},s
    return {"item":best,"confidence":round(bs,3)} if best and bs>=0.12 else None

def simulate(project:dict,text:str,history:list|None=None)->dict:
    text=str(text or '').strip()
    if not text:raise ValueError('Mensaje vacío')
    route=resolve_route('03-agente-ia-whatsapp',task='conversation',profile=project.get('model',{}).get('profile'))
    cls=classify(project,text); it=cls.get('intent'); km=knowledge_match(project,text)
    low=_norm(text)
    risk=any(x in low for x in ['tarjeta','clave','contrasena','password','reclamo','demanda','fraude'])
    asks_price=any(x in low.split() for x in ['precio','precios','costo','costos','vale'])
    handoff=risk or bool(it and it.get('action')=='handoff')
    source=None
    if handoff:
        answer=project.get('business',{}).get('handoff') or 'Te conectaré con una persona del equipo.'; source='handoff'
    elif asks_price and not (km and any(x in _norm((km['item'].get('question','')+' '+km['item'].get('title',''))) for x in ['precio','costo','valor'])):
        answer='No voy a inventar un precio. Si está en la base aprobada puedo informarlo; de lo contrario te conecto con el equipo.';source='guardrail';handoff=True
    elif km:
        answer=km['item'].get('answer') or 'Tengo esa referencia, pero la respuesta aún no está aprobada. Puedo conectarte con una persona.';source='knowledge'
        if not km['item'].get('answer'):handoff=True
    elif it:
        answer=it.get('response') or 'Entendido. ¿Me das un poco más de contexto?';source='intent'
    else:
        answer='No estoy seguro de haber entendido. Puedo darte información, ayudarte con una compra o conectarte con una persona.';source='fallback'
    ctx=native_context.text('03-agente-ia-whatsapp',['FACT','DECISION','CONSTRAINT','PREFERENCE'],20)
    ctx_meta=native_context.metadata('03-agente-ia-whatsapp')
    adoption=None
    # Guardrails/handoff always win. Workspace context is supplemental and cannot override them.
    if not handoff:
        approved=[{"title":k.get("title"),"question":k.get("question"),"answer":k.get("answer")} for k in project.get("knowledge",[]) if k.get("enabled",True) and k.get("answer")]
        approved_docs=[{"title":d.get("title"),"answer":d.get("text"),"source":d.get("source")} for d in project.get("knowledge_documents",[]) if d.get("enabled",False) and d.get("text")]
        approved=(approved+approved_docs)[:30]
        recent=(history or [])[-6:]
        prompt=("NEGOCIO\n"+str(project.get('business',{}))+"\n\nCONOCIMIENTO APROBADO\n"+str(approved[:20])+"\n\nCONTEXTO CANÓNICO DEL WORKSPACE (SUPLEMENTARIO; NO AUTORIZA PRECIOS NI POLÍTICAS)\n"+(ctx or '(sin contexto)')+"\n\nINTENT DETECTADO\n"+str(it or {})+"\n\nRESPUESTA LOCAL SEGURA\n"+answer+"\n\nHISTORIAL\n"+str(recent)+"\n\nMENSAJE USUARIO\n"+text+"\n\nRedacta únicamente la respuesta final al usuario. No inventes hechos, precios ni políticas.")
        adoption=ai_adoption.run('03-agente-ia-whatsapp','conversation-response',prompt,local_text=answer,system='Eres el redactor conversacional de Binario IA. Respeta literalmente guardrails y conocimiento aprobado. No agregues hechos no presentes.',project_id=project.get('id'))
        answer=adoption.get('text') or answer
    mode=('deterministic-local-sandbox' if adoption and not adoption.get('enabled') else ((adoption or {}).get('mode') or 'local-guardrail'))
    return {"user":text,"assistant":answer,"intent":it.get('id') if it else None,"intent_label":it.get('label') if it else None,"confidence":cls.get('confidence',0),"knowledge_id":km['item'].get('id') if km else None,"handoff":handoff,"source":source,"route":{"profile":route.get('profile'),"chosen":(route.get('chosen') or {}).get('id'),"provider":(route.get('chosen') or {}).get('provider')},"execution_mode":mode,"ai_adoption":adoption,"workspace_context":ctx_meta}
