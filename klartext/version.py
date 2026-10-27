"""Versionsnummer der App. Sie steht in der Datei VERSION im Hauptordner des Projekts."""
from resources import resource_path


def app_version():
    try:
        return resource_path("assets/VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "Entwicklung"
