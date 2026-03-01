"""Page scraper: extracts text content from individual ayore.org pages.

ayore.org is a WordPress site. Content pages typically have:
    - An <article> or <div class="entry-content"> with the main text
    - Bold section headers within the text
    - A glossary section at the bottom (Ayoreo terms with Spanish definitions)
    - Metadata: narrator name, location, date, transcriber/translator

Each story is scraped in all three languages (ES, EN, AYO) and stored
together under a shared story_id for aligned corpus construction.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from bs4 import Tag

from src.scraping.utils import fetch_page
from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)

RAW_PAGES_DIR = PROJECT_ROOT / "data" / "raw" / "pages"


def _find_content_div(soup) -> Tag | None:
    """Find the main content container in the page."""
    # WordPress common patterns
    for selector in [
        ("div", {"class": "entry-content"}),
        ("article", {}),
        ("div", {"class": "post-content"}),
        ("main", {}),
    ]:
        tag = soup.find(selector[0], selector[1])
        if tag:
            return tag
    return soup.body


def _html_to_markdown_basic(tag: Tag) -> str:
    """Convert a BeautifulSoup tag to text while preserving basic bold/italic formatting."""
    import copy
    copied = copy.copy(tag)
    # Convert bold
    for b in copied.find_all(["b", "strong"]):
        text = b.get_text(strip=True)
        if text:
            b.replace_with(f"**{text}**")
    # Convert italics
    for i in copied.find_all(["i", "em"]):
        text = i.get_text(strip=True)
        if text:
            i.replace_with(f"*{text}*")
    return copied.get_text(strip=True)


def _extract_metadata(text: str) -> dict:
    """Extract narrator, location, date, and transcriber from page text.

    Typical patterns found on ayore.org:
        "Narrator: Cajoide, Campo Loro, Paraguay, 1985"
        "Transcribed by: Maxine Morarie"
        "Translated to Spanish by: Julia Morarie"
    """
    metadata = {}

    # Look for narrator pattern (name at the start, or after "Narrator:")
    narrator_match = re.search(
        r"(?:Narr?ador|Narrator|Narrated by)[:\s]+(.+?)(?:\n|$)", text, re.IGNORECASE
    )
    if narrator_match:
        metadata["narrator"] = narrator_match.group(1).strip().rstrip(".")

    # Location and date
    location_match = re.search(
        r"(?:Campo Loro|Tobité|Zapocó|Santa Cruz|Poza Verde|Rincón del Tigre)"
        r"[,\s]+(?:Bolivia|Paraguay)[,\s]*(\d{4})?",
        text, re.IGNORECASE,
    )
    if location_match:
        metadata["location"] = location_match.group(0).strip().rstrip(",")
        if location_match.group(1):
            metadata["year"] = location_match.group(1)

    # Transcriber/translator
    for pattern in [
        r"(?:Transcri(?:bed|to) (?:by|por))[:\s]+(.+?)(?:\n|$)",
        r"(?:Translat(?:ed|ado) (?:to Spanish )?(?:by|por))[:\s]+(.+?)(?:\n|$)",
    ]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            role = "transcriber" if "transcri" in match.group(0).lower() else "translator"
            metadata[role] = match.group(1).strip().rstrip(".")

    return metadata


def _extract_glossary(content_div: Tag) -> list[dict]:
    """Extract glossary entries from the page content.

    Glossary items are typically at the bottom of the page, formatted as
    bold Ayoreo terms followed by definitions, or in a list/table.
    """
    glossary = []
    text = content_div.get_text(separator="\n")

    # Pattern 1: "Ayoreo term – Spanish definition" or "Ayoreo term - definition"
    # Often the term is bold and followed by a dash and definition
    for match in re.finditer(
        r"^[\s•*-]*([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü\-]+(?:\s[a-záéíóúñü\-]+)*)"
        r"\s*[–\-—:]\s*"
        r"(.+?)$",
        text, re.MULTILINE,
    ):
        term = match.group(1).strip()
        definition = match.group(2).strip().rstrip(".")
        # Filter out common false positives (section headers, metadata lines)
        if len(term) < 50 and len(definition) < 200 and len(term.split()) <= 5:
            glossary.append({"ayoreo": term, "spanish": definition})

    # Pattern 2: Look for bold tags followed by non-bold text
    for bold in content_div.find_all(["strong", "b"]):
        term = bold.get_text(strip=True)
        next_text = bold.next_sibling
        if next_text and isinstance(next_text, str):
            # Check if it looks like "term – definition"
            definition = next_text.strip().lstrip("–-—: ")
            if definition and 3 < len(term) < 40 and len(definition) < 200:
                # Avoid section headers (which are usually longer)
                if not term[0].isdigit() and term not in ("Nota", "Fuente", "Source"):
                    glossary.append({"ayoreo": term, "spanish": definition})

    # Deduplicate
    seen = set()
    unique = []
    for entry in glossary:
        key = entry["ayoreo"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(entry)

    return unique


def extract_language_urls(soup) -> dict[str, str]:
    """Extract URLs for all language versions from the WPML language switcher.

    ayore.org uses WPML, which inserts a widget listing links to every other
    language version of the current page. This gives exact URL mappings that
    are far more reliable than positional pairing from index pages.

    The switcher shows only the OTHER languages — not the current page's lang.
    So if called on an ES page, the result will contain 'en' and 'ayo' keys.

    Returns:
        Dict mapping language code → URL, e.g. {'en': '...', 'ayo': '...'}.
        Empty dict if no WPML switcher is found.
    """
    urls = {}
    switcher = soup.find("div", class_="wpml-ls")
    if not switcher:
        return urls
    for li in switcher.find_all("li", class_="wpml-ls-item"):
        span = li.find("span", class_="wpml-ls-native")
        a = li.find("a", class_="wpml-ls-link")
        if span and a:
            lang = span.get("lang")   # e.g. "en", "ayo", "es"
            href = a.get("href")
            if lang and href:
                urls[lang] = href
    return urls


def extract_page_content(soup) -> dict:
    """Extract structured content from a parsed ayore.org page.

    Returns:
        Dict with title, body, glossary, metadata, and raw_html.
    """
    # Title
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Main content area
    content_div = _find_content_div(soup)
    if content_div is None:
        return {"title": title, "body": "", "glossary": [], "metadata": {}}

    # Extract body text (paragraphs only, skip nav/footer)
    paragraphs = []
    for p in content_div.find_all(["p", "blockquote"]):
        text = _html_to_markdown_basic(p)
        if text and len(text) > 10:  # Skip very short fragments
            paragraphs.append(text)

    body = "\n\n".join(paragraphs)

    # If no <p> tags found, fall back to full text extraction
    if not body:
        body = _html_to_markdown_basic(content_div)

    # Glossary
    glossary = _extract_glossary(content_div)

    # Metadata
    full_text = content_div.get_text(separator="\n")
    metadata = _extract_metadata(full_text)

    return {
        "title": title,
        "body": body,
        "glossary": glossary,
        "metadata": metadata,
    }


def scrape_page(page_info: dict) -> dict:
    """Scrape all three language versions (ES, EN, AYO) of a story.

    Args:
        page_info: Dict from crawler with url_es, url_en, url_ayo, story_id, etc.

    Returns:
        Dict with all scraped content keyed by language, sharing a story_id.
    """
    result = {
        "story_id":  page_info.get("story_id"),
        "url_es":    page_info.get("url_es"),
        "url_en":    page_info.get("url_en"),
        "url_ayo":   page_info.get("url_ayo"),
        "section":   page_info.get("section", "unknown"),
        "type":      page_info.get("type", "narrative"),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }

    # --- Spanish (primary) ---
    # Scrape ES first; use its WPML switcher to confirm/fill EN and AYO URLs.
    es_soup = None
    if page_info.get("url_es"):
        log.info(f"Scraping ES: {page_info['url_es']}")
        es_soup = fetch_page(page_info["url_es"])
        if es_soup:
            es_content = extract_page_content(es_soup)
            result["title_es"] = es_content["title"]
            result["body_es"]  = es_content["body"]
            result["glossary"] = es_content["glossary"]
            result["metadata"] = es_content["metadata"]

            # Resolve sibling language URLs from the WPML switcher.
            # These override/supplement whatever the crawler found by position.
            wpml_urls = extract_language_urls(es_soup)
            if wpml_urls:
                log.debug(f"WPML URLs from ES page: {wpml_urls}")
            for lang_code, wpml_url in wpml_urls.items():
                key = f"url_{lang_code}"
                if not result.get(key):
                    log.info(f"WPML filled missing {key}: {wpml_url}")
                    result[key] = wpml_url
                elif result[key] != wpml_url:
                    log.warning(
                        f"WPML URL mismatch for {key}: "
                        f"crawler={result[key]} wpml={wpml_url} — using WPML"
                    )
                    result[key] = wpml_url
        else:
            log.warning(f"Failed to fetch ES: {page_info['url_es']}")
            result["title_es"] = ""
            result["body_es"]  = ""

    # --- English ---
    if result.get("url_en"):
        log.info(f"Scraping EN: {result['url_en']}")
        en_soup = fetch_page(result["url_en"])
        if en_soup:
            en_content = extract_page_content(en_soup)
            result["title_en"] = en_content["title"]
            result["body_en"]  = en_content["body"]
            if len(result.get("body_en", "")) < 50:
                log.warning(
                    f"EN page may be empty/boilerplate: {result['url_en']} "
                    f"(body length: {len(result.get('body_en', ''))})"
                )
        else:
            log.warning(f"Failed to fetch EN: {result['url_en']}")
            result["title_en"] = ""
            result["body_en"]  = ""

    # --- Ayoreo ---
    if result.get("url_ayo"):
        log.info(f"Scraping AYO: {result['url_ayo']}")
        ayo_soup = fetch_page(result["url_ayo"])
        if ayo_soup:
            ayo_content = extract_page_content(ayo_soup)
            result["title_ayo"] = ayo_content["title"]
            result["body_ayo"]  = ayo_content["body"]
            if len(result.get("body_ayo", "")) < 50:
                log.warning(
                    f"AYO page may be empty/boilerplate: {result['url_ayo']} "
                    f"(body length: {len(result.get('body_ayo', ''))})"
                )
        else:
            log.warning(f"Failed to fetch AYO: {result['url_ayo']}")
            result["title_ayo"] = ""
            result["body_ayo"]  = ""

    return result


def save_page(page_data: dict, filename: str) -> Path:
    """Save scraped page data as JSON.

    Returns:
        Path to the saved file.
    """
    RAW_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    # Clean filename: replace problematic characters
    clean_name = re.sub(r"[^\w\-]", "_", filename)
    path = RAW_PAGES_DIR / f"{clean_name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(page_data, f, ensure_ascii=False, indent=2)
    log.info(f"Saved: {path}")
    return path
