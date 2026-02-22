"""POS tagging evaluation metrics."""

from src.utils.logger import get_logger

log = get_logger(__name__)


def accuracy(predicted: list[str], gold: list[str]) -> float:
    """Calculate token-level POS tagging accuracy.

    Args:
        predicted: List of predicted POS tags.
        gold: List of gold-standard POS tags.

    Returns:
        Accuracy as a float between 0 and 1.
    """
    if len(predicted) != len(gold):
        raise ValueError(
            f"Length mismatch: {len(predicted)} predicted vs {len(gold)} gold"
        )
    if not gold:
        return 0.0

    correct = sum(p == g for p, g in zip(predicted, gold))
    acc = correct / len(gold)
    log.info(f"POS accuracy: {acc:.4f} ({correct}/{len(gold)})")
    return acc


def per_tag_accuracy(
    predicted: list[str], gold: list[str]
) -> dict[str, dict[str, float]]:
    """Calculate per-tag precision, recall, and F1.

    Returns:
        Dict mapping each tag to {precision, recall, f1, support}.
    """
    from collections import Counter

    tag_correct = Counter()
    tag_predicted = Counter()
    tag_gold = Counter()

    for p, g in zip(predicted, gold):
        tag_predicted[p] += 1
        tag_gold[g] += 1
        if p == g:
            tag_correct[p] += 1

    results = {}
    for tag in sorted(set(list(tag_predicted.keys()) + list(tag_gold.keys()))):
        precision = tag_correct[tag] / tag_predicted[tag] if tag_predicted[tag] else 0.0
        recall = tag_correct[tag] / tag_gold[tag] if tag_gold[tag] else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )
        results[tag] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": tag_gold[tag],
        }

    return results
