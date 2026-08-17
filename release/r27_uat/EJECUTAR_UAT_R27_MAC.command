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
  /usr/bin/osascript -e 'display dialog "No se encontró Python para ejecutar la UAT R27. Reinstala el paquete FULL MAC UAT." buttons {"OK"} default button "OK" with icon caution' 2>/dev/null || true
  exit 10
fi

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

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$HOME/Desktop/BINARIO_IA_R27_UAT_EVIDENCE_$STAMP"
/bin/mkdir -p "$OUT"

echo "============================================================"
echo " BINARIO IA R27 · MAC UAT EVIDENCE"
echo "============================================================"
echo "Candidato: $ROOT"
echo "Evidencia: $OUT"
echo

cd "$ROOT"
"$PY" "$ROOT/scripts/r27_mac_uat_evidence.py" \
  --root "$ROOT" \
  --projects-root "$BINARIO_PROJECTS_HOME" \
  --output "$OUT" \
  --whisper-selftest
RC=$?

echo
if [[ "$RC" -eq 0 ]]; then
  echo "Preflight terminado. Revisa el reporte y completa los gates manuales pendientes."
else
  echo "Preflight con fallo bloqueante (rc=$RC). R27 permanece bloqueado."
fi
/usr/bin/open "$OUT" 2>/dev/null || true
/usr/bin/open "$OUT/r27-mac-uat-evidence.md" 2>/dev/null || true

echo
read -k 1 "?Pulsa una tecla para cerrar…"
exit "$RC"
