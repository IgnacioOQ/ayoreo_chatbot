"""LoRA fine-tuning: train a lightweight neural network adapter on top of an LLM.

This module implements Parameter-Efficient Fine-Tuning (PEFT) using LoRA adapters.
Instead of modifying the base LLM's weights, we train a small neural network
(~1-5% of total parameters) that sits on top of the frozen base model.

Architecture:
    Base LLM (frozen) + LoRA Adapter (trainable) = Ayoreo-capable translator

The adapter learns Ayoreo-Spanish translation patterns from the parallel corpus
while the base model provides general language understanding.

Supported base models:
    - mistralai/Mistral-7B-v0.3 (recommended: good multilingual, efficient)
    - meta-llama/Llama-3.1-8B (strong baseline)
    - facebook/nllb-200-distilled-600M (smaller, translation-specific)
"""

import json
from pathlib import Path

from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

log = get_logger(__name__)

SPLITS_DIR = PROJECT_ROOT / "data" / "splits"
MODELS_DIR = PROJECT_ROOT / "models"


def load_training_data(path: Path | None = None) -> list[dict]:
    """Load parallel corpus as training examples.

    Returns:
        List of dicts with 'input' and 'output' keys formatted for instruction tuning.
    """
    if path is None:
        path = SPLITS_DIR / "train.jsonl"

    examples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            # Bidirectional: each pair generates two training examples
            examples.append({
                "instruction": "Traducí del Ayoreo al Español.",
                "input": entry["ayoreo"],
                "output": entry["spanish"],
            })
            examples.append({
                "instruction": "Traducí del Español al Ayoreo.",
                "input": entry["spanish"],
                "output": entry["ayoreo"],
            })

    log.info(f"Loaded {len(examples)} training examples (bidirectional)")
    return examples


def format_prompt(example: dict) -> str:
    """Format a training example as an instruction-following prompt.

    Uses a consistent template so the model learns to respond
    to this exact format at inference time.
    """
    return (
        f"### Instrucción:\n{example['instruction']}\n\n"
        f"### Entrada:\n{example['input']}\n\n"
        f"### Respuesta:\n{example['output']}"
    )


def create_lora_config(config: dict | None = None):
    """Create LoRA configuration for PEFT.

    Returns:
        peft.LoraConfig with parameters tuned for low-resource translation.
    """
    from peft import LoraConfig, TaskType

    if config is None:
        config = load_config("training").get("lora", {})

    return LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=config.get("rank", 16),                    # LoRA rank (size of adapter)
        lora_alpha=config.get("alpha", 32),           # Scaling factor
        lora_dropout=config.get("dropout", 0.05),     # Regularization
        target_modules=config.get("target_modules", [
            "q_proj", "k_proj", "v_proj", "o_proj",   # Attention layers
            "gate_proj", "up_proj", "down_proj",       # MLP layers
        ]),
        bias="none",
    )


def train(
    base_model: str | None = None,
    output_dir: str | Path | None = None,
    epochs: int | None = None,
    batch_size: int | None = None,
    learning_rate: float | None = None,
    max_seq_length: int = 512,
):
    """Train LoRA adapter on the Ayoreo parallel corpus.

    This trains a small neural network (adapter) on top of a frozen base LLM.
    The adapter learns Ayoreo translation patterns.

    Args:
        base_model: HuggingFace model ID. Default from config.
        output_dir: Where to save the trained adapter. Default: models/lora_ayoreo/
        epochs: Number of training epochs. Default from config.
        batch_size: Training batch size. Default from config.
        learning_rate: Learning rate. Default from config.
        max_seq_length: Maximum sequence length for tokenization.
    """
    import torch
    from datasets import Dataset
    from peft import get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling,
    )

    # Load config
    config = load_config("training").get("lora", {})
    base_model = base_model or config.get("base_model", "mistralai/Mistral-7B-v0.3")
    output_dir = Path(output_dir or MODELS_DIR / "lora_ayoreo")
    epochs = epochs or config.get("epochs", 10)
    batch_size = batch_size or config.get("batch_size", 4)
    learning_rate = learning_rate or config.get("learning_rate", 2e-4)

    log.info(f"Base model: {base_model}")
    log.info(f"Output dir: {output_dir}")
    log.info(f"Training: {epochs} epochs, batch_size={batch_size}, lr={learning_rate}")

    # 1. Load tokenizer and base model
    log.info("Loading tokenizer and base model...")
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )

    # 2. Apply LoRA adapter (the trainable neural network overhead)
    lora_config = create_lora_config(config)
    model = get_peft_model(model, lora_config)

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    log.info(
        f"Trainable parameters: {trainable_params:,} / {total_params:,} "
        f"({100 * trainable_params / total_params:.2f}%)"
    )

    # 3. Prepare dataset
    train_examples = load_training_data(SPLITS_DIR / "train.jsonl")
    val_examples = load_training_data(SPLITS_DIR / "val.jsonl")

    def tokenize_example(example):
        prompt = format_prompt(example)
        tokenized = tokenizer(
            prompt,
            truncation=True,
            max_length=max_seq_length,
            padding="max_length",
        )
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized

    train_dataset = Dataset.from_list(train_examples).map(tokenize_example)
    val_dataset = Dataset.from_list(val_examples).map(tokenize_example)

    # 4. Training arguments
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        warmup_ratio=0.1,
        weight_decay=0.01,
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        fp16=torch.cuda.is_available(),
        report_to="none",
        gradient_accumulation_steps=config.get("gradient_accumulation_steps", 4),
    )

    # 5. Train
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )

    log.info("Starting LoRA training...")
    trainer.train()

    # 6. Save adapter (only the trained neural network, not the base model)
    adapter_dir = output_dir / "adapter"
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    log.info(f"LoRA adapter saved to {adapter_dir}")

    return adapter_dir
