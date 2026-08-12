#!/bin/zsh
# Compatibilidad R26: delega al shell canónico y su runtime nativo certificado.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/ABRIR_BINARIO_IA.command" --start-app 05-editor-video-ia "$@"
