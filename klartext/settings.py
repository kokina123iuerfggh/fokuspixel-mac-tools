"""Einstellungen, Claude-Schlüssel und Ablageort."""
import json
import os
from pathlib import Path

APP_NAME = "Klartext"

DEFAULTS = {
    "key": "alt_r",  # rechte Optionstaste; die Fn-Taste lässt sich nicht abfragen
    "model": "small",
    "language": "de",
    "cleanup": "regeln",
    "style": "neutral",
    "tap_seconds": 0.3,
    "dictionary": {},
    "snippets": {},
}


def support_dir():
    folder = Path.home() / "Library" / "Application Support" / APP_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder


class Settings:
    def __init__(self, path=None):
        self.path = Path(path) if path else support_dir() / "config.json"
        self.data = json.loads(json.dumps(DEFAULTS))
        if self.path.exists():
            try:
                self.data.update(json.loads(self.path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def dictionary_words(self):
        return list(self.data["dictionary"].values())


def _key_path(folder):
    return (Path(folder) if folder else support_dir()) / "api_key.txt"


def load_api_key(folder=None):
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    try:
        return _key_path(folder).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def save_api_key(key, folder=None):
    path = _key_path(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(key.strip())
