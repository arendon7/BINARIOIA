# R27 · Mac UAT Gate

R27 no se publica hasta ejecutar este UAT sobre un Mac real.

## Entrada y navegación
- Abrir Binario IA desde un único launcher.
- Llegar siempre al Hub canónico.
- APP05 abre Video Studio nuevo.
- Volver al Hub sin perder proyecto.
- Abrir un proyecto existente y comprobar que Video recibe el mismo `project_id`.

## Finder / proyectos
- Ver ruta física del proyecto desde el Hub.
- Abrirla en Finder.
- Encontrar `assets`, `autosave`, `exports`, `training` y `logs`.
- Confirmar que una migración legacy conserva la carpeta anterior.

## Video Studio
- Modo Simple visible al entrar.
- Cambiar Simple ↔ Pro y reiniciar; la preferencia debe persistir.
- Importar video y eliminar recurso con `×`.
- Subtítulos inferiores independientes de ideas clave superiores.
- Timeline: video, B-roll, imágenes, captions, música y voz.
- Scene strip, waveform, silencios/ripple, color, crop, keyframes y Social Clipper.
- Render H.264/AAC real.
- VideoToolbox en Apple Silicon cuando esté disponible; fallback software sin bloqueo.

## Whisper
- Estado inicial visible en Inicio.
- Preparar/reparar sin congelar la UI.
- Ejecutar `Probar Whisper`: `say → audio → transcripción`.
- Transcribir un audio/video real corto del usuario.
- Confirmar arquitectura nativa del worker.
- Forzar/observar un fallo de Whisper y comprobar que edición/render siguen funcionando.

## IA / modelos
- Abrir IA y modelos desde Hub.
- Ver ayuda del proveedor y nombre de variable/Keychain requerida.
- Guardar una clave en Keychain sin escribirla en JSON/proyecto.
- Probar un proveedor habilitado.
- Confirmar fallback local cuando proveedor externo está desactivado/no disponible.

## Criterio de aprobación

Todos los pasos críticos deben ser PASS. Los defectos visuales menores pueden entrar como deuda explícita; fallos de launcher, proyecto, Video, Whisper, render, pérdida de datos o credenciales bloquean release.
