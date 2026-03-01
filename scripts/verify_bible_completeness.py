import json
from pathlib import Path

# Standard 66-book Protestant Biblical Canon and respective chapter lengths
BIBLE_BOOKS = {
    "GEN": 50, "EXO": 40, "LEV": 27, "NUM": 36, "DEU": 34, "JOS": 24, "JDG": 21, "RUT": 4,
    "1SA": 31, "2SA": 24, "1KI": 22, "2KI": 25, "1CH": 29, "2CH": 36, "EZR": 10, "NEH": 13,
    "EST": 10, "JOB": 42, "PSA": 150, "PRO": 31, "ECC": 12, "SNG": 8, "ISA": 66, "JER": 52,
    "LAM": 5, "EZK": 48, "DAN": 12, "HOS": 14, "JOL": 3, "AMO": 9, "OBA": 1, "JON": 4,
    "MIC": 7, "NAM": 3, "HAB": 3, "ZEP": 3, "HAG": 2, "ZEC": 14, "MAL": 4,
    "MAT": 28, "MRK": 16, "LUK": 24, "JHN": 21, "ACT": 28, "ROM": 16, "1CO": 16, "2CO": 13,
    "GAL": 6, "EPH": 6, "PHP": 4, "COL": 4, "1TH": 5, "2TH": 3, "1TI": 6, "2TI": 4,
    "TIT": 3, "PHM": 1, "HEB": 13, "JAS": 5, "1PE": 5, "2PE": 3, "1JN": 5, "2JN": 1,
    "3JN": 1, "JUD": 1, "REV": 22
}
# Total = 1189 Canonical Chapters

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BIBLE_JSON = PROJECT_ROOT / "data" / "raw" / "bible" / "bible.json"
SUMMARY_JSON = PROJECT_ROOT / "data" / "raw" / "bible" / "bible_scraping_summary.json"

def main():
    if not BIBLE_JSON.exists():
        print("Error: bible.json target not found!")
        return

    with open(BIBLE_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    scraped_chapters = set()
    for entry in data.values():
        slug = entry.get("chapter_usfm") # e.g. GEN.1
        if slug:
            scraped_chapters.add(slug)
            
    print("="*50)
    print("BIBLE.JSON EXOGENOUS COVERAGE REPORT")
    print("="*50)
    
    total_canonical = sum(BIBLE_BOOKS.values())
    print(f"Total Canonical Chapters Expected: {total_canonical}")
    print(f"Total Chapters Physically Scraped:    {len(scraped_chapters)}")
    print(f"Total Structural Translation Mismatches Encountered: ", end="")
    
    if SUMMARY_JSON.exists():
        with open(SUMMARY_JSON, "r", encoding="utf-8") as f:
            summary = json.load(f)
            misms = len(summary.get("mismatches", []))
            print(f"{misms} {'(Check summary JSON)' if misms > 0 else ''}")
    else:
        print("Unknown (Summary missing)")
    
    missing = []
    # Test strict sequential traversal against exogenous truth map
    for book, num_chapters in BIBLE_BOOKS.items():
        for ch in range(1, num_chapters + 1):
            usfm = f"{book}.{ch}"
            if usfm not in scraped_chapters:
                missing.append(usfm)
                
    if not missing:
        print("\\n🎉 PERFECT COMPLETENESS! All 1189 Canonical Chapters are safely extracted.")
    else:
        perc = (len(scraped_chapters) / total_canonical) * 100
        print(f"\\n⚠️ Missing {len(missing)} chapters (Completion: {perc:.2f}%).")
        print("This may indicate Ayoré translations are incomplete for the following segments:")
        for m in missing[:20]:
            print(f" - {m}")
        if len(missing) > 20:
            print(f"   ...and {len(missing) - 20} more chapters.")

if __name__ == "__main__":
    main()
