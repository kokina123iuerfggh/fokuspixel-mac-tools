# Klartext

Diktieren per Tastendruck für den Mac. Taste halten, sprechen, loslassen: Der aufgeräumte Text erscheint dort, wo du gerade schreibst, in jeder App.

Die Spracherkennung läuft **lokal** auf deinem Mac. Das Audio verlässt den Rechner nicht, es gibt kein Konto und keine Gebühren.

## Was es kann

- **Halten oder tippen:** Taste gedrückt halten und sprechen. Oder kurz antippen für den Freihand-Modus und zum Beenden noch einmal tippen. Standardtaste ist die rechte Option-Taste. Die Taste stellst du im Menü unter **Aufnahme-Taste** ein.
- **Aufräumen:** Entfernt Füllwörter („äh“, „ähm“), Wiederholungen („ich ich“), setzt Leerzeichen und Großschreibung. Regeln sind sprachabhängig, damit zum Beispiel das deutsche „um“ erhalten bleibt.
- **Optional mit Claude:** Löst Selbstkorrekturen auf („Freitag, äh, Donnerstag“ wird zu „Donnerstag“) und passt den Stil an (neutral, locker, formell). Dabei wird nur der erkannte Text gesendet, nie Audio. Ohne Schlüssel oder bei einem Fehler arbeitet automatisch die lokale Regel-Variante.
- **Wörterbuch:** Namen und Fachbegriffe richtig schreiben.
- **Kürzel:** Ein gesprochener Auslöser wird durch einen Textbaustein ersetzt, zum Beispiel „meine Mail“ durch deine Adresse.
- **Statusanzeige:** Kleines schwebendes Fenster („Ich höre zu …“, „Wird aufgeräumt …“, „Eingefügt“).
- **Verlauf:** Die letzten Diktate im Menü, ein Klick kopiert sie.
- **Menüleiste:** Aufräumen, Stil, Sprache und Genauigkeit der Spracherkennung einstellbar.

## Einrichtung

Python 3.12 ist am sichersten (`brew install python@3.12`). Sehr neue Versionen wie 3.14 haben für die Spracherkennung oft noch keine fertigen Pakete.

**Als App bauen (empfohlen):**

```bash
cd ~/klartext
bash build_app.sh
```

Der Ordner muss in deinem Benutzerordner liegen, nicht in Downloads, sonst darf das Terminal ihn nicht lesen. Danach liegt `dist/Klartext.app` im Ordner. In den Ordner Programme ziehen und beim ersten Start mit Rechtsklick auf Öffnen starten, weil die App nicht von Apple signiert ist.

**Oder direkt starten:**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Beim ersten Start wird das Sprachmodell heruntergeladen. Das dauert je nach Größe einen Moment, danach läuft alles ohne Internet.

## Berechtigungen

Systemeinstellungen > Datenschutz & Sicherheit, jeweils für Klartext (bei direktem Start für das Terminal):

| Berechtigung | Wofür |
|---|---|
| Mikrofon | Aufnahme |
| Bedienungshilfen | Text einfügen |
| Eingabeüberwachung | Taste erkennen |

Danach die App neu starten.

## Einstellungen, Wörterbuch und Kürzel

Im Menü „Wörterbuch und Kürzel bearbeiten …“ öffnet sich die Datei `config.json` im Texteditor. Beispiel:

```json
{
  "key": "alt_r",
  "language": "de",
  "dictionary": { "claude code": "Claude Code", "fokus pixel": "Fokus Pixel" },
  "snippets": { "meine mail": "name@example.com" }
}
```

Die Aufnahme-Taste musst du nicht in dieser Datei ändern: Im Menü unter **Aufnahme-Taste** wählst du einen Vorschlag oder klickst auf **Andere Taste festlegen …** und drückst die gewünschte Taste. Das gilt sofort und wird gemerkt. Nicht geeignet sind Tasten, die man beim Schreiben braucht (Buchstaben, Leertaste, Return, Pfeile und ähnliche). Die Fn-Taste lässt sich auf dem Mac nicht abfragen. Die Datei liegt unter `~/Library/Application Support/Klartext/`, dort auch der Verlauf.

## Claude zuschalten (optional)

Menü > „Aufräumen“ > „Claude“ und den API-Schlüssel einfügen. Er wird nur auf diesem Mac gespeichert (`api_key.txt`, nur für dich lesbar). Alternativ die Umgebungsvariable `ANTHROPIC_API_KEY` setzen. Das kostet pro Diktat einen sehr kleinen Betrag.

## Grenzen

- Entwickelt ohne Mac. Die Logik und die Spracherkennung sind getestet (siehe unten). Mikrofon, Tastenabfrage, Einfügen und der App-Bau sind auf dem Mac noch zu prüfen.
- Kleine Modelle (`tiny`, `base`) verhören sich öfter. Das Modell `small` ist der Standard, `medium` ist genauer, aber langsamer.
- Kein Konto, keine Synchronisation, keine Handy-Version.

## Tests

```bash
python -m unittest discover -s tests -v
```
