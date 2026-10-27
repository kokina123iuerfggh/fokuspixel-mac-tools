"""Verlauf der letzten Diktate, lokal gespeichert."""
import json
from datetime import datetime
from pathlib import Path


class History:
    def __init__(self, path, limit=200):
        self.path = Path(path)
        self.limit = limit
        self.entries = []
        try:
            self.entries = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass

    def add(self, text, raw=""):
        self.entries.insert(0, {"time": datetime.now().isoformat(timespec="seconds"), "text": text, "raw": raw})
        del self.entries[self.limit :]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.entries, ensure_ascii=False, indent=1), encoding="utf-8")

    def recent(self, count=8):
        return self.entries[:count]
