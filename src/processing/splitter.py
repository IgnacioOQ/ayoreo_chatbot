"""Train/val/test splitting for the parallel corpus."""

import json
import random
from pathlib import Path

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SPLITS_DIR = PROJECT_ROOT / "data" / "splits"


def split_corpus(
    corpus: list[dict],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    seed: int = 42,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Split corpus into train/val/test sets, stratified by source type.

    Args:
        corpus: Full parallel corpus.
        train_ratio: Fraction for training.
        val_ratio: Fraction for validation. Test gets the remainder.
        seed: Random seed for reproducibility.

    Returns:
        (train, val, test) lists.
    """
    random.seed(seed)

    # Group by type for stratified splitting
    by_type: dict[str, list[dict]] = {}
    for entry in corpus:
        t = entry.get("type", "other")
        by_type.setdefault(t, []).append(entry)

    train, val, test = [], [], []

    for type_name, entries in by_type.items():
        random.shuffle(entries)
        n = len(entries)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        train.extend(entries[:n_train])
        val.extend(entries[n_train : n_train + n_val])
        test.extend(entries[n_train + n_val :])

        log.info(
            f"Type '{type_name}': {n_train} train, {n_val} val, "
            f"{n - n_train - n_val} test"
        )

    log.info(f"Total split: {len(train)} train, {len(val)} val, {len(test)} test")
    return train, val, test


def save_splits(train: list[dict], val: list[dict], test: list[dict]) -> None:
    """Save splits as JSONL files."""
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)

    for name, data in [("train", train), ("val", val), ("test", test)]:
        path = SPLITS_DIR / f"{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for entry in data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        log.info(f"Saved {name} split ({len(data)} entries) to {path}")
