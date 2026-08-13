from __future__ import annotations
from .models import DocumentSpec, ContentBlock

DEFAULT_SECTIONS={
 'proposal':['Resumen ejecutivo','Contexto y necesidad','Objetivo','Alcance','Metodología','Entregables','Cronograma','Inversión','Condiciones','Próximos pasos'],
 'report':['Resumen ejecutivo','Antecedentes','Objetivo','Metodología','Resultados','Análisis','Conclusiones','Recomendaciones'],
 'legal':['Objeto','Antecedentes','Definiciones','Obligaciones','Condiciones económicas','Responsabilidad','Confidencialidad','Protección de datos','Terminación','Solución de controversias','Disposiciones finales'],
 'memo':['Asunto','Contexto','Análisis','Recomendación','Acciones'],
 'generic':['Resumen','Contexto','Desarrollo','Conclusiones','Próximos pasos']
}

def scaffold(spec: DocumentSpec) -> DocumentSpec:
    if spec.blocks:
        return spec
    key=spec.document_type.lower()
    sections=DEFAULT_SECTIONS.get(key, DEFAULT_SECTIONS['generic'])
    blocks=[]
    for i,name in enumerate(sections,1):
        blocks.append(ContentBlock(id=f'h-{i:02d}',kind='heading',text=name,level=1,locked=True))
        blocks.append(ContentBlock(id=f'p-{i:02d}',kind='paragraph',text=f'[[PENDIENTE:{name}]]'))
    spec.blocks=blocks
    return spec
