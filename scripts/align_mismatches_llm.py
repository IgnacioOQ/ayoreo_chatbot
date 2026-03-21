import argparse
import json
import os
import shutil
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from tqdm import tqdm
from typing import Optional, Tuple

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

# Max EN chunks per Gemini call. Stories exceeding this are split into windows.
WINDOW_SIZE = 20

# COMPRESSED SEMANTIC MATCHING PROTOCOL
SYSTEM_PROMPT = """Align parallel texts across high-resource English (EN) and low-resource Ayoreo (AYO).
Output ONLY compact minified JSON (no extra whitespace). No preamble.

Output format: {"alignment":[{"en":[<indices>],"ayo":[<indices>]},...]

Rules:
1. Anchor Alignment: Use English (EN) as the primary anchor. Map EN chunks to AYO chunks based on semantics.
2. Narrative Sequencing: Establish chronological narrative progression from EN.
3. Low-Resource Anchoring: Scan Ayoreo chunks for shared entities (proper nouns, numbers, quotes) and structural heuristics (text length) to anchor to EN.
4. Monotonicity: Chunks ALWAYS appear chronologically.
5. Missing Languages: If a translation is entirely missing, map it to empty array [].
   CRITICAL (MISSING INTRO): Missing Ayoreo components almost always occur at the VERY BEGINNING (meta-comments omitted in translation).
   CRITICAL (SIZE MATCHING): Do not associate a short, 1-sentence EN chunk with a massive Ayoreo paragraph. They DO NOT MATCH. Map short meta-comments to [].
6. Index bounds: all EN indices must be in [0, N_EN-1], all AYO indices in [0, N_AYO-1]. Never output indices outside these ranges.
7. Coverage: every EN index 0..N_EN-1 must appear in exactly one block. Every AYO index 0..N_AYO-1 must appear in at most one block.

Input: EN and AYO text block arrays.
Output: Compact JSON alignment mapping local indices."""


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

def _call_align_window(
    client, cache_name, story_id,
    en_slice: list, ayo_slice: list,
    en_offset: int, ayo_offset: int,
) -> Tuple[Optional[list], int, int, int]:
    """Single Gemini call for one window. Returns blocks with indices adjusted by offsets."""
    n_en  = len(en_slice)
    n_ayo = len(ayo_slice)
    prompt = f"""Story ID: {story_id} | EN indices 0-{n_en-1} ({n_en} items) | AYO indices 0-{n_ayo-1} ({n_ayo} items)

EN: {json.dumps(en_slice, separators=(',', ':'), ensure_ascii=False)}
AYO: {json.dumps(ayo_slice, separators=(',', ':'), ensure_ascii=False)}"""

    config_kwargs = dict(
        response_mime_type="application/json",
        temperature=0.1,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        max_output_tokens=8192,
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

    if not response.text:
        for candidate in (response.candidates or []):
            logger.error(
                f"Empty response for [{story_id}] en[{en_offset}..] — "
                f"finish_reason={candidate.finish_reason}, "
                f"safety_ratings={candidate.safety_ratings}"
            )
        if not response.candidates:
            logger.error(f"Empty response for [{story_id}] en[{en_offset}..] — no candidates.")
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
            logger.error(f"Prompt feedback for [{story_id}]: {response.prompt_feedback}")
        return None, in_tok, out_tok, tot_tok

    try:
        parsed = json.loads(response.text)
        blocks = parsed.get("alignment", [])
        # Adjust local window indices back to global story indices
        adjusted = [
            {
                "en":  [i + en_offset  for i in block.get("en",  [])],
                "ayo": [i + ayo_offset for i in block.get("ayo", [])],
            }
            for block in blocks
        ]
        return adjusted, in_tok, out_tok, tot_tok
    except Exception as e:
        logger.error(f"Failed to parse model output for [{story_id}] en[{en_offset}..]: {e}\nOutput: {response.text[:500]}")
        return None, in_tok, out_tok, tot_tok


def align_story(client, cache_name, story_id, entry) -> Tuple[Optional[list], int, int, int]:
    """Align one story via the Gemini API.

    Returns:
        (alignment_map, input_tokens, output_tokens, total_tokens)
        alignment_map is None on failure; [] for skipped (EN=0); token counts are 0 on skip/failure.
    """
    deco = entry.get("body_decomposition", {})
    en_flat  = flatten_for_prompt(deco.get('en',  []))
    ayo_flat = flatten_for_prompt(deco.get('ayo', []))

    # No English content — nothing to anchor alignment against; skip API call.
    if not en_flat:
        logger.info(f"Skipping [{story_id}] — no EN content (EN=0, AYO={len(ayo_flat)})")
        return [], 0, 0, 0

    # Small story: single API call
    if len(en_flat) <= WINDOW_SIZE:
        return _call_align_window(client, cache_name, story_id, en_flat, ayo_flat, 0, 0)

    # Large story: windowed batching
    logger.info(f"Windowed alignment for [{story_id}] — EN={len(en_flat)}, AYO={len(ayo_flat)}")
    n_en  = len(en_flat)
    n_ayo = len(ayo_flat)
    ratio = n_ayo / n_en  # AYO chunks per EN chunk

    all_blocks: list = []
    total_in = total_out = total_tok = 0
    ayo_cursor = 0
    en_start   = 0

    while en_start < n_en:
        en_end   = min(en_start + WINDOW_SIZE, n_en)
        en_slice = en_flat[en_start:en_end]

        # Proportional AYO window with 30% buffer; last EN window gets all remaining AYO
        if en_end == n_en:
            ayo_end = n_ayo
        else:
            ayo_window = max(1, round(len(en_slice) * ratio * 1.3))
            ayo_end = min(ayo_cursor + ayo_window, n_ayo)
        ayo_slice = ayo_flat[ayo_cursor:ayo_end]

        blocks, in_tok, out_tok, tok = _call_align_window(
            client, cache_name, story_id, en_slice, ayo_slice, en_start, ayo_cursor
        )
        total_in  += in_tok
        total_out += out_tok
        total_tok += tok

        if blocks is None:
            return None, total_in, total_out, total_tok

        all_blocks.extend(blocks)

        # Advance AYO cursor to just past the last AYO index used in this window
        max_ayo_used = ayo_cursor - 1
        for block in blocks:
            if block.get("ayo"):
                max_ayo_used = max(max_ayo_used, max(block["ayo"]))
        ayo_cursor = max_ayo_used + 1

        en_start = en_end
        if en_start < n_en:
            time.sleep(1)  # brief pause between windows

    return all_blocks, total_in, total_out, total_tok


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
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%Hh%M")
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

            if alignment_map is not None:
                label = "skipped (EN=0)" if not alignment_map else f"{in_tok:,} in / {out_tok:,} out"
                tqdm.write(f"  ✓ {story_id}  ({label})")
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
