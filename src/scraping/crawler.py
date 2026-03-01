"""Site crawler: discovers all content URLs on ayore.org.

The site uses different URL slug conventions per language:
    ES:  https://ayore.org/es/cultura/ensenanzas/...
    EN:  https://ayore.org/culture/teachings/...       (no lang prefix)
    AYO: https://ayore.org/ayo/culture/teachings/...

We crawl each language independently and pair pages by position, since all
three index pages list sub-pages in the same order.
"""

from src.scraping.utils import fetch_page, get_language_from_url, normalize_url
from src.utils.config import load_config
from src.utils.logger import get_logger

log = get_logger(__name__)

BASE_URL = "https://ayore.org"


def discover_section_pages(lang: str | None, section_path: str) -> list[dict]:
    """Fetch a section index page and return all sub-page URLs with titles.

    Args:
        lang: Language prefix ('es', 'ayo') or None for English (no prefix).
        section_path: Relative path like "cultura/ensenanzas" or "culture/teachings".

    Returns:
        List of dicts with 'url', 'title', and 'slug' keys, ordered as found.
    """
    if lang:
        index_url = f"{BASE_URL}/{lang}/{section_path}/"
    else:
        index_url = f"{BASE_URL}/{section_path}/"

    log.info(f"Discovering pages in: {index_url}")

    soup = fetch_page(index_url)
    if soup is None:
        return []

    pages = []
    seen_urls = set()

    for a_tag in soup.find_all("a", href=True):
        href = normalize_url(a_tag["href"], index_url)

        # Drop anchor fragments (e.g. /section/#masthead) — not real pages
        if "#" in href:
            continue

        # Keep only links that fall within this section path
        if f"/{section_path}/" not in href:
            continue
        if href.rstrip("/") == index_url.rstrip("/"):
            continue
        if href in seen_urls:
            continue

        # Language guard: skip URLs belonging to a different language than requested.
        # For English (lang=None), skip any URL that has a lang prefix (es, ayo, en).
        url_lang = get_language_from_url(href)
        if lang is None and url_lang is not None:
            continue
        if lang is not None and url_lang != lang:
            continue

        seen_urls.add(href)

        slug = href.rstrip("/").split("/")[-1]
        title = a_tag.get_text(strip=True)

        pages.append({"url": href, "title": title, "slug": slug})

    log.info(f"Found {len(pages)} pages in {index_url}")
    return pages


def pair_pages_trilingual(
    es_pages: list[dict],
    en_pages: list[dict],
    ayo_pages: list[dict],
) -> list[dict]:
    """Pair Spanish, English, and Ayoreo pages by list position.

    All three index pages list sub-pages in the same order, so positional
    pairing is the correct strategy. If counts differ, unpaired pages are
    stored with None for the missing language fields.

    Returns:
        List of dicts with url/title/slug for all three languages.
    """
    max_len = max(len(es_pages), len(en_pages), len(ayo_pages), 1)
    pairs = []

    for i in range(max_len):
        es  = es_pages[i]  if i < len(es_pages)  else None
        en  = en_pages[i]  if i < len(en_pages)  else None
        ayo = ayo_pages[i] if i < len(ayo_pages) else None

        pairs.append({
            "url_es":    es["url"]    if es  else None,
            "url_en":    en["url"]    if en  else None,
            "url_ayo":   ayo["url"]   if ayo else None,
            "title_es":  es["title"]  if es  else None,
            "title_en":  en["title"]  if en  else None,
            "title_ayo": ayo["title"] if ayo else None,
            "slug_es":   es["slug"]   if es  else None,
            "slug_en":   en["slug"]   if en  else None,
            "slug_ayo":  ayo["slug"]  if ayo else None,
        })

    paired_all  = sum(1 for p in pairs if p["url_es"] and p["url_en"] and p["url_ayo"])
    paired_some = sum(1 for p in pairs if not (p["url_es"] and p["url_en"] and p["url_ayo"]))
    log.info(f"Trilingual pairs: {paired_all} complete, {paired_some} partial")

    return pairs


def discover_all() -> list[dict]:
    """Discover all pages across all configured sections in all three languages.

    Returns:
        List of dicts, each with section info and paired URLs:
        {story_id, section, type, url_es, url_en, url_ayo, title_es, title_en, title_ayo, ...}
    """
    config = load_config("scraping")
    all_pages = []

    for section in config.get("sections", []):
        path_es  = section["path_es"]
        path_ayo = section["path_ayo"]
        path_en  = section.get("path_en", path_ayo)  # default to ayo path if omitted
        section_type = section.get("type", "narrative")
        section_name = path_es.split("/")[-1]  # e.g. "relatos-personales"

        log.info(f"--- Section: {section_name} ---")

        es_pages  = discover_section_pages("es",  path_es)
        en_pages  = discover_section_pages(None,  path_en)
        ayo_pages = discover_section_pages("ayo", path_ayo)

        pairs = pair_pages_trilingual(es_pages, en_pages, ayo_pages)

        for pair in pairs:
            # Canonical story_id: section + ES slug (stable, human-readable reference)
            slug = pair["slug_es"] or pair["slug_en"] or pair["slug_ayo"] or str(len(all_pages))
            pair["story_id"] = f"{section_name}__{slug}"
            pair["section"]  = section_name
            pair["type"]     = section_type
            all_pages.append(pair)

    total    = len(all_pages)
    with_all = sum(1 for p in all_pages if p["url_es"] and p["url_en"] and p["url_ayo"])
    log.info(f"Total pages discovered: {total} ({with_all} with all three languages)")
    return all_pages
