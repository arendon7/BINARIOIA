#!/bin/zsh
set -u
TARGET="$HOME/Applications/Binario IA R27 UAT"
APP="$HOME/Applications/Binario IA R27 UAT.app"
VS="$HOME/Applications/Binario IA R27 UAT - VS Code.app"
/bin/rm -rf "$TARGET" "$APP" "$VS"
echo "Binario IA R27 UAT fue retirado."
echo "R26, el runtime compartido y ~/Documents/Binario IA/Projects se conservaron."
