"""Pfade zu mitgelieferten Dateien, auch in der gebauten App."""
import sys
from pathlib import Path


def resource_path(name):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name
