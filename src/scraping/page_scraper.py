"""Page scraper: extracts text content from individual ayore.org pages."""

import json
from datetime import datetime, timezone
from pathlib import Path

from src.scraping.utils import fetch_page
from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)

RAW_PAGES_DIR = PROJECT_ROOT / "data" / "raw" / "pages"


def extract_page_content(soup) -> dict:
    """Extract main body text and glossary from a parsed page.

    Returns:
        Dict with 'title', 'body', and 'glossary' keys.
    """
    # Extract title
    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Extract main content area (adjust selector based on site structure)
    content_div = soup.find("article") or soup.find("div", class_="entry-content")
    if content_div is None:
        content_div = soup.find("main") or soup.body

    body = content_div.get_text(separator="\n", strip=True) if content_div else ""

    # TODO: Extract glossary section separately once site structure is confirmed
    glossary = []

    return {"title": title, "body": body, "glossary": glossary}


def scrape_parallel_page(es_url: str, ayo_url: str, section: str) -> dict:
    """Scrape both Spanish and Ayoreo versions of a page.

    Returns:
        Dict with parallel content from both versions.
    """
    log.info(f"Scraping: {es_url}")

    es_soup = fetch_page(es_url)
    ayo_soup = fetch_page(ayo_url)

    if es_soup is None or ayo_soup is None:
        log.error(f"Failed to scrape pair: {es_url}")
        return {}

    es_content = extract_page_content(es_soup)
    ayo_content = extract_page_content(ayo_soup)

    return {
        "url_es": es_url,
        "url_ayo": ayo_url,
        "title_es": es_content["title"],
        "title_ayo": ayo_content["title"],
        "body_es": es_content["body"],
        "body_ayo": ayo_content["body"],
        "glossary": es_content["glossary"],
        "section": section,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def save_page(page_data: dict, filename: str) -> None:
    """Save scraped page data as JSON."""
    RAW_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_PAGES_DIR / f"{filename}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(page_data, f, ensure_ascii=False, indent=2)
    log.info(f"Saved: {path}")
