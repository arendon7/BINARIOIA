# R27 · Integration Status

## Integrado en `develop`

- UX / Hub / Video flow / Project Storage.
- Whisper runtime aislado por arquitectura.
- Agent Training recuperado y protegido contra drift.
- Project Storage canónico en Apps de trabajo; App Factory con excepción global/workspace explícita.
- CI/release gate/ledger Git-first.

## Regresión local de integración

- R27 core/UI: **86/86 PASS**.
- 12 Apps: **482/482 PASS** en procesos separados.
- APP03 Agent Studio: **47/47 PASS**.
- APP05 Video Studio: **75/75 PASS**.
- APP12 App Factory: **28/28 PASS**.

## Release

**BLOQUEADO.**

No crear ZIP/DMG/PKG mientras:
1. issue #4 siga abierto (árbol fuente R26 completo todavía no importado físicamente a Git),
2. `.release-blocked` exista,
3. no se complete `docs/R27_MAC_UAT.md` en hardware real.
