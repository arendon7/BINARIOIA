# Binario IA · App 11 Documentos IA · RC1

Motor documental desacoplado para Binario IA v0.8.1.

## Flujo
`objetivo → fuentes → esquema → generación/edición por bloques → revisión → Quality Gate → DOCX/PDF/HTML/Markdown`

## Capacidades
- proyectos documentales estructurados;
- ingesta TXT/MD/HTML/JSON/CSV/DOCX/PDF;
- hash SHA-256 y procedencia de fuentes;
- esquema por tipo documental;
- adaptador al modelo configurado en el Hub;
- bloques editables y bloqueables;
- historial de revisiones con hash;
- diff entre revisiones;
- Quality Gate bloqueante;
- DOCX corporativo;
- PDF desde la misma revisión DOCX;
- HTML y Markdown;
- servicio local y UI;
- nodo Workflow Studio;
- contratos `sbia-flow-1.2` y `sbia-interop-1.2`.

## Ejecutar
```bash
python -m documentos_ia.cli examples/sample_project.json --export-dir examples/exports
python -m documentos_ia.service  # asigna puerto libre automáticamente
```

## Regla de publicación
Una exportación final queda bloqueada si el Quality Gate detecta incidencias críticas. Se puede usar `--draft` únicamente para artefactos de trabajo.
