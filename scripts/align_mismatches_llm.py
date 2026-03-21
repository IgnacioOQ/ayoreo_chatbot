import argparse
import json
import os
import shutil
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel
from tqdm import tqdm
from typing import List, Optional, Tuple

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("token_tracker")

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("google-genai library is missing. Please install it with: pip install google-genai")
    exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = PROJECT_ROOT / "data" / "raw" / "ayoreoorg" / "ayoreoorg.json"
ALIGNED_JSON_PATH = PROJECT_ROOT / "data" / "raw" / "ayoreoorg" / "aligned_ayoreoorg.json"

# Pydantic Schemas for Structured Output
class AlignmentBlock(BaseModel):
    en: List[int]
    ayo: List[int]
    es: Optional[List[int]] = None  # Spanish is optional; omit or leave null when not present

class AlignmentResponse(BaseModel):
    alignment: List[AlignmentBlock]

# COMPRESSED SEMANTIC MATCHING PROTOCOL
SYSTEM_PROMPT = """Align parallel texts across high-resource English (EN) and low-resource Ayoreo (AYO).
Output ONLY JSON matching the schema. No preamble.

Anchor Heuristic Protocol:
1. Anchor Alignment: Use English (EN) as the primary anchor. Map EN chunks to AYO chunks based on semantics.
2. Narrative Sequencing: Establish chronological narrative progression from EN.
3. Low-Resource Anchoring: Scan Ayoreo chunks for shared entities (proper nouns, numbers, quotes) and structural heuristics (text length) to anchor to EN.
4. Monotonicity: Chunks ALWAYS appear chronologically.
5. Missing Languages: If a translation is entirely missing, map it to empty array [].
   CRITICAL (MISSING INTRO): Missing Ayoreo components almost always occur at the VERY BEGINNING (meta-comments omitted in translation).
   CRITICAL (SIZE MATCHING): Do not associate a short, 1-sentence EN chunk with a massive Ayoreo paragraph. They DO NOT MATCH. Map short meta-comments to [].
6. Spanish (ES) is optional supplementary input. If provided, use it to cross-check EN anchoring only.

Input: EN and AYO text block arrays (ES is optional).
Output: Array of unified semantic blocks mapping indices from EN/AYO (and ES if provided)."""


def get_entries_to_process(dataset):
    return dataset

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

def align_story(client, cache_name, story_id, entry) -> Tuple[Optional[list], int, int, int]:
    """Align one story via the Gemini API.

    Returns:
        (alignment_map, input_tokens, output_tokens, total_tokens)
        alignment_map is None on failure; token counts are 0 on failure.
    """
    deco = entry.get("body_decomposition", {})

    en_flat  = flatten_for_prompt(deco.get('en',  []))
    ayo_flat = flatten_for_prompt(deco.get('ayo', []))
    es_flat  = flatten_for_prompt(deco.get('es',  []))  # optional

    max_blocks = max(len(en_flat), len(ayo_flat))
    est_out_tokens = max(128, int(max_blocks * 25))

    prompt = f"""Story ID: {story_id}

EN: {json.dumps(en_flat, separators=(',', ':'), ensure_ascii=False)}
AYO: {json.dumps(ayo_flat, separators=(',', ':'), ensure_ascii=False)}"""

    if es_flat:
        prompt += f"\nES (optional): {json.dumps(es_flat, separators=(',', ':'), ensure_ascii=False)}"

    # Build config: use cache if available, otherwise pass system_instruction inline.
    # Disable thinking — this is a structural task; thinking tokens bypass max_output_tokens.
    config_kwargs = dict(
        response_mime_type="application/json",
        response_schema=AlignmentResponse.model_json_schema(),
        max_output_tokens=est_out_tokens,
        temperature=0.1,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )
    if cache_name:
        config_kwargs["cached_content"] = cache_name
    else:
        config_kwargs["system_instruction"] = SYSTEM_PROMPT

    prompt_kwargs = {
        "model": 'gemini-2.5-flash',
        "contents": prompt,
        "config": types.GenerateContentConfig(**config_kwargs),
    }

    response = call_with_retry(client.models.generate_content, prompt_kwargs)

    if not response:
        return None, 0, 0, 0

    meta = response.usage_metadata
    in_tok  = meta.prompt_token_count     or 0
    out_tok = meta.candidates_token_count or 0
    tot_tok = meta.total_token_count      or 0

    try:
        parsed = json.loads(response.text)
        return parsed.get("alignment", []), in_tok, out_tok, tot_tok
    except Exception as e:
        logger.error(f"Failed to parse model output: {e}\nOutput: {response.text}")
        return None, in_tok, out_tok, tot_tok


def main():
    parser = argparse.ArgumentParser(description="Semantic alignment of EN↔AYO story chunks via Gemini.")
    parser.add_argument(
        "--max-tokens", type=int, default=4_000_000, metavar="N",
        help="Stop after spending this many total tokens in the session (resumes automatically on next run). Default: 4,000,000.",
    )
    args = parser.parse_args()

    try:
        client = genai.Client()
    except Exception as e:
        print(f"Failed to initialize Gemini Client. Make sure you have authentication configured. Error: {e}")
        return

    load_path = ALIGNED_JSON_PATH if ALIGNED_JSON_PATH.exists() else JSON_PATH

    # Back up existing aligned file before making any changes
    if ALIGNED_JSON_PATH.exists():
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = ALIGNED_JSON_PATH.with_name(f"aligned_ayoreoorg_backup_{ts}.json")
        shutil.copy2(ALIGNED_JSON_PATH, backup_path)
        print(f"Backed up existing aligned data to: {backup_path.name}")

    with open(load_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    entries_to_process = get_entries_to_process(dataset)

    already_done = sum(1 for e in entries_to_process.values() if "alignment_map" in e)
    remaining    = len(entries_to_process) - already_done
    print(f"Stories: {len(entries_to_process)} total — {already_done} already aligned, {remaining} to process.")
    print(f"Token budget for this session: {args.max_tokens:,}")

    # Try to create a context cache for the system prompt (requires ~32k+ tokens minimum).
    # Our prompt is small, so this will likely fail — fall back to inline system_instruction.
    cache_name = None
    print("Attempting to create Context Cache for System Prompt...")
    try:
        cache = client.caches.create(
            model="gemini-2.5-flash",
            config=types.CreateCachedContentConfig(
                display_name="ayoreoorg_alignment_cache",
                system_instruction=SYSTEM_PROMPT,
                ttl="3600s"
            )
        )
        cache_name = cache.name
        print(f"Cache created successfully: {cache_name}")
    except Exception as e:
        print(f"Cache creation failed (expected if prompt < 32k tokens) — using inline system instruction. ({e})")

    # Session token counters
    session_input  = 0
    session_output = 0
    session_total  = 0
    processed      = 0
    threshold_hit  = False

    # Two progress bars: one for stories, one for the token budget
    story_bar = tqdm(
        total=remaining,
        desc="Stories  ",
        unit="story",
        position=0,
        leave=True,
    )
    token_bar = tqdm(
        total=args.max_tokens,
        desc="Tokens   ",
        unit="tok",
        unit_scale=True,
        position=1,
        leave=True,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
    )

    try:
        for story_id, entry in entries_to_process.items():
            if "alignment_map" in entry:
                continue

            # Check token budget BEFORE making the next request
            if session_total >= args.max_tokens:
                tqdm.write(
                    f"\nToken budget reached: {session_total:,} / {args.max_tokens:,} tokens used. Stopping.\n"
                    f"Run the script again to continue — already-aligned stories will be skipped automatically."
                )
                threshold_hit = True
                break

            story_bar.set_description(f"Stories   [{story_id[:40]}]")
            alignment_map, in_tok, out_tok, tot_tok = align_story(client, cache_name, story_id, entry)

            session_input  += in_tok
            session_output += out_tok
            session_total  += tot_tok
            processed      += 1

            story_bar.update(1)
            token_bar.update(tot_tok)
            token_bar.set_postfix({"in": f"{session_input:,}", "out": f"{session_output:,}"})

            if alignment_map:
                tqdm.write(f"  ✓ {story_id}  ({in_tok:,} in / {out_tok:,} out)")
                dataset[story_id]["alignment_map"] = json.dumps(alignment_map)
                with open(ALIGNED_JSON_PATH, "w", encoding="utf-8") as f:
                    json.dump(dataset, f, indent=2, ensure_ascii=False)
            else:
                tqdm.write(f"  ✗ {story_id}  — alignment failed, skipping.")

            time.sleep(2)  # rate limit safety

    finally:
        story_bar.close()
        token_bar.close()

    # Final summary
    print("\n=== Session Summary ===")
    print(f"  Stories processed this session : {processed}")
    print(f"  Input tokens                   : {session_input:,}")
    print(f"  Output tokens                  : {session_output:,}")
    print(f"  Total tokens                   : {session_total:,}")
    status = "budget reached" if threshold_hit else "within budget"
    print(f"  Budget ({args.max_tokens:,})        : {status}")
    already_done_now = sum(1 for e in dataset.values() if "alignment_map" in e)
    print(f"  Total stories aligned to date  : {already_done_now} / {len(dataset)}")
    if already_done_now < len(dataset):
        print(f"  {len(dataset) - already_done_now} stories remaining — run again to continue.")
    else:
        print("  All stories aligned!")


if __name__ == "__main__":
    main()
