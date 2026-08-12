# R27 · Estrategia de artefactos certificados

El desarrollo vive en Git. Los ZIP/DMG/PKG no son fuente de verdad.

## Baseline recuperado

- Artefacto: `BINARIO_IA_v0.26.0_R26_FULL_MAC.zip`
- SHA-256: `87b36e06e896fbbb07309e9947a4113771515cb534cfa6e525446b7a21f97c46`
- Rol: artefacto de recuperación/provenance del ciclo R26, no árbol de desarrollo.

## Regla

Un release futuro solo puede construirse desde un checkout Git limpio que pase `scripts/release_gate.py`, regresión completa y UAT Mac. El artefacto R26 puede utilizarse para recuperar/importar fuente faltante, pero nunca para sobrescribir silenciosamente código R27 ya versionado.

## Orden de reconciliación

1. Verificar SHA del artefacto de recuperación.
2. Importar únicamente el baseline certificado.
3. Aplicar cambios R27 desde Git por encima del baseline.
4. Repetir tests por App y R27.
5. Revisar drift de capacidades/test counts.
6. Solo entonces eliminar `.release-blocked`.
