#!/bin/bash
# Lance FORMULA : serveur local + fenêtre plein écran (Chromium en mode appli).
# Prévu pour être lancé via son raccourci Steam (manette OK en mode Jeu et en mode Bureau).
DIR="$(dirname "$(readlink -f "$0")")"
PORT=47800
URL="http://127.0.0.1:$PORT/"
LOGS="$HOME/.local/share/formula"
mkdir -p "$LOGS"

SRV=""
if ! curl -s -o /dev/null "$URL"; then
  python3 "$DIR/formula.py" >"$LOGS/server.log" 2>&1 &
  SRV=$!
  for _ in $(seq 60); do curl -s -o /dev/null "$URL" && break; sleep 0.1; done
fi

flatpak run --user org.chromium.Chromium \
  --app="$URL" --kiosk --start-fullscreen \
  --user-data-dir="$HOME/.var/app/org.chromium.Chromium/formula-profile" \
  --no-first-run --no-default-browser-check --noerrdialogs \
  --disable-features=Translate,MediaRouter --password-store=basic \
  --ozone-platform=x11 --class=formula >"$LOGS/browser.log" 2>&1 &
WEB=$!

if [ -n "$SRV" ]; then
  # Quand l'un des deux s'arrête (bouton Quitter ou fenêtre fermée), on arrête l'autre.
  wait -n "$SRV" "$WEB"
  kill "$SRV" "$WEB" 2>/dev/null
  pkill -f -- "--user-data-dir=$HOME/.var/app/org.chromium.Chromium/formula-profile" 2>/dev/null
else
  wait "$WEB"
fi
