"""Vom erkannten Rohtext zum fertigen Text."""
import cleanup
import llm


def finalize(raw, language, mode, style, dictionary, snippets, api_key="", polisher=llm.polish):
    """mode: "aus" (nur Wörterbuch und Kürzel), "regeln" (lokal) oder "claude" (mit Rückfall auf Regeln)."""
    text = raw.strip()
    if not text:
        return ""
    if mode == "claude" and api_key:
        polished = polisher(text, api_key, style, language)
        if polished:
            return cleanup.apply_replacements(cleanup.apply_replacements(polished, dictionary), snippets)
    if mode in ("regeln", "claude"):
        return cleanup.clean(text, language, dictionary, snippets)
    return cleanup.apply_replacements(cleanup.apply_replacements(text, dictionary), snippets)
