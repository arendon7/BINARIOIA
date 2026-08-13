from __future__ import annotations
from .models import DocumentSpec
from .quality import evaluate

def run_workflow(payload:dict)->dict:
    """sbia-flow-1.2 compatible adapter.
    Input may contain a serialized DocumentSpec under `document`.
    """
    doc=payload.get('document') or payload
    spec=DocumentSpec(
        id=doc['id'],title=doc['title'],document_type=doc.get('document_type','generic'),objective=doc.get('objective',''),audience=doc.get('audience',''),
        blocks=[],sources=[]
    )
    # Adapter intentionally expects already-structured blocks only when provided.
    from .models import ContentBlock, SourceRef, StyleProfile
    spec.blocks=[ContentBlock(**x) for x in doc.get('blocks',[])]
    spec.sources=[SourceRef(**x) for x in doc.get('sources',[])]
    spec.style=StyleProfile(**doc.get('style',{}))
    spec.metadata=doc.get('metadata',{})
    q=evaluate(spec)
    return {'schema':'sbia-flow-1.2','engine':'documents-ia','document':spec.to_dict(),'quality':q.to_dict()}
