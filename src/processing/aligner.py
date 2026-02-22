"""Sentence-level alignment of parallel Ayoreo-Spanish texts."""

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


def align_paragraphs(es_text: str, ayo_text: str) -> list[tuple[str, str]]:
    """Align parallel texts at paragraph level.

    When paragraph counts match, aligns 1:1.
    When they don't, falls back to treating the full text as one pair.

    Returns:
        List of (spanish_paragraph, ayoreo_paragraph) tuples.
    """
    es_paras = split_paragraphs(es_text)
    ayo_paras = split_paragraphs(ayo_text)

    if len(es_paras) == len(ayo_paras):
        return list(zip(es_paras, ayo_paras))

    log.warning(
        f"Paragraph count mismatch: {len(es_paras)} ES vs {len(ayo_paras)} AYO. "
        "Falling back to full-text pair."
    )
    return [(es_text.strip(), ayo_text.strip())]


def align_sentences(es_text: str, ayo_text: str) -> list[tuple[str, str]]:
    """Align parallel texts at sentence level within aligned paragraphs.

    Returns:
        List of (spanish_sentence, ayoreo_sentence) tuples.
    """
    aligned_pairs = []
    para_pairs = align_paragraphs(es_text, ayo_text)

    for es_para, ayo_para in para_pairs:
        es_sents = split_sentences(es_para)
        ayo_sents = split_sentences(ayo_para)

        if len(es_sents) == len(ayo_sents):
            aligned_pairs.extend(zip(es_sents, ayo_sents))
        else:
            # If sentence counts differ, keep as paragraph-level pair
            aligned_pairs.append((es_para, ayo_para))

    return aligned_pairs
