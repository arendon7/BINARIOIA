#!/bin/zsh
# Compatibilidad: usa el Hub y runtime canónicos de Binario IA.
set -u
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
exec "$ROOT/ABRIR_BINARIO_IA.command" --start-app 12-app-factory-ia "$@"
