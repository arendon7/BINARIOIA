# R27 Development Ledger

Fuente operativa para no perder capacidades entre iteraciones. Actualizar este archivo cuando una capacidad cambie de estado.

## Reglas

- `main` = estable/certificado.
- `develop` = integración del siguiente release.
- `feature/*` / `fix/*` = trabajo aislado.
- No declarar una capacidad “mejorada” si solo cambió Foundation: debe existir, ser visible y estar probada en su App.
- No generar ZIP/DMG/PKG mientras el release gate falle o el issue #4 siga abierto.
- No sustituir una capacidad histórica por una versión más simple sin migración explícita.
- Si un conteo de pruebas baja, se trata como **drift/regresión** hasta demostrar lo contrario. Nunca se actualiza el ledger hacia abajo para normalizar una pérdida.

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
- [x] CI Git-first para gobernanza, regresión y bloqueo de release.
- [x] `.release-blocked` impide tags/ramas de release prematuros.
- [ ] Árbol fuente R26 completo importado físicamente a Git. **BLOCKER #4**.

### Shell / navegación
- [x] Un solo Hub como entrada conceptual.
- [x] APP 05 dirige a Video Studio R26/R27.
- [x] Entradas legacy APP05/R26/App Factory/Knowledge convergen al runtime canónico.
- [x] Inicio simplificado: Video / Proyectos / 12 Apps; avanzado separado.
- [x] Capa visual R27 del Hub versionada en `hub/ui/assets/r27.css` y protegida por tests.
- [x] Proyecto seleccionado en Hub se entrega al mismo Video Studio.
- [x] Ruta de proyectos visible y abrible en Finder.
- [ ] Smoke visual real en Mac.

### Proyectos / almacenamiento
- [x] Raíz canónica `~/Documents/Binario IA/Projects/`.
- [x] Estructura física `assets/autosave/exports/training/logs`.
- [x] Compatibilidad con registros históricos `prj-*.json`.
- [x] Migración no destructiva: copiar primero, conservar legacy y marcar migración.
- [x] Preservación al desinstalar.
- [x] APP01 Audit → Project Storage canónico.
- [x] APP02 Web → Project Storage canónico.
- [x] APP03 Agent → Project Storage canónico + training.
- [x] APP04 YouTube → Project Storage canónico.
- [x] APP05 Video → proyecto físico R26/R27 canónico.
- [x] APP06 Brand → Project Storage canónico.
- [x] APP07 Commerce → Project Storage canónico.
- [x] APP08 Kit → estado/build en autosave; entregables en exports.
- [x] APP09 Proposal → Project Storage canónico.
- [x] APP10 Research → Project Storage canónico.
- [x] APP11 Documentos → usa flujo/proyecto canónico existente.
- [x] APP12 App Factory → excepción explícita: estado global en Application Support; fuente generada visible en `Projects/_App Factory/<slug>`.
- [ ] UAT Finder en Mac: confirmar que un usuario puede localizar todo sin conocer la arquitectura interna. **TRACK #5**.

### Video Studio
- [x] Editor R26/R27 canónico desde APP05.
- [x] Simple/Pro persistente fuera del origen del navegador.
- [x] Simple mantiene controles útiles y oculta solo controles Pro.
- [x] Timeline, clips sociales, captions, imágenes/B-roll, audio, color, silencios, proxies y render preservados desde R26.
- [x] APP05 regresión histórica **75/75 PASS**.
- [ ] Smoke visual/ergonómico real en Mac.
- [ ] Validar FFmpeg/VideoToolbox en hardware real.

### Whisper
- [x] Worker aislado del Python de UI.
- [x] Runtime nativo persistente/dedicado por arquitectura.
- [x] Fail-closed arm64/x86_64.
- [x] Estados separados `runtime_ok`, `model_cached`, `ready`.
- [x] Modelo faltante se prepara sin reinstalar runtime sano.
- [x] Preparación/reparación asíncrona con progreso.
- [x] Fallo de Whisper no bloquea edición/render.
- [x] Auto-prueba Mac `say → audio → Whisper → texto` expuesta desde Inicio.
- [ ] Smoke real Mac arm64/x86_64.
- [ ] Transcripción real de audio del usuario en Mac.

### Agent Studio / APP03
- [x] Entrenamiento desde TXT/MD/PDF/DOCX.
- [x] Q&A desde CSV/JSON/JSONL.
- [x] Plantillas CSV/JSONL.
- [x] Q&A explícitas se consideran conocimiento aprobado.
- [x] Documentos libres requieren aprobación antes de retrieval.
- [x] Fuente original guardada dentro del proyecto canónico.
- [x] Export incluye documentos aprobados.
- [x] Gate físico de almacenamiento canónico.
- [x] Drift local detectado y reconciliado contra Git; no se aceptó la caída 47→44.
- [x] APP03: **47/47 PASS** en regresión actual.

### IA / modelos
- [x] Control Center del Hub conserva rutas, proveedores, costos, Keychain y pruebas.
- [x] Entradas R26 antiguas convergen al Hub en vez de crear otro runtime.
- [ ] Smoke de proveedores reales con claves del usuario en Mac.

## Regresión actual

Regresión reconstruida después de detectar y corregir drift local de APP03:

- R27 core/UI: **86/86 PASS**.
- 12 Apps, ejecutadas en procesos separados para evitar colisiones de nombres de módulos de test: **482/482 PASS**.
- APP03 Agent Studio: **47/47 PASS**.
- APP05 Video Studio: **75/75 PASS**.
- APP12 App Factory: **28/28 PASS**.
- Hub HTTP/contratos: PASS.
- Foundation histórica: 612/612 en baseline preseal; durante desarrollo puede aparecer 611/612 por el checksum congelado de R26, esperado mientras cambia fuente. Re-certificar hashes únicamente al cerrar release.

## Gates antes de release

1. Importar árbol fuente R26 completo al repo y cerrar #4.
2. Reconciliar PR UX y PR Whisper sobre esa fuente física.
3. 12/12 Apps discoverable y regresión completa PASS sin caída de conteos.
4. R27 tests PASS.
5. Smoke Mac: launcher único, proyectos, APP05, Simple/Pro, FFmpeg/VideoToolbox y Whisper real.
6. Revisión visual del Hub/Video y UAT Finder en Mac.
7. Smoke de modelos/proveedores reales si se habilitan claves del usuario.
8. Regenerar manifests/checksums desde checkout Git limpio.
9. Solo entonces construir instalable y ofrecer descarga.
