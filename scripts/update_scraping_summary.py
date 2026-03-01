"""Update scraping_summary.json with the results of the 'creencias' scrape."""

import json
from pathlib import Path

def update_summary():
    project_root = Path(__file__).resolve().parent.parent
    ayoreoorg_path = project_root / "data" / "raw" / "ayoreoorg" / "ayoreoorg.json"
    summary_path = project_root / "data" / "raw" / "ayoreoorg" / "scraping_summary.json"
    
    if not ayoreoorg_path.exists():
        print("ayoreoorg.json not found")
        return
        
    with open(ayoreoorg_path, "r", encoding="utf-8") as f:
        stories = json.load(f)
        
    # Build list of summary objects based on stories.json
    pages = []
    scraped_count = 0
    for story_id, data in stories.items():
        pages.append({
            "story_id": story_id,
            "section": data.get("section", ""),
            "url_es": data.get("url_es"),
            "url_en": data.get("url_en"),
            "url_ayo": data.get("url_ayo"),
            "has_es": bool(data.get("url_es")),
            "has_en": bool(data.get("url_en")),
            "has_ayo": bool(data.get("url_ayo"))
        })
        scraped_count += 1
        
    summary = {
        "total_discovered": scraped_count,
        "scraped": scraped_count,
        "failed": 0,
        "pages": pages
    }
    
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        
    print(f"Updated scraping_summary.json with {scraped_count} stories")

if __name__ == "__main__":
    update_summary()
