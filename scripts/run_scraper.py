"""Run the full scraping pipeline: discover pages, scrape, and save."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scraping.crawler import discover_all
from src.scraping.page_scraper import scrape_parallel_page, save_page
from src.utils.logger import get_logger

log = get_logger(__name__)


def main():
    log.info("Starting scraping pipeline...")

    # 1. Discover all parallel page pairs
    pairs = discover_all()
    log.info(f"Discovered {len(pairs)} parallel page pairs")

    # 2. Scrape each pair
    for es_url, ayo_url in pairs:
        # Derive section and filename from URL
        parts = es_url.split("/es/")[-1].strip("/").split("/")
        section = parts[0] if parts else "unknown"
        filename = "_".join(parts) if parts else "page"

        page_data = scrape_parallel_page(es_url, ayo_url, section)
        if page_data:
            save_page(page_data, filename)

    log.info("Scraping pipeline complete.")


if __name__ == "__main__":
    main()
