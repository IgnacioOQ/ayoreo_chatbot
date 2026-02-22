"""Format parallel corpus for fine-tuning APIs (Gemini, OpenAI)."""

import json
from pathlib import Path

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)

SPLITS_DIR = PROJECT_ROOT / "data" / "splits"


def to_gemini_format(
    input_path: Path | None = None,
    direction: str = "ayo_to_es",
) -> list[dict]:
    """Convert corpus to Gemini fine-tuning format.

    Args:
        input_path: Path to JSONL corpus file. Defaults to train split.
        direction: 'ayo_to_es' or 'es_to_ayo'.

    Returns:
        List of training examples in Gemini format.
    """
    if input_path is None:
        input_path = SPLITS_DIR / "train.jsonl"

    examples = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            if direction == "ayo_to_es":
                input_text = entry["ayoreo"]
                output_text = entry["spanish"]
                task = "Traducí del Ayoreo al Español"
            else:
                input_text = entry["spanish"]
                output_text = entry["ayoreo"]
                task = "Traducí del Español al Ayoreo"

            examples.append({
                "text_input": f"{task}: {input_text}",
                "output": output_text,
            })

    log.info(f"Prepared {len(examples)} examples for Gemini fine-tuning ({direction})")
    return examples
