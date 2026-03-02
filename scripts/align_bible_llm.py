import json
import os
from pathlib import Path

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("google-genai library is missing. Please install it with: pip install google-genai")
    exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = PROJECT_ROOT / "data" / "raw" / "bible" / "bible.json"
ALIGNED_JSON_PATH = PROJECT_ROOT / "data" / "raw" / "bible" / "aligned_bible.json"

# SEMANTIC MATCHING PROTOCOL PROMPT
SYSTEM_PROMPT = """You are an expert linguistic alignment AI specializing in matching parallel texts across high-resource languages (Spanish, English) and structurally opaque low-resource languages (Ayoreo).

Your goal is to perfectly align paragraphs of the exact same semantic unit of translation. However, because Ayoreo text parsing often yields a different number of paragraphs compared to Spanish/English, you must map the array indices.

You MUST follow this exact Anchor Heuristic Protocol step by step in your reasoning:
1. High-Resource Anchor Alignment: Create a perfect mapping between the parsed Spanish (ES) and English (EN) chunks based strictly on semantics.
2. Narrative Sequencing: Establish the exact narrative progression.
3. Low-Resource Anchoring: Scan the opaque Ayoreo chunks for shared entities (e.g., proper nouns, numbers, punctuation patterns like quotation marks) and structural heuristics (e.g., overall text length, matching short components to short components, and long components to long components) that transcend translation to anchor to the ES/EN maps.
4. Monotonic Structural Constraints: The chunks ALWAYS appear chronologically.
5. Missing Languages: If a translation is entirely missing (e.g. the Ayoreo array is empty/null), you still MUST output its key in every grouping, but its value MUST be an empty array `[]`. 
   **CRITICAL HEURISTIC:** In most cases where Ayoreo components are missing, it happens at the VERY BEGINNING of the story rather than the end. This is because Spanish/English descriptions often start with meta-comments or context that is completely omitted in the Ayoreo translations.

We will provide you the body_decomposition arrays for 'es', 'en', and 'ayo', where the structure is a list of {"header": str|null, "text": str}.
You must output a JSON list where each item represents a unified semantic block, mapping which indices from the ES, EN, and AYO arrays belong to it.
"""

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

def align_story(client, story_id, entry):
    deco = entry.get("body_decomposition", {})
    
    # Prompt payload
    prompt = f"""Story ID: {story_id}

ES Decompositions:
{json.dumps(deco.get('es', []), indent=2, ensure_ascii=False)}

EN Decompositions:
{json.dumps(deco.get('en', []), indent=2, ensure_ascii=False)}

AYO Decompositions:
{json.dumps(deco.get('ayo', []), indent=2, ensure_ascii=False)}
"""

    print(f"Aligning {story_id}...")
    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema={
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "es": {
                                "type": "ARRAY",
                                "items": {"type": "INTEGER"},
                                "description": "List of indices from the ES array that belong to this semantic block"
                            },
                            "en": {
                                "type": "ARRAY",
                                "items": {"type": "INTEGER"},
                                "description": "List of indices from the EN array that belong to this semantic block"
                            },
                            "ayo": {
                                "type": "ARRAY",
                                "items": {"type": "INTEGER"},
                                "description": "List of indices from the AYO array that belong to this semantic block"
                            }
                        },
                        "required": ["es", "en", "ayo"]
                    }
                },
                temperature=0.1,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Failed to align {story_id}: {e}")
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
    for story_id, entry in mismatches.items():
        if "alignment_map" in entry:
            print(f"Skipping {story_id}, already aligned.")
            continue
            
        alignment_map = align_story(client, story_id, entry)
        
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
