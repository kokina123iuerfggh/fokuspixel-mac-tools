# Bildschirm-Werkzeug für den Mac

Ein Symbol in der Menüleiste mit zwei Funktionen:

1. **Screenshot aufnehmen und bearbeiten:** Bereich oder ganzen Bildschirm aufnehmen, dann bearbeiten und als PNG speichern oder in die Zwischenablage kopieren. Werkzeuge: Auswählen und Verschieben, Pfeil, Linie, Rahmen, Kreis, Stift, Textmarker, Text, Verpixeln (für sensible Stellen), nummerierte Markierung und Zuschneiden. Dazu neun Farben, eigene Farbe, Stärkeregler, Rückgängig und Wiederholen.
2. **Mauszeiger hervorheben:** Ein grüner Leuchtkreis folgt dem Mauszeiger, damit Zuschauer ihn bei Bildschirmübertragungen besser sehen. Beim Klicken wird der Kreis rot. Mit gedrückter **Optionstaste und dem Mausrad** machst du ihn stufenlos größer oder kleiner, oder du wählst im Menü eine feste Größe.
3. **Lupe:** Ein rundes Fenster neben dem Zeiger zeigt die Umgebung des Zeigers 2-, 3- oder 4-fach vergrößert, ideal für kleine Schrift. Solange die Lupe an ist, pausiert der Leuchtkreis, weil die Lupe sonst nur den vergrößerten Kreis zeigen würde. Er erscheint wieder, sobald die Lupe aus ist.

Alles läuft lokal auf dem Mac, ohne Claude und ohne Internet.

## Einrichtung (einmalig)

```bash
cd screenshot-tool
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Alternativ als normale App bauen (kein Terminal mehr nötig):

```bash
./build_app.sh
```

Danach liegt `dist/Bildschirm-Werkzeug.app` im Ordner. In den Ordner Programme ziehen und beim ersten Start mit Rechtsklick > Öffnen starten, weil die App nicht von Apple signiert ist.

## Berechtigungen (Systemeinstellungen > Datenschutz & Sicherheit)

| Berechtigung | Wofür |
|---|---|
| Bildschirm- und Systemaudioaufnahme | Screenshots |
| Eingabeüberwachung | Tastenkürzel und rote Klick-Anzeige |

Nach dem Erteilen die App neu starten. Ohne Eingabeüberwachung funktionieren Menü und Leuchtkreis trotzdem, nur die Tastenkürzel und die Klick-Farbe nicht.

## Bedienung

- **Menüleistensymbol:** Bereich aufnehmen, ganzen Bildschirm aufnehmen, Mauszeiger hervorheben, Ordner öffnen, Beenden.
- **Tastenkürzel:** `Ctrl+Alt+S` Bereich aufnehmen, `Ctrl+Alt+M` Mauszeiger-Hervorhebung ein/aus, `Ctrl+Alt+L` Lupe ein/aus. Mit `--no-hotkeys` abschaltbar.
- **Leuchtkreis größer und kleiner:** `Option` gedrückt halten und das Mausrad drehen. Ohne Optionstaste scrollt das Mausrad wie gewohnt. Die Größe wird gemerkt.
- **Farbe und Stärke:** Wirken auf die nächste Zeichnung **und** auf die gerade markierte. Eine frisch gezeichnete Markierung bleibt markiert (gestrichelter Rahmen), du kannst also direkt danach Farbe und Stärke ändern. Der Punkt neben dem Regler zeigt die Vorschau. Mit dem Auswahl-Werkzeug markierst du eine andere Zeichnung.
- **Editor:** Werkzeug unten wählen und im Bild ziehen. Nummern und Text setzt du per Klick. Mit dem Auswahl-Werkzeug verschiebst du Markierungen, `Entf` löscht die gewählte. `Cmd+Z` macht rückgängig, `Cmd+Shift+Z` wiederholt, `Cmd+S` oder „Sichern“ speichert, `Cmd+C` oder „Kopieren“ kopiert, `Cmd+Shift+S` speichert unter. „Verwerfen“ schließt ohne zu speichern.
- **Speicherort:** Standardmäßig `~/Pictures/Screenshots`, änderbar mit `--save-dir ORDNER`.

## Bekannte Grenzen

- Verpixelte Stellen lassen sich nicht verschieben, damit das Original darunter verdeckt bleibt. Falsch gesetzt: Rückgängig (⌘Z) und neu ziehen.
- Die Lupe und das Größenändern per Mausrad brauchen die Berechtigungen Bildschirmaufnahme und Eingabeüberwachung. Das Mausrad scrollt mit gedrückter Optionstaste in manchen Programmen zusätzlich.
- Der Leuchtkreis und die Lupe erscheinen nicht über Programmen im macOS-Vollbildmodus. Für Bildschirmübertragungen ein Fenster nicht im Vollbild, sondern maximiert nutzen.
- Entwickelt in einer Linux-Umgebung ohne Mac. Getestet sind hier nur der Editor (Zeichnen, Rückgängig, Speichern) und der Leuchtkreis ohne Bildschirm. Aufnahme mit `screencapture`, Tastenkürzel, Menüleistensymbol und das Bauen der App sind auf dem Mac noch zu prüfen.

## Tests

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
```
