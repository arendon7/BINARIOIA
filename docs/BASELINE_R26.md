# Baseline canónico · Binario IA v0.26.0 R26 FULL MAC

Este repositorio parte del artefacto completo consolidado sobre **R25.1-a1 Product Reconciliation + Social Clipper** y la integración R26.

## Artefacto de recuperación

- Archivo: `BINARIO_IA_v0.26.0_R26_FULL_MAC.zip`
- SHA-256: `87b36e06e896fbbb07309e9947a4113771515cb534cfa6e525446b7a21f97c46`
- Copia de custodia Drive ID: `1ApcRRY0zVL3bJ_ifyXb_xjPRjNJb7I_H`
- Base funcional: 12/12 Apps
- Apps históricas: 460/460 pruebas PASS en la certificación del artefacto
- Video R25: 75/75 PASS en la certificación del artefacto
- R26 integrado: 64/64 PASS en la certificación del artefacto
- Hashes del payload fusionado: 3.770/3.770 PASS

## Snapshot fuente de recuperación

El ciclo R27 conserva además un snapshot textual filtrado del payload R26 para evitar que una conversación, runtime temporal o instalador sea el único lugar desde el cual recuperar código.

- Archivo: `BINARIOIA_R26_SOURCE_TEXT_CANONICAL.tar.gz`
- Archivos fuente seleccionados: **1.617**
- Tamaño fuente sin comprimir: **5.201.194 bytes**
- SHA-256: `b854a8316ecc1003ea9f2806ceb9dea229c9f276f881b942dad3dc2c46e30f87`
- Copia de custodia Drive ID: `1ufivwWBMohoPzaNj_8maCWWe8MTEQxrt`
- Criterio: Apps, common, config, docs, hub, r26, runtime, scripts, tests y workflow; excluye caches, outputs de validación, payload duplicado del instalador y media pesada de fixtures.

La copia de custodia **no sustituye Git**. PR #6 hidrata progresivamente el código ejecutable como archivos navegables. Ante conflictos de importación, la regla es: **R26 rellena faltantes; R27 prevalece sobre el baseline**.

## Regla desde R27

El ZIP deja de ser el lugar de desarrollo. El desarrollo ocurre en Git con ramas, tests y PRs. Un nuevo ZIP/instalador se genera únicamente cuando `develop` supera el ciclo de integración y certificación.

## Conservación

No eliminar capacidades históricas para simplificar una implementación nueva. Si cambia un contrato existente, se mantiene compatibilidad o se documenta/migra explícitamente. Los tests de regresión de R25/R26 son gates de R27.

Si durante hidratación una versión R26 intenta reemplazar una corrección R27, el import se rechaza o se restaura el archivo R27 antes de continuar. Un descenso no explicado de tests o capacidades se trata como regresión.

## Datos del usuario

Los proyectos permanecen fuera del bundle:

`~/Documents/Binario IA/Projects/`

Desinstalar o actualizar la aplicación no debe eliminar esta carpeta.
