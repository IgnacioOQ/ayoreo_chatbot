"""Run fine-tuning data preparation (actual fine-tuning done via API)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.training.prepare_finetune import to_gemini_format
from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)


def main():
    log.info("Preparing fine-tuning data...")

    # Prepare both translation directions
    for direction in ["ayo_to_es", "es_to_ayo"]:
        examples = to_gemini_format(direction=direction)

        output_dir = PROJECT_ROOT / "data" / "finetune"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"gemini_{direction}.jsonl"
        with open(output_path, "w", encoding="utf-8") as f:
            for ex in examples:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")

        log.info(f"Saved {len(examples)} examples to {output_path}")

    log.info("Fine-tuning data preparation complete.")
    log.info("To fine-tune, use the Gemini API or Google AI Studio.")


if __name__ == "__main__":
    main()
