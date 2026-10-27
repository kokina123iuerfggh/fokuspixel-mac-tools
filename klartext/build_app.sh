#!/usr/bin/env bash
# Baut aus Klartext eine Mac-App in dist/Klartext.app (auf dem Mac ausführen).
set -euo pipefail
cd "$(dirname "$0")"

# Die Spracherkennung braucht ein Python, für das fertige Pakete existieren. 3.12 ist am sichersten.
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
pip install --upgrade pip
pip install -r requirements.txt pyinstaller pillow

VERSION="$(tr -d '[:space:]' < ../VERSION)"
cp ../VERSION assets/VERSION
echo "Version $VERSION"

pyinstaller --noconfirm --windowed --name "Klartext" \
  --icon assets/icon.png --add-data "assets:assets" \
  --collect-all faster_whisper --collect-all ctranslate2 --collect-all onnxruntime \
  --collect-all av --collect-all tokenizers --collect-all sounddevice \
  --collect-submodules pynput \
  app.py

APP="dist/Klartext.app"
PLIST="$APP/Contents/Info.plist"
# Versionsnummer für das Finder-Infofenster
plutil -replace CFBundleShortVersionString -string "$VERSION" "$APP/Contents/Info.plist"
plutil -replace CFBundleVersion -string "$VERSION" "$APP/Contents/Info.plist"
# Kein Dock-Symbol, nur das Symbol in der Menüleiste
plutil -insert LSUIElement -bool true "$PLIST"
# Ohne diesen Text fragt macOS nicht nach der Mikrofon-Berechtigung
plutil -insert NSMicrophoneUsageDescription -string "Klartext nimmt deine Stimme auf, um sie in Text umzuwandeln." "$PLIST"
# Ad-hoc-Signatur, damit macOS die erteilten Berechtigungen behält
codesign --force --deep --sign - "$APP"

echo "Fertig: $APP"
echo "In den Ordner Programme ziehen, mit Rechtsklick > Öffnen starten."
