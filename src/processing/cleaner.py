"""Text normalization and cleaning for Ayoreo and Spanish text."""

import re
import unicodedata


def normalize_unicode(text: str) -> str:
    """Apply NFC normalization — critical for Ayoreo special characters."""
    return unicodedata.normalize("NFC", text)


def clean_whitespace(text: str) -> str:
    """Normalize whitespace: collapse multiple spaces/newlines."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_html_artifacts(text: str) -> str:
    """Remove leftover HTML entities and tags."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&\w+;", " ", text)
    return text


def clean_text(text: str) -> str:
    """Full cleaning pipeline for scraped text."""
    text = normalize_unicode(text)
    text = strip_html_artifacts(text)
    text = clean_whitespace(text)
    return text
