"""Inference with a trained LoRA adapter — the neural network translation backend.

This loads the base LLM + trained LoRA adapter and generates translations
without needing an external API call. The adapter acts as a neural network
"overhead" on top of the frozen LLM, giving it Ayoreo translation capability.
"""

from pathlib import Path

from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

log = get_logger(__name__)

MODELS_DIR = PROJECT_ROOT / "models"


class LoRATranslator:
    """Translation using a locally trained LoRA adapter over a base LLM.

    The adapter is a small neural network trained on the Ayoreo corpus
    that modifies the base model's behavior for translation.
    """

    def __init__(self, adapter_path: str | Path | None = None):
        """
        Args:
            adapter_path: Path to saved LoRA adapter. Default: models/lora_ayoreo/adapter/
        """
        self.adapter_path = Path(adapter_path or MODELS_DIR / "lora_ayoreo" / "adapter")
        self._model = None
        self._tokenizer = None

    def _ensure_loaded(self) -> None:
        """Lazy-load the model + adapter."""
        if self._model is not None:
            return

        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer

        config = load_config("training").get("lora", {})
        base_model_name = config.get("base_model", "mistralai/Mistral-7B-v0.3")

        log.info(f"Loading base model: {base_model_name}")
        self._tokenizer = AutoTokenizer.from_pretrained(str(self.adapter_path))
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
        )

        log.info(f"Loading LoRA adapter from: {self.adapter_path}")
        self._model = PeftModel.from_pretrained(base_model, str(self.adapter_path))
        self._model.eval()

        log.info("LoRA translator ready")

    def translate(
        self,
        text: str,
        direction: str = "ayo_to_en",
        max_new_tokens: int = 256,
        temperature: float = 0.3,
    ) -> str:
        """Translate text using the neural network (base LLM + LoRA adapter).

        Args:
            text: Input text to translate.
            direction: 'ayo_to_en' or 'en_to_ayo'.
            max_new_tokens: Maximum tokens to generate.
            temperature: Sampling temperature (lower = more deterministic).

        Returns:
            Translated text.
        """
        import torch

        self._ensure_loaded()

        if direction == "ayo_to_en":
            instruction = "Translate from Ayoreo to English."
        else:
            instruction = "Translate from English to Ayoreo."

        # Same prompt format used during training
        prompt = (
            f"### Instruction:\n{instruction}\n\n"
            f"### Input:\n{text}\n\n"
            f"### Response:\n"
        )

        inputs = self._tokenizer(prompt, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=self._tokenizer.pad_token_id,
            )

        # Decode only the generated part (after the prompt)
        generated = outputs[0][inputs["input_ids"].shape[1]:]
        result = self._tokenizer.decode(generated, skip_special_tokens=True).strip()

        log.info(f"LoRA translation: {result[:100]}...")
        return result

    @property
    def is_available(self) -> bool:
        """Check if a trained adapter exists."""
        return self.adapter_path.exists()
