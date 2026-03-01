import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import time
from datetime import datetime
import re

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BIBLE_DIR = PROJECT_ROOT / "data" / "raw" / "bible"
BIBLE_JSON = BIBLE_DIR / "bible.json"
SUMMARY_JSON = BIBLE_DIR / "bible_scraping_summary.json"

BIBLE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
}

def extract_chapter_data(url: str, expected_usfm_prefix: str) -> dict:
    print(f"  Fetching {url}...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"  [Error] Failed to fetch {url} - Status: {response.status_code}")
            return None
    except Exception as e:
        print(f"  [Error] Exception fetching {url}: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract Title (e.g. "Éxodo 1")
    h1 = soup.find('h1')
    title = h1.text.strip() if h1 else "Unknown Title"
    
    # Extract Section (e.g. "Éxodo") by stripping numbers
    parts = title.rsplit(' ', 1)
    if len(parts) == 2 and parts[1].isdigit():
        section = parts[0]
    else:
        section = title
    
    verse_elements = soup.find_all(attrs={"data-usfm": True})
    verses_map = {}
    
    chapter_num = title.split()[-1]
    
    for el in verse_elements:
        usfm = el.get("data-usfm")
        # Handle merged verses like "1SA.31.11+1SA.31.12"
        usfm_parts = usfm.split("+")
        # Ensure at least one part belongs to this chapter
        if not any(p.startswith(expected_usfm_prefix + ".") for p in usfm_parts):
            continue
        
        # Build verse number string: single verse or range (e.g. "11-12")
        verse_nums = []
        for p in usfm_parts:
            if p.startswith(expected_usfm_prefix + "."):
                verse_nums.append(p.split(".")[-1])
        if not verse_nums:
            continue
        verse_num_str = "-".join(verse_nums) if len(verse_nums) > 1 else verse_nums[0]
        
        # Scrub verse index artifacts from HTML spans
        for label in el.find_all("span", class_=lambda c: c and 'label' in c.lower() and 'chaptercontent' in c.lower()):
            label.decompose()
            
        text = el.get_text(separator=" ", strip=True)
        if not text:
            continue
            
        header = f"{section} {chapter_num},{verse_num_str}"
        
        if header not in verses_map:
            verses_map[header] = []
        verses_map[header].append(text)
        
    decomposition = []
    # Merge disjoint spans mapping to the exact same verse together
    for header, text_list in verses_map.items():
        decomposition.append({
            "header": header,
            "text": " ".join(text_list).strip()
        })
        
    next_url = None
    # Locate the definitive 'Next Chapter' hyperlink
    for a in soup.find_all('a', href=True):
        if 'Siguiente capítulo' in a.text:
            next_url = "https://www.bible.com" + a['href']
            break

    return {
        "title": title,
        "section": section,
        "decomposition": decomposition,
        "next_url": next_url,
        "verse_count": len(decomposition)
    }


def main(test_run=False):
    # Stateful payload loading
    if BIBLE_JSON.exists():
        with open(BIBLE_JSON, "r", encoding="utf-8") as f:
            output_data = json.load(f)
    else:
        output_data = {}
        
    if SUMMARY_JSON.exists():
        with open(SUMMARY_JSON, "r", encoding="utf-8") as f:
            summary = json.load(f)
            if "mismatches" not in summary:
                summary["mismatches"] = []
            if "history" not in summary:
                summary["history"] = []
    else:
        summary = {
            "execution_date": datetime.now().isoformat(),
            "total_chapters_scraped": 0,
            "mismatches": [],
            "history": []
        }
    
    current_ayo_url = "https://www.bible.com/es-ES/bible/2825/GEN.1.AYORE"
    chapters_processed_this_run = 0
    
    print("Starting Bible extraction...")
    print("Press Ctrl+C to stop. Progress saves safely every chapter.")
    
    try:
        while current_ayo_url:
            if test_run and chapters_processed_this_run >= 2:
                print("Test run complete (2 iterations).")
                break
                
            print(f"\\nProcessing {current_ayo_url.split('/')[-1]}...")
            
            # Extract standard slug (e.g. 'GEN.1')
            usfm_slug = current_ayo_url.split("/")[-1].replace(".AYORE", "")
            story_id = f"bible__{usfm_slug.lower().replace('.', '-')}"
            
            # Phase 1: Always ping Ayoré specifically to dynamically resolve `next_url` for the traversal loop
            ayo_data = extract_chapter_data(current_ayo_url, usfm_slug)
            if not ayo_data:
                print("Failed to fetch Ayoreo traversal data. Stopping sequence.")
                break
                
            next_ayo_url = ayo_data["next_url"]
            
            # Skip if we already completely scraped this chapter (graceful resume)
            if story_id in output_data and not test_run:
                print(f"  {story_id} fully assembled in DB! Skipping ES/EN redundancy fetches.")
                current_ayo_url = next_ayo_url
                continue
                
            # Phase 2: Predict and fetch ES and EN counterparts
            es_url = current_ayo_url.replace("/2825/", "/3291/").replace(".AYORE", ".VBL")
            en_url = current_ayo_url.replace("/2825/", "/1932/").replace(".AYORE", ".FBV")
            
            es_data = extract_chapter_data(es_url, usfm_slug)
            en_data = extract_chapter_data(en_url, usfm_slug)
            
            if not es_data or not en_data:
                print("  Failed to fetch ES or EN components. Skipping chapter recording to ensure integrity.")
                current_ayo_url = next_ayo_url
                continue
                
            body_es = "\\n\\n".join([d["text"] for d in es_data["decomposition"]])
            body_en = "\\n\\n".join([d["text"] for d in en_data["decomposition"]])
            body_ayo = "\\n\\n".join([d["text"] for d in ayo_data["decomposition"]])
            
            # Phase 3: Intrinsic Validation (Mismatch Monitoring)
            warnings = []
            counts = {
                "es": es_data["verse_count"],
                "en": en_data["verse_count"],
                "ayo": ayo_data["verse_count"]
            }
            if len(set(counts.values())) > 1:
                msg = f"Translation Verse Mismatch: {counts}"
                print(f"  [Warning] {msg}")
                warnings.append(msg)
                summary["mismatches"].append({
                    "story_id": story_id,
                    "counts": counts,
                    "timestamp": datetime.now().isoformat()
                })
            
            output_data[story_id] = {
                "story_id": story_id,
                "url_es": es_url,
                "url_en": en_url,
                "url_ayo": current_ayo_url,
                "type": "faith",
                "section": es_data["section"],
                "chapter_usfm": usfm_slug,
                "title_es": es_data["title"],
                "title_en": en_data["title"],
                "title_ayo": ayo_data["title"],
                "body_es": body_es,
                "body_en": body_en,
                "body_ayo": body_ayo,
                "body_decomposition": {
                    "es": es_data["decomposition"],
                    "en": en_data["decomposition"],
                    "ayo": ayo_data["decomposition"]
                },
                "warnings": warnings
            }
                
            if story_id not in summary["history"]:
                summary["history"].append(story_id)
                
            summary["total_chapters_scraped"] = len(output_data)
            summary["execution_date"] = datetime.now().isoformat()
            
            # Synchronous incremental writes preventing data loss
            with open(BIBLE_JSON, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
                
            chapters_processed_this_run += 1
            current_ayo_url = next_ayo_url
            time.sleep(1.5)
            
    except KeyboardInterrupt:
        print("\\nManual interrupt detected.")
        
    print(f"\\n✅ Scraping suspended. Total chapters safely written to DB: {len(output_data)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-run", action="store_true", help="Only scrape 2 iterations from the cursor")
    args = parser.parse_args()
    main(test_run=args.test_run)
