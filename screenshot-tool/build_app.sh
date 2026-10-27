#!/usr/bin/env bash
# Baut aus dem Werkzeug eine Mac-App in dist/Bildschirm-Werkzeug.app (auf dem Mac ausführen).
set -euo pipefail
cd "$(dirname "$0")"

PY=""
for version in 3.12 3.13 3.11; do
  if command -v "python$version" >/dev/null 2>&1; then
    PY="python$version"
    break
  fi
done
if [ -z "$PY" ]; then
  echo "Kein passendes Python gefunden. Bitte installieren: brew install python@3.12"
  exit 1
fi
echo "Nutze $PY"

"$PY" -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pyinstaller pillow

VERSION="$(tr -d '[:space:]' < ../VERSION)"
cp ../VERSION assets/VERSION
echo "Version $VERSION"

pyinstaller --noconfirm --windowed --name "Bildschirm-Werkzeug" \
  --icon assets/icon.png --add-data "assets:assets" app.py

APP="dist/Bildschirm-Werkzeug.app"
# Versionsnummer für das Finder-Infofenster
plutil -replace CFBundleShortVersionString -string "$VERSION" "$APP/Contents/Info.plist"
plutil -replace CFBundleVersion -string "$VERSION" "$APP/Contents/Info.plist"
# Kein Dock-Symbol, nur das Symbol in der Menüleiste
plutil -insert LSUIElement -bool true "$APP/Contents/Info.plist"
# Ad-hoc-Signatur, damit macOS die erteilten Berechtigungen behält
codesign --force --deep --sign - "$APP"

echo "Fertig: $APP"
echo "In den Ordner Programme ziehen, mit Rechtsklick > Öffnen starten."
