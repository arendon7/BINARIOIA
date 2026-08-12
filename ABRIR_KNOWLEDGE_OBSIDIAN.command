#!/bin/zsh
# Compatibilidad: Knowledge se gestiona desde el Hub canónico.
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec "$ROOT/ABRIR_BINARIO_IA.command" --start-page knowledge "$@"
