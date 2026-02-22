"""Clean and convert extracted glossaries to a structured dictionary using Gemini."""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai
from pydantic import BaseModel, Field

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Initialize Gemini Client
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    # Try to load from .env if not in environment
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    log.error("GOOGLE_API_KEY not found in environment or .env file.")
    exit(1)

client = genai.Client(api_key=api_key)

class DictionaryEntry(BaseModel):
    ayoreo: str = Field(description="The cleaned Ayoreo word or short phrase. Must be lowercase.")
    spanish: str = Field(description="The Spanish translation or definition. Must be lowercase.")
    pos_tag: str = Field(
        description="The primary Part-of-Speech tag for the Spanish definition. Allowed values: VERB, NOUN, ADJ, ADV, PRON, NUM, CONJ, PREP, INTERJ, PHRASE, OTHER"
    )
    is_valid: bool = Field(description="False if the input was clearly a narrative sentence, conversational dialogue, or garbage rather than a dictionary entry. True if it's a valid vocabulary word or short idiom.")

class DictionaryResult(BaseModel):
    entries: list[DictionaryEntry]

def batch_process_glossaries(entries: list[dict], batch_size: int = 50) -> list[dict]:
    """Process glossaries in batches using Gemini Structured Outputs."""
    cleaned_entries = []
    
    # We use a relatively fast and cheap model for this data cleaning
    model_id = "gemini-2.5-flash"
    
    prompt_template = """
    You are an expert linguist working on an Ayoreo to Spanish dictionary.
    I have extracted glossary terms from a website, but the extraction is noisy. Some entries are just single vocabulary words (good), but others are full sentences, conversational dialogue snippets, or garbage (bad).
    
    Your task is to:
    1. Clean the 'ayoreo' word/phrase and the 'spanish' definition. Standardize them to lowercase.
    2. Remove unnecessary punctuation or quotes.
    3. Infer the Spanish Part-of-Speech (POS) tag based on the Spanish definition (e.g., if it translates to 'cantar', it's a VERB. If it means 'árbol', it's a NOUN). If it's a short idiom or common phrase, use 'PHRASE'.
    4. Mark 'is_valid' as False if the entry is a full conversational sentence (e.g., 'Mi esposa dice', 'Yo dije', 'Él le dijo a ella') or garbage. We only want vocabulary words, short idioms, or cultural terms.
    
    Process the following batch of extracted entries:
    {json_data}
    """

    for i in range(0, len(entries), batch_size):
        batch = entries[i:i+batch_size]
        log.info(f"Processing batch {i//batch_size + 1}/{(len(entries) + batch_size - 1)//batch_size} ({len(batch)} items)")
        
        # Prepare succinct input to save tokens
        input_data = [{"id": j, "ayoreo": e["ayoreo"], "spanish": e["spanish"]} for j, e in enumerate(batch)]
        prompt = prompt_template.format(json_data=json.dumps(input_data, ensure_ascii=False, indent=2))
        
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DictionaryResult,
                    temperature=0.1,
                ),
            )
            
            result_data = response.parsed
            
            # Map back to add sources and filter valid ones
            for j, cleaned in enumerate(result_data.entries):
                if cleaned.is_valid:
                    cleaned_entries.append({
                        "ayoreo": cleaned.ayoreo.strip(),
                        "spanish": cleaned.spanish.strip(),
                        "pos_tag": cleaned.pos_tag,
                        "source": batch[j].get("source", "unknown")
                    })
                    
        except Exception as e:
            log.error(f"Error processing batch {i//batch_size + 1}: {e}")
            # In a production script we might retry, but we'll just skip here for simplicity if it fails consistently
            continue

    return cleaned_entries

def main():
    glossaries_path = PROCESSED_DIR / "glossaries.json"
    if not glossaries_path.exists():
        log.error(f"Glossaries file not found at {glossaries_path}")
        return

    with open(glossaries_path, encoding="utf-8") as f:
        glossaries = json.load(f)
        
    log.info(f"Loaded {len(glossaries)} raw glossary entries. Starting Gemini cleaning...")
    
    # We might want to deduplicate by ayoreo term first before sending to API to save tokens
    unique_glossaries = []
    seen = set()
    for g in glossaries:
        # Simple heuristic filter to avoid sending obvious full paragraphs to the API
        if len(g["ayoreo"].split()) > 6 or len(g["spanish"].split()) > 20:
             continue
        if g["ayoreo"].lower() not in seen:
            seen.add(g["ayoreo"].lower())
            unique_glossaries.append(g)
            
    log.info(f"Filtered down to {len(unique_glossaries)} valid candidate entries based on length.")
    
    cleaned_dictionary = batch_process_glossaries(unique_glossaries, batch_size=40)
    
    # Deduplicate again just in case Gemini normalized different words to the same string
    final_dict = []
    final_seen = set()
    for entry in cleaned_dictionary:
        if entry["ayoreo"] not in final_seen:
            final_seen.add(entry["ayoreo"])
            final_dict.append(entry)
            
    # Save the dictionary
    out_path = PROCESSED_DIR / "dictionary_ayoreo_espanol.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final_dict, f, ensure_ascii=False, indent=2)
        
    log.info(f"Successfully cleaned and saved {len(final_dict)} dictionary entries to {out_path}.")

if __name__ == "__main__":
    main()
