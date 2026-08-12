# R27 · Source Blocker #4 · Next Step

El único bloqueo estructural de Git que queda es importar físicamente el árbol completo R26 certificado.

## Restricción actual

El conector usado en esta sesión permite crear/editar archivos GitHub, ramas, commits y PRs, pero no puede transferir automáticamente el ZIP local completo de ~19 MiB como árbol Git.

## Cierre correcto

En un checkout local de `arendon7/BINARIOIA`:

```bash
python scripts/import_certified_baseline.py /ruta/BINARIO_IA_v0.26.0_R26_FULL_MAC.zip .
```

El importador:
1. verifica SHA-256 `87b36e06e896fbbb07309e9947a4113771515cb534cfa6e525446b7a21f97c46`,
2. exige las 12 Apps canónicas,
3. importa solo el baseline certificado,
4. no autoriza release por sí mismo.

Después deben reaplicarse/reconciliarse los cambios R27 ya versionados en Git y correr los gates completos antes de retirar `.release-blocked`.
