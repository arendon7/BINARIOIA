#!/bin/zsh
set -u
CONTENTS="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$CONTENTS/Resources/package"
if [[ ! -d "$SOURCE/installer" || ! -d "$SOURCE/payload/Binario IA R27 UAT" || ! -f "$SOURCE/INSTALAR_BINARIO_IA_R27_FULL_MAC_UAT.command" ]]; then
  /usr/bin/osascript -e 'display dialog "El instalador R27 UAT está incompleto. Vuelve a descomprimir el ZIP completo." buttons {"OK"} default button "OK" with icon stop'
  exit 2
fi
STAGE="$(/usr/bin/mktemp -d "${TMPDIR:-/tmp}/binarioia-r27-uat.XXXXXX")" || exit 3
/bin/cp -R "$SOURCE/." "$STAGE/" || exit 4
CMD="$STAGE/INSTALAR_BINARIO_IA_R27_FULL_MAC_UAT.command"
/bin/chmod +x "$CMD"
/usr/bin/osascript - "$CMD" "$STAGE" <<'APPLESCRIPT'
on run argv
  set cmdPath to item 1 of argv
  set stagePath to item 2 of argv
  tell application "Terminal"
    activate
    do script "/bin/zsh " & quoted form of cmdPath & "; rc=$?; /bin/rm -rf " & quoted form of stagePath & "; echo; echo 'Instalador temporal limpiado.'"
  end tell
end run
APPLESCRIPT
