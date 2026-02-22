"""Tests for the processing module."""

from src.processing.cleaner import clean_text, normalize_unicode
from src.processing.aligner import split_paragraphs, split_sentences, align_paragraphs


def test_normalize_unicode():
    # NFC normalization should produce consistent output
    text = "ñ"  # might be composed or decomposed
    result = normalize_unicode(text)
    assert result == "ñ"


def test_clean_text_strips_whitespace():
    text = "  Hello   world  \n\n\n\n  test  "
    result = clean_text(text)
    assert "   " not in result
    assert result.startswith("Hello")


def test_split_paragraphs():
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    paras = split_paragraphs(text)
    assert len(paras) == 3


def test_split_sentences():
    text = "First sentence. Second sentence! Third sentence?"
    sents = split_sentences(text)
    assert len(sents) == 3


def test_align_paragraphs_matching():
    es = "Para uno.\n\nPara dos."
    ayo = "Ayo uno.\n\nAyo dos."
    pairs = align_paragraphs(es, ayo)
    assert len(pairs) == 2
    assert pairs[0] == ("Para uno.", "Ayo uno.")


def test_align_paragraphs_mismatch_fallback():
    es = "Para uno.\n\nPara dos.\n\nPara tres."
    ayo = "Ayo uno.\n\nAyo dos."
    pairs = align_paragraphs(es, ayo)
    # Falls back to full-text pair
    assert len(pairs) == 1
