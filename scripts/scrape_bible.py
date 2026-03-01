import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import time
from datetime import datetime

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BIBLE_DIR = PROJECT_ROOT / "data" / "raw" / "bible"
BIBLE_JSON = BIBLE_DIR / "bible.json"
SUMMARY_JSON = BIBLE_DIR / "bible_scraping_summary.json"

BIBLE_DIR.mkdir(parents=True, exist_ok=True)

# URL Templates
URLS = {
    "ayo": "https://www.bible.com/es-ES/bible/2825/GEN.{chapter}.AYORE",
    "es": "https://www.bible.com/es-ES/bible/3291/GEN.{chapter}.VBL",
    "en": "https://www.bible.com/es-ES/bible/1932/GEN.{chapter}.FBV"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
}

def extract_chapter(url: str, chapter: int) -> list:
    print(f"  Fetching {url}...")
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"  [Error] Failed to fetch {url}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    verse_elements = soup.find_all(attrs={"data-usfm": True})
    
    verses_map = {}
    
    for el in verse_elements:
        usfm = el.get("data-usfm")
        # Ensure it belongs to the current chapter (e.g., GEN.1.X)
        if not usfm.startswith(f"GEN.{chapter}."):
            continue
            
        verse_num_str = usfm.split(".")[-1]
        
        # Following user request: target the specific ChapterContent label spans to organically 
        # separate verse numbers from the body content. We remove those label tags so the raw 
        # extracted text doesn't contain leading verse numbers (e.g. '1 In the beginning' -> 'In the beginning')
        for label in el.find_all("span", class_=lambda c: c and 'label' in c.lower() and 'chaptercontent' in c.lower()):
            label.decompose()
            
        text = el.get_text(separator=" ", strip=True)
        if not text:
            continue
            
        header = f"Genesis {chapter},{verse_num_str}"
        
        if header not in verses_map:
            verses_map[header] = []
        verses_map[header].append(text)
        
    decomposition = []
    # Merge disjoint spans of the same verse perfectly
    for header, text_list in verses_map.items():
        decomposition.append({
            "header": header,
            "text": " ".join(text_list).strip()
        })
        
    return decomposition

def main(test_run=False):
    max_chapters = 1 if test_run else 50
    
    output_data = {}
    summary = {
        "execution_date": datetime.now().isoformat(),
        "total_chapters_scraped": 0,
        "sources": URLS,
        "chapters": []
    }
    
    print(f"Starting Genesis extraction (1 to {max_chapters})...")
    
    for chapter in range(1, max_chapters + 1):
        print(f"\\nProcessing Chapter {chapter}...")
        
        entry_id = f"genesis-{chapter}"
        
        decomp_es = extract_chapter(URLS["es"].format(chapter=chapter), chapter)
        decomp_en = extract_chapter(URLS["en"].format(chapter=chapter), chapter)
        decomp_ayo = extract_chapter(URLS["ayo"].format(chapter=chapter), chapter)
        
        body_es = "\\n\\n".join([d["text"] for d in decomp_es])
        body_en = "\\n\\n".join([d["text"] for d in decomp_en])
        body_ayo = "\\n\\n".join([d["text"] for d in decomp_ayo])
        
        output_data[entry_id] = {
            "story_id": entry_id,
            "url_es": URLS["es"].format(chapter=chapter),
            "url_en": URLS["en"].format(chapter=chapter),
            "url_ayo": URLS["ayo"].format(chapter=chapter),
            "type": "faith",
            "section": "Genesis",
            "chapter": chapter,
            "title_es": f"Génesis {chapter}",
            "title_en": f"Genesis {chapter}",
            "title_ayo": f"Génesis {chapter}",
            "body_es": body_es,
            "body_en": body_en,
            "body_ayo": body_ayo,
            "body_decomposition": {
                "es": decomp_es,
                "en": decomp_en,
                "ayo": decomp_ayo
            }
        }
        
        summary["chapters"].append(chapter)
        summary["total_chapters_scraped"] += 1
        
        # Be nice to the servers
        time.sleep(1.5)
        
    with open(BIBLE_JSON, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        
    print(f"\\n✅ Successfully saved {len(output_data)} chapters to {BIBLE_JSON}")
    print(f"✅ Saved scraping execution log to {SUMMARY_JSON}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-run", action="store_true", help="Only scrape Chapter 1")
    args = parser.parse_args()
    
    main(test_run=args.test_run)
