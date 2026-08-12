# R27 Development Ledger

Fuente operativa para no perder capacidades entre iteraciones. Actualizar este archivo cuando una capacidad cambie de estado.

## Reglas

- `main` = estable/certificado.
- `develop` = integración del siguiente release.
- `feature/*` / `fix/*` = trabajo aislado.
- No declarar una capacidad “mejorada” si solo cambió Foundation: debe existir, ser visible y estar probada en su App.
- No generar ZIP/DMG/PKG mientras el release gate falle o el issue #4 siga abierto.
- No sustituir una capacidad histórica por una versión más simple sin migración explícita.
- Los datos de usuario deben converger gradualmente al proyecto canónico; cualquier migración de stores legacy debe ser no destructiva.

## Baseline recuperable

- R26 FULL MAC sobre R25.1-a1 Product Reconciliation + Social Clipper.
- SHA-256: `87b36e06e896fbbb07309e9947a4113771515cb534cfa6e525446b7a21f97c46`.
- 12 Apps canónicas.
- Identidad por árbol: `config/R26_SOURCE_BASELINE_MAP.json`.

## Estado R27

### Fuente / repositorio
- [x] Repo `arendon7/BINARIOIA` definido como fuente canónica.
- [x] `main/develop/feature/fix` establecidos.
- [x] Importador fail-closed del baseline certificado.
- [x] Release gate que exige fuente completa.
- [ ] Árbol fuente R26 completo importado físicamente a Git. **BLOCKER #4**.

### Shell / navegación
- [x] Un solo Hub como entrada conceptual.
- [x] APP 05 dirige a Video Studio R26/R27.
- [x] Entradas legacy APP05/R26/App Factory/Knowledge convergen al runtime canónico.
- [x] Inicio simplificado: Video / Proyectos / 12 Apps; avanzado separado.
- [x] Proyecto seleccionado en Hub se entrega al mismo Video Studio.
- [x] Ruta de proyectos visible y abrible en Finder.
- [x] APP05 y accesos R26 directos dejan de crear runtimes paralelos.
- [ ] Smoke visual real en Mac.

### Proyectos
- [x] Raíz canónica `~/Documents/Binario IA/Projects/`.
- [x] Estructura física `assets/autosave/exports/training/logs`.
- [x] Compatibilidad con registros históricos `prj-*.json`.
- [x] Migración de proyectos viejos sin borrado.
- [x] Preservación al desinstalar.
- [x] `common/project_storage.py` como bridge reutilizable por App.
- [x] APP03 migrada al mismo proyecto físico: estado, versiones, training, logs y exports.
- [ ] Apps 01/02/04/06/07/08/09/10: migración gradual de stores paralelos. **TRACK #5**.
- [ ] APP12: evaluar semántica de workspace antes de migrar storage.

### Video Studio
- [x] Editor R26/R27 canónico desde APP05.
- [x] Simple/Pro persistente fuera del origen del navegador.
- [x] Simple mantiene controles útiles y oculta solo controles Pro.
- [x] Timeline, clips sociales, captions, imágenes/B-roll, audio, color, silencios, proxies y render preservados desde R26.
- [x] APP05 regresión histórica 75/75 PASS.
- [ ] Smoke visual/ergonómico real en Mac.
- [ ] Validar FFmpeg/VideoToolbox en hardware real.

### Whisper
- [x] Worker aislado del Python de UI.
- [x] Runtime nativo persistente por arquitectura.
- [x] En macOS nunca cae al Python de la UI.
- [x] Si falta runtime persistente, puede crear un runtime Whisper dedicado por arquitectura.
- [x] Fail-closed arm64/x86_64.
- [x] Estados separados `runtime_ok`, `model_cached`, `ready`.
- [x] Modelo faltante se prepara sin reinstalar runtime sano.
- [x] Preparación/reparación asíncrona con progreso.
- [x] Fallo de Whisper no bloquea edición/render.
- [x] Auto-prueba macOS: `say → audio → Whisper → texto` sin terminal.
- [x] Inicio cambia de `Preparar / reparar Whisper` a `Probar Whisper` cuando está listo.
- [ ] Ejecutar auto-prueba real en Mac arm64/x86_64.
- [ ] Transcripción real de un video del usuario en Mac.

### Agent Studio / APP03
- [x] Entrenamiento desde TXT/MD/PDF/DOCX.
- [x] Q&A desde CSV/JSON/JSONL.
- [x] Plantillas CSV/JSONL.
- [x] Q&A explícitas se consideran conocimiento aprobado.
- [x] Documentos libres requieren aprobación antes de retrieval.
- [x] Fuente original guardada en `training/`.
- [x] Export incluye documentos aprobados.
- [x] Estado Agent Studio vive dentro del proyecto canónico, no en un segundo proyecto paralelo.
- [x] Migración legacy no destructiva.
- [x] APP03: 47 tests PASS en regresión actual.

### IA / modelos
- [x] Control Center del Hub conserva rutas, proveedores, costos, Keychain y pruebas.
- [x] Entradas R26 antiguas convergen al Hub en vez de crear otro runtime.
- [ ] Smoke de proveedores reales con claves del usuario en Mac.

## Regresión actual

- R27 core/UI: **85/85 PASS**.
- 12 Apps: **463/463 PASS**.
- APP03: **47/47 PASS**.
- APP05: **75/75 PASS**.
- Hub: PASS.
- Foundation histórica: 611/612 durante desarrollo; el único fallo conocido es el checksum congelado del baseline, esperado porque R27 modifica fuente. Re-certificar checksums únicamente al cerrar release.

## Gates antes de release

1. Importar árbol fuente R26 completo al repo y cerrar #4.
2. Reconciliar PR UX y PR Whisper sobre esa fuente física.
3. 12/12 Apps discoverable y regresión completa PASS.
4. R27 tests PASS.
5. Smoke Mac: launcher único, proyectos, APP05, Simple/Pro, FFmpeg y Whisper `Probar Whisper` real.
6. Revisión visual del Hub/Video en Mac.
7. Validar persistencia/ubicación del proyecto desde Finder.
8. Regenerar manifests/checksums desde Git limpio.
9. Solo entonces construir instalable y ofrecer descarga.
