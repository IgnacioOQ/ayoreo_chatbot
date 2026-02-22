"""Run LoRA fine-tuning on the Ayoreo parallel corpus.

Usage:
    # Full training with defaults from configs/training.yaml
    python scripts/run_finetune.py

    # Custom base model
    python scripts/run_finetune.py --base-model meta-llama/Llama-3.1-8B

    # Prepare Gemini API format only (no local training)
    python scripts/run_finetune.py --gemini-only
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)


def prepare_gemini_data():
    """Prepare data in Gemini fine-tuning format."""
    from src.training.prepare_finetune import to_gemini_format

    for direction in ["ayo_to_es", "es_to_ayo"]:
        examples = to_gemini_format(direction=direction)

        output_dir = PROJECT_ROOT / "data" / "finetune"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"gemini_{direction}.jsonl"
        with open(output_path, "w", encoding="utf-8") as f:
            for ex in examples:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")

        log.info(f"Saved {len(examples)} examples to {output_path}")


def train_lora(base_model: str | None = None, epochs: int | None = None):
    """Train LoRA adapter on the parallel corpus."""
    from src.training.lora_trainer import train

    adapter_dir = train(base_model=base_model, epochs=epochs)
    log.info(f"Training complete. Adapter saved to: {adapter_dir}")
    return adapter_dir


def main():
    parser = argparse.ArgumentParser(description="Fine-tune for Ayoreo translation")
    parser.add_argument(
        "--base-model",
        type=str,
        default=None,
        help="HuggingFace model ID (default: from configs/training.yaml)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help="Number of training epochs (default: from config)",
    )
    parser.add_argument(
        "--gemini-only",
        action="store_true",
        help="Only prepare Gemini API format, skip LoRA training",
    )
    args = parser.parse_args()

    # Always prepare Gemini format
    log.info("Preparing Gemini fine-tuning data...")
    prepare_gemini_data()

    if not args.gemini_only:
        log.info("Starting LoRA training...")
        train_lora(base_model=args.base_model, epochs=args.epochs)
    else:
        log.info("Gemini data prepared. Skipping LoRA training (--gemini-only).")


if __name__ == "__main__":
    main()
