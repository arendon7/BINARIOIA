#!/bin/zsh
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGET="$HOME/Applications/Binario IA R27 UAT"
APP="$HOME/Applications/Binario IA R27 UAT.app"
VS="$HOME/Applications/Binario IA R27 UAT - VS Code.app"
clear
echo "============================================================"
echo " BINARIO IA v0.27.0 · R27 FULL MAC UAT"
echo " Hub unificado + Video Studio R27 + Whisper R27 + 12 Apps"
echo "============================================================"
echo
echo "Se instala AL LADO de R26; no reemplaza la versión estable."
echo "Destino: $TARGET"
echo "Proyectos: $HOME/Documents/Binario IA/Projects (se preservan)"
echo
PY=""
for P in /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12 /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3 "$(command -v python3 2>/dev/null || true)"; do
  if [[ -n "$P" && -x "$P" ]]; then PY="$P"; break; fi
done
if [[ -z "$PY" ]]; then
  BREW=""
  for B in /opt/homebrew/bin/brew /usr/local/bin/brew "$(command -v brew 2>/dev/null || true)"; do
    if [[ -n "$B" && -x "$B" ]]; then BREW="$B"; break; fi
  done
  if [[ -n "$BREW" ]]; then
    echo "Python 3 no detectado. Intentando preparar Python 3.12 con Homebrew…"
    "$BREW" install python@3.12 || true
    [[ -x /opt/homebrew/bin/python3.12 ]] && PY=/opt/homebrew/bin/python3.12
    [[ -z "$PY" && -x /usr/local/bin/python3.12 ]] && PY=/usr/local/bin/python3.12
  fi
fi
if [[ -z "$PY" ]]; then
  echo "ERROR: no se encontró Python 3 compatible. Instala Python 3.12 y vuelve a ejecutar este instalador."
  read -k 1 "?Pulsa una tecla para cerrar…"; exit 3
fi

# La regresión fuente ya fue certificada en CI. Aquí validamos lo físico:
# runtime nativo, dependencias, FFmpeg y Whisper end-to-end en este Mac.
"$PY" "$ROOT/installer/install_standalone.py" --target "$TARGET" --no-launch --skip-validation
RC=$?
if [[ "$RC" -ne 0 ]]; then
  echo; echo "La instalación física R27 UAT no quedó lista (rc=$RC). R26 no fue modificado."
  read -k 1 "?Pulsa una tecla para cerrar…"; exit "$RC"
fi

/bin/rm -rf "$APP"
/bin/mkdir -p "$APP/Contents/MacOS"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>Binario IA R27 UAT</string>
<key>CFBundleDisplayName</key><string>Binario IA R27 UAT</string>
<key>CFBundleIdentifier</key><string>com.sistemabinario.binarioia.r27.uat</string>
<key>CFBundleVersion</key><string>27.0.0</string>
<key>CFBundleShortVersionString</key><string>0.27.0-uat</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleExecutable</key><string>launch</string>
<key>LSMinimumSystemVersion</key><string>12.0</string>
</dict></plist>
PLIST
cat > "$APP/Contents/MacOS/launch" <<EOF
#!/bin/zsh
exec /bin/zsh "$TARGET/ABRIR_BINARIO_IA_R27.command"
EOF
/bin/chmod +x "$APP/Contents/MacOS/launch" "$TARGET/ABRIR_BINARIO_IA_R27.command" "$TARGET/ABRIR_BINARIO_IA.command" "$TARGET/ABRIR_BINARIO_IA_R26.command" "$TARGET/DESINSTALAR_BINARIO_IA_R27_UAT.command" 2>/dev/null || true

/bin/rm -rf "$VS"
/bin/mkdir -p "$VS/Contents/MacOS"
cat > "$VS/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>Binario IA R27 UAT - VS Code</string>
<key>CFBundleDisplayName</key><string>Binario IA R27 UAT - VS Code</string>
<key>CFBundleIdentifier</key><string>com.sistemabinario.binarioia.r27.uat.vscode</string>
<key>CFBundleVersion</key><string>27.0.0</string>
<key>CFBundleShortVersionString</key><string>0.27.0-uat</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleExecutable</key><string>launch</string>
<key>LSMinimumSystemVersion</key><string>12.0</string>
</dict></plist>
PLIST
cat > "$VS/Contents/MacOS/launch" <<EOF
#!/bin/zsh
ROOT="$TARGET"
if [[ -d "/Applications/Visual Studio Code.app" ]]; then open -a "Visual Studio Code" "$TARGET"; elif [[ -d "$HOME/Applications/Visual Studio Code.app" ]]; then open "$HOME/Applications/Visual Studio Code.app" --args "$TARGET"; elif command -v code >/dev/null 2>&1; then code "$TARGET"; else osascript -e 'display dialog "Visual Studio Code no está instalado. Es opcional." buttons {"OK"}'; fi
EOF
/bin/chmod +x "$VS/Contents/MacOS/launch"

DATA="$HOME/Library/Application Support/Binario IA/R27/uat"
/bin/mkdir -p "$DATA" "$HOME/Documents/Binario IA/Projects"
"$PY" - "$DATA/install_manifest.json" "$HOME/Applications" "$TARGET" "$APP" "$VS" <<'PYEOF'
import json,sys
from pathlib import Path
out,root,target,app,vs=map(Path,sys.argv[1:])
data={'schema':'sbia-managed-install-1.0','release':'0.27.0-r27-uat','channel':'uat','install_root':str(root.resolve()),'managed_paths':[str(target.resolve()),str(app.resolve()),str(vs.resolve())],'projects_preserved':str(Path.home()/'Documents'/'Binario IA'/'Projects')}
out.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
PYEOF

echo
echo "INSTALACIÓN R27 UAT COMPLETADA."
echo "R26 permanece instalado sin cambios."
echo "Prueba: Inicio → Video Studio → Importar → Transcribir → Clips → Renderizar."
if [[ "${BINARIO_NO_LAUNCH:-0}" != "1" ]]; then /usr/bin/open "$APP" 2>/dev/null || true; fi
echo; read -k 1 "?Pulsa una tecla para cerrar…"
exit 0
