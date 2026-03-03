import json
import os
import time
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("token_tracker")

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("google-genai library is missing. Please install it with: pip install google-genai")
    exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = PROJECT_ROOT / "data" / "raw" / "bible" / "bible.json"
ALIGNED_JSON_PATH = PROJECT_ROOT / "data" / "raw" / "bible" / "aligned_bible.json"

# Pydantic Schemas for Structured Output
class AlignmentBlock(BaseModel):
    es: List[int]
    en: List[int]
    ayo: List[int]

class AlignmentResponse(BaseModel):
    alignment: List[AlignmentBlock]

# COMPRESSED SEMANTIC MATCHING PROTOCOL
SYSTEM_PROMPT = """Align parallel texts across high-resource (Spanish/English) and low-resource (Ayoreo) languages.
Output ONLY JSON matching the schema. No preamble.

Anchor Heuristic Protocol:
1. Anchor Alignment: Perfectly map parsed Spanish (ES) and English (EN) chunks based on semantics.
2. Narrative Sequencing: Establish chronological narrative progression.
3. Low-Resource Anchoring: Scan Ayoreo chunks for shared entities (proper nouns, numbers, quotes) and structural heuristics (text length) to anchor to ES/EN maps.
4. Monotonicity: Chunks ALWAYS appear chronologically.
5. Missing Languages: If a translation is entirely missing, map it to empty array [].
   CRITICAL (MISSING INTRO): Missing Ayoreo components almost always occur at the VERY BEGINNING (meta-comments omitted in translation).
   CRITICAL (SIZE MATCHING): Do not associate a short, 1-sentence ES/EN chunk with a massive Ayoreo paragraph. They DO NOT MATCH. Map short meta-comments to [].

Input: ES, EN, and AYO text block arrays.
Output: Array of unified semantic blocks mapping indices from ES/EN/AYO."""

def get_mismatched_entries(dataset):
    mismatches = {}
    for story_id, entry in dataset.items():
        is_mismatched = False
        warnings = entry.get("warnings", [])
        for warning in warnings:
            if "Translation Verse Mismatch" in warning or "Translation Value Mismatch" in warning:
                is_mismatched = True
                break
                
        if is_mismatched:
            mismatches[story_id] = entry
    return mismatches

def call_with_retry(call_fn, prompt_kwargs, max_retries=3, base_delay=1.0):
    for attempt in range(max_retries):
        try:
            return call_fn(**prompt_kwargs)
        except Exception as e:
            error_code = getattr(e, 'code', None)
            if error_code in (400, 403):
                logger.error(f"Non-retryable error ({error_code}): {e}")
                return None
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Retryable error (attempt {attempt + 1}/{max_retries}): {e}. Waiting {delay}s.")
            time.sleep(delay)
    logger.error("Max retries exceeded.")
    return None

def flatten_for_prompt(decompositions: list) -> list:
    # Field Pruning: Extract only 'text', dropping 'header' overhead
    if not decompositions:
        return []
    return [comp.get('text', '') for comp in decompositions]

def align_story(client, cache_name, story_id, entry):
    deco = entry.get("body_decomposition", {})
    
    # Prompt payload minified and pruned
    es_flat = flatten_for_prompt(deco.get('es', []))
    en_flat = flatten_for_prompt(deco.get('en', []))
    ayo_flat = flatten_for_prompt(deco.get('ayo', []))
    
    # Calculate output cap: rough estimate based on array lengths + buffer
    max_blocks = max(len(es_flat), len(en_flat), len(ayo_flat))
    # 3 languages * ~8 chars per index array * ~max_blocks + base json overhead
    est_out_tokens = max(128, int(max_blocks * 25))

    prompt = f"""Story ID: {story_id}

ES: {json.dumps(es_flat, separators=(',', ':'), ensure_ascii=False)}
EN: {json.dumps(en_flat, separators=(',', ':'), ensure_ascii=False)}
AYO: {json.dumps(ayo_flat, separators=(',', ':'), ensure_ascii=False)}"""

    print(f"Aligning {story_id}...")
    
    prompt_kwargs = {
        "model": 'gemini-2.5-flash',
        "contents": prompt,
        "config": types.GenerateContentConfig(
            cached_content=cache_name,
            response_mime_type="application/json",
            response_schema=AlignmentResponse.model_json_schema(),
            max_output_tokens=est_out_tokens,
            temperature=0.1,
        )
    }

    response = call_with_retry(client.models.generate_content, prompt_kwargs)
    
    if not response:
        return None

    meta = response.usage_metadata
    logger.info(
        f"[{story_id}] input={meta.prompt_token_count} "
        f"output={meta.candidates_token_count} "
        f"total={meta.total_token_count}"
    )

    try:
        parsed = json.loads(response.text)
        return parsed.get("alignment", [])  # Flatten back from Pydantic wrapper
    except Exception as e:
        logger.error(f"Failed to parse model output: {e}\nOutput: {response.text}")
        return None

def main():
    try:
        client = genai.Client()
    except Exception as e:
        print(f"Failed to initialize Gemini Client. Make sure you have authentication configured. Error: {e}")
        return
    
    load_path = ALIGNED_JSON_PATH if ALIGNED_JSON_PATH.exists() else JSON_PATH
    with open(load_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    mismatches = get_mismatched_entries(dataset)
    print(f"Found {len(mismatches)} mismatched stories.")
    
    import time
    
    print("Creating Context Cache for System Prompt...")
    try:
        cache = client.caches.create(
            model="gemini-2.5-flash",
            config=types.CreateCachedContentConfig(
                display_name="bible_alignment_cache",
                system_instruction=SYSTEM_PROMPT,
                ttl="3600s" # 1 hour
            )
        )
        cache_name = cache.name
        print(f"Cache created successfully: {cache_name}")
    except Exception as e:
        print(f"Failed to create cache. Ensure your model supports explicit caching. Error: {e}")
        return

    for story_id, entry in mismatches.items():
        if "alignment_map" in entry:
            print(f"Skipping {story_id}, already aligned.")
            continue
            
        alignment_map = align_story(client, cache_name, story_id, entry)
        
        if alignment_map:
            print(f"\nResult for {story_id}:")
            print(json.dumps(alignment_map, indent=2))
            
            # Save it back as a string to the JSON format used in sanity_app.py
            dataset[story_id]["alignment_map"] = json.dumps(alignment_map)
            with open(ALIGNED_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(dataset, f, indent=2, ensure_ascii=False)
            print("Saved update to aligned_bible.json!")
            
            time.sleep(2) # rate limit safety
    
    print("Alignment process complete.")

if __name__ == "__main__":
    main()
