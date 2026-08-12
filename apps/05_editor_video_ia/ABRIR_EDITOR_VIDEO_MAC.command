#!/bin/zsh
# Compatibilidad: APP 05 siempre abre el Video Studio canónico desde el Hub.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec "$ROOT/ABRIR_BINARIO_IA.command" --start-app 05-editor-video-ia "$@"
