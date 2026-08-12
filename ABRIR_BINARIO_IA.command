#!/bin/zsh
# Entrada canónica. Se conserva este nombre por compatibilidad con instaladores y accesos existentes.
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec "$ROOT/ABRIR_BINARIO_IA_R26.command" "$@"
