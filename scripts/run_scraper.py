"""Run the full scraping pipeline: discover pages, scrape, save, and download PDFs.

Usage:
    # Full scrape (all sections + PDFs)
    python scripts/run_scraper.py

    # Scrape only a specific section (for testing)
    python scripts/run_scraper.py --section ensenanzas

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
from src.scraping.page_scraper import scrape_page, save_page
from src.scraping.pdf_scraper import download_all_pdfs
from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)


def scrape_pages(section_filter: str | None = None, dry_run: bool = False):
    """Discover and scrape all content pages."""
    # 1. Discover all pages
    all_pages = discover_all()

    # Filter by section if requested
    if section_filter:
        all_pages = [p for p in all_pages if p.get("section") == section_filter]
        log.info(f"Filtered to section '{section_filter}': {len(all_pages)} pages")

    if dry_run:
        log.info("Dry run — listing discovered pages:")
        for i, page in enumerate(all_pages):
            es = page.get("url_es", "—")
            ayo = page.get("url_ayo", "—")
            log.info(f"  [{i+1}] ES: {es}")
            log.info(f"       AYO: {ayo}")
        return all_pages

    # 2. Scrape each page
    scraped = 0
    failed = 0
    for i, page_info in enumerate(all_pages):
        log.info(f"--- Page {i+1}/{len(all_pages)} ---")

        page_data = scrape_page(page_info)

        # Skip if no content was extracted
        has_es = bool(page_data.get("body_es", "").strip())
        has_ayo = bool(page_data.get("body_ayo", "").strip())

        if not has_es and not has_ayo:
            log.warning(f"No content extracted, skipping")
            failed += 1
            continue

        # Generate filename from section + slug
        section = page_info.get("section", "unknown")
        slug = page_info.get("slug_es") or page_info.get("slug_ayo") or f"page_{i}"
        filename = f"{section}__{slug}"

        save_page(page_data, filename)
        scraped += 1

    log.info(f"Scraping complete: {scraped} saved, {failed} failed out of {len(all_pages)}")

    # 3. Save summary
    summary = {
        "total_discovered": len(all_pages),
        "scraped": scraped,
        "failed": failed,
        "pages": [
            {
                "section": p.get("section"),
                "url_es": p.get("url_es"),
                "url_ayo": p.get("url_ayo"),
                "has_es": p.get("url_es") is not None,
                "has_ayo": p.get("url_ayo") is not None,
            }
            for p in all_pages
        ],
    }
    summary_path = PROJECT_ROOT / "data" / "raw" / "scraping_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    log.info(f"Summary saved to {summary_path}")

    return all_pages


def main():
    parser = argparse.ArgumentParser(description="Scrape ayore.org")
    parser.add_argument(
        "--section", type=str, default=None,
        help="Scrape only this section (e.g. 'ensenanzas', 'creencias')",
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
