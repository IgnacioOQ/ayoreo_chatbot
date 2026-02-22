"""Translation quality evaluation metrics."""

from src.utils.logger import get_logger

log = get_logger(__name__)


def compute_bleu(predictions: list[str], references: list[str]) -> float:
    """Compute corpus-level BLEU score using sacrebleu.

    Args:
        predictions: List of translated sentences.
        references: List of reference translations.

    Returns:
        BLEU score as a float.
    """
    import sacrebleu

    result = sacrebleu.corpus_bleu(predictions, [references])
    log.info(f"BLEU: {result.score:.2f}")
    return result.score


def compute_chrf(predictions: list[str], references: list[str]) -> float:
    """Compute corpus-level chrF score — better for morphologically rich languages.

    Args:
        predictions: List of translated sentences.
        references: List of reference translations.

    Returns:
        chrF score as a float.
    """
    import sacrebleu

    result = sacrebleu.corpus_chrf(predictions, [references])
    log.info(f"chrF: {result.score:.2f}")
    return result.score
