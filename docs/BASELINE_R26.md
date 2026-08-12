# Baseline canónico · Binario IA v0.26.0 R26 FULL MAC

Este repositorio parte del artefacto completo consolidado sobre **R25.1-a1 Product Reconciliation + Social Clipper** y la integración R26.

## Artefacto de recuperación

- Archivo: `BINARIO_IA_v0.26.0_R26_FULL_MAC.zip`
- SHA-256: `87b36e06e896fbbb07309e9947a4113771515cb534cfa6e525446b7a21f97c46`
- Base funcional: 12/12 Apps
- Apps históricas: 460/460 pruebas PASS en la certificación del artefacto
- Video R25: 75/75 PASS en la certificación del artefacto
- R26 integrado: 64/64 PASS en la certificación del artefacto
- Hashes del payload fusionado: 3.770/3.770 PASS

## Regla desde R27

El ZIP deja de ser el lugar de desarrollo. El desarrollo ocurre en Git con ramas, tests y PRs. Un nuevo ZIP/instalador se genera únicamente cuando `develop` supera el ciclo de integración y certificación.

## Conservación

No eliminar capacidades históricas para simplificar una implementación nueva. Si cambia un contrato existente, se mantiene compatibilidad o se documenta/migra explícitamente. Los tests de regresión de R25/R26 son gates de R27.

## Datos del usuario

Los proyectos permanecen fuera del bundle:

`~/Documents/Binario IA/Projects/`

Desinstalar o actualizar la aplicación no debe eliminar esta carpeta.
