# Fokus Pixel Mac-Werkzeuge

Kleine Werkzeuge für den Mac. Sie laufen lokal auf deinem Rechner und brauchen keinen Account.

**Webseite mit Download und Anleitung:** https://kokina123iuerfggh.github.io/fokuspixel-mac-tools/

## Inhalt

| Ordner | Was es ist |
|---|---|
| [`klartext/`](klartext) | Diktieren per Tastendruck. Taste halten, sprechen, loslassen, der aufgeräumte Text erscheint in jeder App. Spracherkennung lokal. |
| [`screenshot-tool/`](screenshot-tool) | Bildschirm-Werkzeug. Screenshots aufnehmen und markieren, dazu ein Leuchtkreis um den Mauszeiger. |
| `index.html` | Die Webseite zu den Werkzeugen. |
| `tools/make_icons.py` | Zeichnet die App-Symbole und die Menüleisten-Symbole beider Apps (`python tools/make_icons.py`). |
| `.github/workflows/` | Baut die Mac-Apps automatisch in der Cloud und hängt sie als Download an ein Release. |

## Fertige Apps

Unter [Releases](../../releases) liegen die fertig gebauten Apps für Macs mit Apple-Chip (M1 und neuer). ZIP herunterladen, entpacken, in den Ordner Programme ziehen. Beim ersten Start fragt macOS nach, weil die Apps nicht von Apple beglaubigt sind (Systemeinstellungen > Datenschutz & Sicherheit > „Trotzdem öffnen“).

## Selbst bauen

In den jeweiligen Ordnern `klartext/` und `screenshot-tool/` steht eine eigene Anleitung mit `build_app.sh`.

## Tests

```bash
python -m unittest discover -s klartext/tests
cd screenshot-tool && QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests
```
