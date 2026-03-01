"""Migrate existing stories data to ayoreoorg.json with type fields."""

import json
from pathlib import Path

def migrate_data():
    project_root = Path(__file__).resolve().parent.parent
    old_target = project_root / "data" / "raw" / "stories.json"
    new_target = project_root / "data" / "raw" / "ayoreoorg.json"
    
    if not old_target.exists():
        print(f"File not found: {old_target}")
        return
        
    with open(old_target, "r", encoding="utf-8") as f:
        stories = json.load(f)
        
    for story_id, data in stories.items():
        # Set all existing stories to type "personal_narrative" as requested
        data["type"] = "personal_narrative"
        
    new_target.parent.mkdir(parents=True, exist_ok=True)
    with open(new_target, "w", encoding="utf-8") as f:
        json.dump(stories, f, ensure_ascii=False, indent=2)
        
    print(f"Migrated {len(stories)} stories from {old_target.name} to {new_target.name}")

if __name__ == "__main__":
    migrate_data()
