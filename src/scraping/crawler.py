"""Site crawler: discovers all content URLs on ayore.org.

The site uses different URL slug conventions per language:
    ES: /es/cultura/ensenanzas/...
    AYO: /ayo/culture/teachings/...
So we crawl each language independently and pair pages by position/title.
"""

from src.scraping.utils import fetch_page, normalize_url
from src.utils.config import load_config
from src.utils.logger import get_logger

log = get_logger(__name__)

BASE_URL = "https://ayore.org"


def discover_section_pages(lang: str, section_path: str) -> list[dict]:
    """Fetch a section index page and return all sub-page URLs with titles.

    Args:
        lang: Language prefix ('es' or 'ayo').
        section_path: Relative path like "cultura/ensenanzas" or "culture/teachings".

    Returns:
        List of dicts with 'url', 'title', and 'slug' keys, ordered as found.
    """
    index_url = f"{BASE_URL}/{lang}/{section_path}/"
    log.info(f"Discovering pages in: {index_url}")

    soup = fetch_page(index_url)
    if soup is None:
        return []

    pages = []
    seen_urls = set()

    for a_tag in soup.find_all("a", href=True):
        href = normalize_url(a_tag["href"], index_url)

        # Keep only links within this section (not the index page itself)
        if f"/{lang}/{section_path}/" not in href:
            continue
        if href.rstrip("/") == index_url.rstrip("/"):
            continue
        if href in seen_urls:
            continue

        seen_urls.add(href)

        # Extract the page-specific slug (last path segment)
        slug = href.rstrip("/").split("/")[-1]
        title = a_tag.get_text(strip=True)

        pages.append({"url": href, "title": title, "slug": slug})

    log.info(f"Found {len(pages)} pages in /{lang}/{section_path}/")
    return pages


def pair_pages_by_position(
    es_pages: list[dict],
    ayo_pages: list[dict],
) -> list[dict]:
    """Pair Spanish and Ayoreo pages.

    Strategy: pair by list position (both index pages list sub-pages in the
    same order). If counts differ, unpaired pages get stored as single-language.

    Returns:
        List of dicts with 'url_es', 'url_ayo', 'title_es', 'title_ayo'.
        Missing pairs have None for the missing language's fields.
    """
    pairs = []
    max_len = max(len(es_pages), len(ayo_pages))

    for i in range(max_len):
        es = es_pages[i] if i < len(es_pages) else None
        ayo = ayo_pages[i] if i < len(ayo_pages) else None

        pairs.append({
            "url_es": es["url"] if es else None,
            "url_ayo": ayo["url"] if ayo else None,
            "title_es": es["title"] if es else None,
            "title_ayo": ayo["title"] if ayo else None,
            "slug_es": es["slug"] if es else None,
            "slug_ayo": ayo["slug"] if ayo else None,
        })

    paired = sum(1 for p in pairs if p["url_es"] and p["url_ayo"])
    es_only = sum(1 for p in pairs if p["url_es"] and not p["url_ayo"])
    ayo_only = sum(1 for p in pairs if not p["url_es"] and p["url_ayo"])
    log.info(f"Paired: {paired}, ES-only: {es_only}, AYO-only: {ayo_only}")

    return pairs


def discover_all() -> list[dict]:
    """Discover all pages across all configured sections in both languages.

    Returns:
        List of dicts, each with section info and paired URLs:
        {section, type, url_es, url_ayo, title_es, title_ayo, ...}
    """
    config = load_config("scraping")
    all_pages = []

    for section in config.get("sections", []):
        path_es = section["path_es"]
        path_ayo = section["path_ayo"]
        section_type = section.get("type", "narrative")

        log.info(f"--- Section: {path_es} / {path_ayo} ---")

        es_pages = discover_section_pages("es", path_es)
        ayo_pages = discover_section_pages("ayo", path_ayo)

        pairs = pair_pages_by_position(es_pages, ayo_pages)

        for pair in pairs:
            pair["section"] = path_es.split("/")[-1]  # e.g. "ensenanzas"
            pair["type"] = section_type
            all_pages.append(pair)

    total = len(all_pages)
    with_both = sum(1 for p in all_pages if p["url_es"] and p["url_ayo"])
    log.info(f"Total pages discovered: {total} ({with_both} with both languages)")
    return all_pages
