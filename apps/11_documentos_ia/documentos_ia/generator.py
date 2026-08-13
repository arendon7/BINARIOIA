from __future__ import annotations
from dataclasses import replace
from typing import Protocol, Callable
from .models import DocumentSpec, ContentBlock
from .planner import scaffold

class GenerationProvider(Protocol):
    def generate_blocks(self, payload: dict) -> list[dict]: ...

class CallbackGenerator:
    """Adapter for whichever LLM/provider the Binario IA Hub has configured."""
    def __init__(self, callback: Callable[[dict], list[dict]]): self.callback=callback
    def generate_blocks(self,payload:dict)->list[dict]: return self.callback(payload)


def generation_payload(spec: DocumentSpec) -> dict:
    return {
        'title':spec.title,'document_type':spec.document_type,'objective':spec.objective,
        'audience':spec.audience,'language':spec.language,
        'outline':[{'id':b.id,'heading':b.text} for b in spec.blocks if b.kind=='heading'],
        'sources':[{'id':s.id,'title':s.title,'notes':s.notes} for s in spec.sources],
        'rules':[
            'Do not invent facts not supported by supplied sources when sources are required.',
            'Return structured blocks, not one monolithic string.',
            'Preserve locked headings.',
            'Prefer concise professional prose; avoid placeholders.'
        ]
    }


def apply_generated_blocks(spec:DocumentSpec, provider:GenerationProvider)->DocumentSpec:
    if not spec.blocks: scaffold(spec)
    updates={x.get('id'):x for x in provider.generate_blocks(generation_payload(spec)) if x.get('id')}
    new=[]
    for b in spec.blocks:
        u=updates.get(b.id)
        if not u or b.locked: new.append(b); continue
        new.append(replace(b,text=u.get('text',b.text),items=list(u.get('items',b.items)),rows=list(u.get('rows',b.rows)),source_ids=list(u.get('source_ids',b.source_ids))))
    spec.blocks=new; return spec
