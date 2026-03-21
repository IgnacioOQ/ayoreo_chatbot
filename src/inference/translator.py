"""Translation engine: calls Gemini with few-shot examples."""

import os

from src.utils.logger import get_logger

log = get_logger(__name__)


def build_translation_prompt(
    text: str,
    examples: list[dict],
    dict_entries: list[dict],
    direction: str = "ayo_to_en",
) -> str:
    """Build a few-shot translation prompt.

    Args:
        text: Text to translate.
        examples: Similar parallel examples from RAG retrieval.
        dict_entries: Dictionary entries for words in the text.
        direction: 'ayo_to_en' or 'en_to_ayo'.

    Returns:
        Formatted prompt string.
    """
    if direction == "ayo_to_en":
        src_lang, tgt_lang = "Ayoreo", "English"
        src_key, tgt_key = "ayoreo", "english"
    else:
        src_lang, tgt_lang = "English", "Ayoreo"
        src_key, tgt_key = "english", "ayoreo"

    parts = [
        f"Translate the following text from {src_lang} to {tgt_lang}.",
        "",
        "Examples of correct translations:",
    ]

    for ex in examples:
        parts.append(f"  {src_lang}: {ex[src_key]}")
        parts.append(f"  {tgt_lang}: {ex[tgt_key]}")
        parts.append("")

    if dict_entries:
        parts.append("Relevant vocabulary:")
        for entry in dict_entries[:10]:
            hw = entry.get("headword", entry.get("ayoreo", ""))
            defn = entry.get("definition_en", entry.get("english", ""))
            parts.append(f"  {hw} = {defn}")
        parts.append("")

    parts.append(f"Text to translate ({src_lang}):")
    parts.append(f"  {text}")
    parts.append("")
    parts.append(f"Translation ({tgt_lang}):")

    return "\n".join(parts)


def translate_with_gemini(prompt: str) -> str:
    """Send translation prompt to Gemini and return the response.

    Requires GOOGLE_API_KEY environment variable.
    """
    from google import genai

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not set in environment")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )

    result = response.text.strip()
    log.info(f"Gemini translation: {result[:100]}...")
    return result
