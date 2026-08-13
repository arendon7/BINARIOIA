#!/bin/zsh
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
ARCH="$(/usr/bin/uname -m 2>/dev/null || echo unknown)"
[[ "$ARCH" == "aarch64" ]] && ARCH="arm64"
RUNTIME_BASE="$HOME/Library/Application Support/Binario IA/runtime/v2"
PY=""
for P in "$RUNTIME_BASE"/macos-${ARCH}-py*/.venv/bin/python3 "$RUNTIME_BASE"/macos-${ARCH}-py*/.venv/bin/python; do
  if [[ -x "$P" ]]; then PY="$P"; break; fi
done
if [[ -z "$PY" ]]; then
  for P in /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12 /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    if [[ -x "$P" ]]; then PY="$P"; break; fi
  done
fi
if [[ -z "$PY" ]]; then
  /usr/bin/osascript -e 'display dialog "Binario IA R27 UAT no encontró Python. Ejecuta nuevamente el instalador FULL MAC." buttons {"OK"} default button "OK" with icon caution' 2>/dev/null || true
  exit 10
fi
load_secret() {
  local var="$1" service="com.sistemabinario.binarioia.$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" value=""
  [[ -n "${(P)var:-}" ]] && return 0
  command -v security >/dev/null 2>&1 || return 0
  value="$(security find-generic-password -a "$var" -s "$service" -w 2>/dev/null || true)"
  [[ -n "$value" ]] && export "$var=$value"
}
load_secret BINARIO_OPENAI_API_KEY
load_secret BINARIO_ANTHROPIC_API_KEY
load_secret BINARIO_GEMINI_API_KEY
export BINARIO_FULL_ROOT="$ROOT"
export BINARIO_IA_ROOT="$ROOT"
export BINARIO_PROJECTS_ROOT="${BINARIO_PROJECTS_ROOT:-$HOME/Documents/Binario IA/Projects}"
export BINARIO_PROJECTS_HOME="${BINARIO_PROJECTS_HOME:-$BINARIO_PROJECTS_ROOT}"
export BINARIO_WHISPER_MODELS="${BINARIO_WHISPER_MODELS:-$HOME/Library/Application Support/Binario IA/models/whisper}"
RUNTIME_ROOT=""
if [[ "$PY" == "$RUNTIME_BASE"/*/.venv/bin/python* ]]; then
  RUNTIME_ROOT="$(cd "$(dirname "$PY")/../.." && pwd)"
  export BINARIO_RUNTIME_ROOT="$RUNTIME_ROOT"
  export BINARIO_WHISPER_PYTHON="$PY"
fi
export PATH="${RUNTIME_ROOT:+$RUNTIME_ROOT/bin:$RUNTIME_ROOT/.venv/bin:}/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
export PYTHONPATH="$ROOT:$ROOT/r26${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT"
exec "$PY" -m hub.server "$@"
