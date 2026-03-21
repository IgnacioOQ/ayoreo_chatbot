"""Sentence-level alignment of parallel Ayoreo-English texts."""

import re

from src.utils.logger import get_logger

log = get_logger(__name__)


def split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs by double newlines."""
    paras = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paras if p.strip()]


def split_sentences(text: str) -> list[str]:
    """Split text into sentences using punctuation boundaries."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def align_paragraphs(en_text: str, ayo_text: str) -> list[tuple[str, str]]:
    """Align parallel texts at paragraph level.

    When paragraph counts match, aligns 1:1.
    When they don't, falls back to treating the full text as one pair.

    Returns:
        List of (english_paragraph, ayoreo_paragraph) tuples.
    """
    en_paras  = split_paragraphs(en_text)
    ayo_paras = split_paragraphs(ayo_text)

    if len(en_paras) == len(ayo_paras):
        return list(zip(en_paras, ayo_paras))

    log.warning(
        f"Paragraph count mismatch: {len(en_paras)} EN vs {len(ayo_paras)} AYO. "
        "Falling back to full-text pair."
    )
    return [(en_text.strip(), ayo_text.strip())]


def align_sentences(en_text: str, ayo_text: str) -> list[tuple[str, str]]:
    """Align parallel texts at sentence level within aligned paragraphs.

    Returns:
        List of (english_sentence, ayoreo_sentence) tuples.
    """
    aligned_pairs = []
    para_pairs = align_paragraphs(en_text, ayo_text)

    for en_para, ayo_para in para_pairs:
        en_sents  = split_sentences(en_para)
        ayo_sents = split_sentences(ayo_para)

        if len(en_sents) == len(ayo_sents):
            aligned_pairs.extend(zip(en_sents, ayo_sents))
        else:
            # If sentence counts differ, keep as paragraph-level pair
            aligned_pairs.append((en_para, ayo_para))

    return aligned_pairs
