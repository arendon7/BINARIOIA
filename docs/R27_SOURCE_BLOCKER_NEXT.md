# R27 · Source custody closed · Next release gate

El blocker estructural #4 de custodia fuente R26 está **CERRADO**.

## Evidencia cerrada
- Issue #4: completed.
- Snapshot fuente certificado: `b854a8316ecc1003ea9f2806ceb9dea229c9f276f881b942dad3dc2c46e30f87`.
- Rutas fuente R26 presentes en Git: **1,617/1,617**.
- Artefacto R26 FULL MAC certificado: `87b36e06e896fbbb07309e9947a4113771515cb534cfa6e525446b7a21f97c46`.
- Política de reconciliación aplicada: R26 llena faltantes; R27 prevalece en conflictos ya versionados.

## Próximo gate real

No volver a hidratar/importar R26. El siguiente gate es **UAT física del candidato R27 en Mac**, siguiendo `docs/R27_MAC_UAT.md`.

Debe validar sobre el candidato exacto:
1. launcher único y Hub canónico;
2. continuidad de `project_id` y almacenamiento canónico visible en Finder;
3. APP05 Video Studio con importación y render H.264/AAC real;
4. FFmpeg y VideoToolbox/fallback;
5. Whisper self-test, worker nativo y transcripción real;
6. modelos/proveedor y Keychain sin secretos en JSON/proyecto;
7. ausencia de defectos bloqueantes o pérdida de datos.

`.release-blocked` permanece intencionalmente hasta obtener esa evidencia física. Su eliminación y cualquier promoción a `main` deben realizarse en un cambio posterior y explícito.
