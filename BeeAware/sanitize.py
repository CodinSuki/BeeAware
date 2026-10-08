"""
sanitize.py

This module is called exactly once, at the point of window-title capture in
app.py. The live app captures raw_title from the OS and immediately sanitizes it
before it is reused downstream; nothing downstream should call this function a
second time or assume the original raw title text is still present.
"""

import re

try:
    from .logger import log_error
except ImportError:
    try:
        from logger import log_error
    except ImportError:
        def log_error(context: str, exc: Exception) -> None:
            print(f"[{context}] {type(exc).__name__}: {exc}")

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
except Exception:
    AnalyzerEngine = None
    AnonymizerEngine = None

    try:
        import spacy

        _SPACY_MODEL = spacy.load("en_core_web_sm")
    except Exception:
        _SPACY_MODEL = None
else:
    _SPACY_MODEL = None


_EMAIL_RE = re.compile(
    r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"
)

# Best-effort phone-number coverage: matches common US/intl formats with spaces,
# dashes, dots, parentheses, and optional country code; it is not guaranteed to
# be complete for every edge case.
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\w)"
)


def _replace_spans(text: str, spans: list[tuple[int, int, str]]) -> str:
    if not spans:
        return text

    sections: list[str] = []
    cursor = 0
    for start, end, replacement in sorted(spans, key=lambda item: (item[0], item[1])):
        if start < cursor:
            continue
        sections.append(text[cursor:start])
        sections.append(replacement)
        cursor = end
    sections.append(text[cursor:])
    return "".join(sections)


def _sanitize_person_names_with_presidio(text: str) -> str:
    if text is None or text == "":
        return text

    analyzer = AnalyzerEngine()
    results = analyzer.analyze(text=text, entities=["PERSON"], language="en")
    if not results:
        return text

    # Preserve the required placeholder format while still using Presidio's
    # PERSON detection and spaCy-backed entity extraction.
    spans = [
        (result.start, result.end, "[PERSON]")
        for result in results
        if getattr(result, "entity_type", None) == "PERSON"
    ]
    return _replace_spans(text, spans)


def _sanitize_person_names_with_spacy(text: str) -> str:
    if text is None or text == "" or _SPACY_MODEL is None:
        return text

    doc = _SPACY_MODEL(text)
    spans = [
        (ent.start_char, ent.end_char, "[PERSON]")
        for ent in doc.ents
        if ent.label_ == "PERSON"
    ]
    return _replace_spans(text, spans)


def sanitize_title(raw_title: str) -> str:
    """Sanitize raw OS window titles before they are used downstream."""
    if raw_title is None or raw_title == "":
        return raw_title

    text = str(raw_title)
    text = _EMAIL_RE.sub("[EMAIL]", text)
    text = _PHONE_RE.sub("[PHONE]", text)

    try:
        if AnalyzerEngine is not None and AnonymizerEngine is not None:
            return _sanitize_person_names_with_presidio(text)
        if _SPACY_MODEL is not None:
            return _sanitize_person_names_with_spacy(text)
        return text
    except Exception as exc:
        log_error("sanitize_title", exc)
        return text
