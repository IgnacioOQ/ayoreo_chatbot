"""Run the full scraping pipeline: discover pages, scrape, save, and download PDFs.

All scraped stories are stored in a single file:
    data/raw/stories.json  — dict keyed by story_id, incrementally merged across runs.

Usage:
    # Full scrape (all sections + PDFs)
    python scripts/run_scraper.py

    # Scrape only a specific section (for testing)
    python scripts/run_scraper.py --section relatos-personales

    # Only download PDFs
    python scripts/run_scraper.py --pdfs-only

    # Dry run: discover pages but don't scrape
    python scripts/run_scraper.py --dry-run
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scraping.crawler import discover_all
from src.scraping.page_scraper import scrape_page
from src.scraping.pdf_scraper import download_all_pdfs
from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)

STORIES_PATH = PROJECT_ROOT / "data" / "raw" / "ayoreoorg" / "ayoreoorg.json"


def scrape_pages(section_filter: str | None = None, dry_run: bool = False):
    """Discover and scrape all content pages, saving to a single stories.json."""
    # 1. Discover all pages
    all_pages = discover_all()

    # Filter by section if requested
    if section_filter:
        all_pages = [p for p in all_pages if p.get("section") == section_filter]
        log.info(f"Filtered to section '{section_filter}': {len(all_pages)} pages")

    if dry_run:
        log.info("Dry run — listing discovered pages:")
        for i, page in enumerate(all_pages):
            log.info(f"  [{i+1}] {page.get('story_id')}  ES: {page.get('url_es', '—')}")
        return all_pages

    # 2. Load existing stories for incremental merge (keyed by story_id)
    STORIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    if STORIES_PATH.exists():
        with open(STORIES_PATH, encoding="utf-8") as f:
            stories = json.load(f)
        log.info(f"Loaded {len(stories)} existing stories from {STORIES_PATH}")
    else:
        stories = {}

    # 3. Scrape each page and merge into the dict
    scraped = 0
    failed = 0
    for i, page_info in enumerate(all_pages):
        log.info(f"--- Page {i+1}/{len(all_pages)} ---")

        page_data = scrape_page(page_info)

        # Skip if no content was extracted in any language
        has_es  = bool(page_data.get("body_es",  "").strip())
        has_en  = bool(page_data.get("body_en",  "").strip())
        has_ayo = bool(page_data.get("body_ayo", "").strip())

        if not has_es and not has_en and not has_ayo:
            log.warning("No content extracted, skipping")
            failed += 1
            continue

        story_id = page_data.get("story_id") or page_info.get("story_id")
        stories[story_id] = page_data
        scraped += 1

    # 4. Save the merged dict
    with open(STORIES_PATH, "w", encoding="utf-8") as f:
        json.dump(stories, f, ensure_ascii=False, indent=2)
    log.info(f"Saved {len(stories)} total stories to {STORIES_PATH}")
    log.info(f"Scraping complete: {scraped} new/updated, {failed} failed out of {len(all_pages)}")

    return all_pages


def main():
    parser = argparse.ArgumentParser(description="Scrape ayore.org")
    parser.add_argument(
        "--section", type=str, default=None,
        help="Scrape only this section (e.g. 'ensenanzas', 'relatos-personales')",
    )
    parser.add_argument(
        "--pdfs-only", action="store_true",
        help="Only download PDFs, skip page scraping",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Discover pages but don't scrape them",
    )
    args = parser.parse_args()

    if not args.pdfs_only:
        log.info("=== Starting page scraping ===")
        scrape_pages(section_filter=args.section, dry_run=args.dry_run)

    if not args.dry_run:
        log.info("=== Downloading PDFs ===")
        paths = download_all_pdfs()
        for p in paths:
            log.info(f"  PDF: {p}")

    log.info("=== Pipeline complete ===")


if __name__ == "__main__":
    main()
