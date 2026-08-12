# BINARIO IA

Repositorio canónico de desarrollo de **Sistema Binario · Binario IA**.

## Política de ramas

- `main`: última versión estable/certificada.
- `develop`: integración continua del siguiente ciclo.
- `feature/*`: trabajo por frente funcional.

## Baseline de recuperación

El repositorio se inicializa desde **Binario IA v0.26.0 R26 FULL MAC**, construido sobre la base completa R25.1-a1 Product Reconciliation + Social Clipper.

El desarrollo deja de hacerse sobre ZIPs sucesivos. Los ZIP instalables se generan únicamente al cerrar un ciclo de iteración y certificación.

## Prioridad actual

1. Unificar Hub/entrada y navegación.
2. Integrar Video Studio R26 como editor canónico desde el Hub.
3. Recuperar y persistir el modo simplificado.
4. Unificar y reparar Whisper/runtime de transcripción.
5. Auditar regresiones y deuda de UX/plataforma.

## Persistencia de usuario

Los proyectos y datos del usuario deben permanecer fuera del bundle de aplicación, bajo `~/Documents/Binario IA/` y `~/Library/Application Support/Binario IA/` según corresponda.
