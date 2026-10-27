"""Regelbasiertes Aufräumen von diktiertem Text, komplett lokal."""
import re

# Füllwörter je Sprache. "um" gibt es nur im Englischen, im Deutschen ist es ein normales Wort.
FILLERS = {
    "de": r"äh+m?|öh+m?|ehm|hm+|mhm+",
    "en": r"um+|uh+m?|erm|hm+",
    "auto": r"äh+m?|öh+m?|ehm|hm+|mhm+|uh+m?|erm",
}

_REPEAT = re.compile(r"(?<!\w)([^\W\d_]+)(?:,?\s+\1(?!\w))+", re.IGNORECASE)
_SENTENCE_START = re.compile(r"(^|[.!?]\s+)([^\W\d_])")


def _filler_pattern(language):
    words = FILLERS.get(language, FILLERS["auto"])
    return re.compile(rf"(?:,\s*)?(?<!\w)(?:{words})(?!\w)(?:\s*,)?", re.IGNORECASE)


def _filler_replacement(match):
    # Stand ein Komma vor dem Füllwort, bleibt es erhalten ("glaube, äh, dass" -> "glaube, dass")
    return "," if match.group(0).lstrip().startswith(",") else " "


def apply_replacements(text, mapping):
    """Ersetzt ganze Wörter oder Wortgruppen, längste zuerst, ohne auf Groß-/Kleinschreibung zu achten."""
    for source in sorted(mapping, key=len, reverse=True):
        target = mapping[source]
        pattern = re.compile(rf"(?<!\w){re.escape(source)}(?!\w)", re.IGNORECASE)
        text = pattern.sub(lambda _m, t=target: t, text)
    return text


def _capitalize(text):
    return _SENTENCE_START.sub(lambda m: m.group(1) + m.group(2).upper(), text)


def clean(text, language="de", dictionary=None, snippets=None):
    if language in (None, ""):
        language = "auto"
    text = _filler_pattern(language).sub(_filler_replacement, text)
    text = _REPEAT.sub(r"\1", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,")
    text = _capitalize(text)
    if dictionary:
        text = apply_replacements(text, dictionary)
    if snippets:
        text = apply_replacements(text, snippets)
    return text
