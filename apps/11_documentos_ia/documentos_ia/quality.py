from __future__ import annotations
import re
from .models import DocumentSpec, QualityIssue, QualityReport

PLACEHOLDER_RE=re.compile(r'\[\[(?:PENDIENTE|TODO|PLACEHOLDER)(?::[^\]]+)?\]\]',re.I)

def evaluate(spec: DocumentSpec) -> QualityReport:
    issues=[]
    text='\n'.join(b.text+' '+ ' '.join(b.items) for b in spec.blocks)
    headings=[b for b in spec.blocks if b.kind=='heading']
    paragraphs=[b for b in spec.blocks if b.kind=='paragraph']
    placeholders=sum(len(PLACEHOLDER_RE.findall(b.text)) for b in spec.blocks)
    empty=sum(1 for b in spec.blocks if b.kind not in {'page_break','table'} and not (b.text.strip() or b.items))
    source_ids={s.id for s in spec.sources}
    bad_refs=[]
    for b in spec.blocks:
        for sid in b.source_ids:
            if sid not in source_ids: bad_refs.append((b.id,sid))
    if placeholders: issues.append(QualityIssue('PLACEHOLDER','block',f'{placeholders} placeholder(s) pendientes.'))
    if empty: issues.append(QualityIssue('EMPTY_BLOCK','warn',f'{empty} bloque(s) vacíos.'))
    if not headings: issues.append(QualityIssue('NO_HEADINGS','block','El documento no tiene estructura de encabezados.'))
    if len(text.split()) < 80: issues.append(QualityIssue('TOO_SHORT','warn','Contenido demasiado breve para un documento profesional.'))
    if bad_refs: issues.append(QualityIssue('BROKEN_SOURCE_REF','block',f'{len(bad_refs)} referencia(s) de fuente inválidas.'))
    if not spec.objective.strip(): issues.append(QualityIssue('NO_OBJECTIVE','block','Falta objetivo del documento.'))
    if spec.document_type in {'report','proposal','legal'} and not paragraphs:
        issues.append(QualityIssue('NO_BODY','block','Falta desarrollo sustantivo.'))
    cited_paras=sum(1 for b in paragraphs if b.source_ids)
    source_coverage=(cited_paras/len(paragraphs)) if paragraphs else 0.0
    if spec.metadata.get('requires_sources') and source_coverage < float(spec.metadata.get('min_source_coverage',0.5)):
        issues.append(QualityIssue('LOW_SOURCE_COVERAGE','block',f'Cobertura de fuentes insuficiente: {source_coverage:.0%}.'))
    score=100
    for x in issues:
        score -= 18 if x.severity=='block' else 6
    score=max(0,score)
    status='pass' if not any(x.severity=='block' for x in issues) and score>=85 else 'blocked'
    return QualityReport(score=score,status=status,issues=issues,metrics={
        'words':len(text.split()),'blocks':len(spec.blocks),'headings':len(headings),
        'sources':len(spec.sources),'placeholders':placeholders,'empty_blocks':empty,'source_coverage':round(source_coverage,4)
    })
