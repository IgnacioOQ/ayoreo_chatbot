import json

path = "data/raw/ayoreoorg/ayoreoorg.json"
try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Loaded {len(data)} entries.")
    
    inconsistent_counts = []
    
    for story_id, entry in data.items():
        deco = entry.get("body_decomposition", {})
        counts = {lang: len(deco.get(lang, [])) for lang in ["es", "en", "ayo"]}
        
        # Check if all counts are identical
        if len(set(counts.values())) > 1:
            inconsistent_counts.append({
                "story_id": story_id,
                "counts": counts
            })
            
    print(f"\nFound {len(inconsistent_counts)} inconsistencies.")
    for inc in inconsistent_counts:
        print(f"{inc['story_id']}: {inc['counts']}")

except Exception as e:
    print(f"Error: {e}")
