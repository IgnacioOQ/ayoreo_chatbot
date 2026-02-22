"""Site crawler: discovers all content URLs on ayore.org."""

from src.scraping.utils import fetch_page, normalize_url, url_exists
from src.utils.config import load_config
from src.utils.logger import get_logger

log = get_logger(__name__)

BASE_URL = "https://ayore.org"


def discover_section_pages(section_path: str) -> list[str]:
    """Fetch a section index page and return all sub-page URLs.

    Args:
        section_path: Relative path like "cultura/ensenanzas"

    Returns:
        List of absolute URLs for sub-pages under this section.
    """
    index_url = f"{BASE_URL}/es/{section_path}/"
    log.info(f"Discovering pages in: {index_url}")

    soup = fetch_page(index_url)
    if soup is None:
        return []

    urls = []
    for a_tag in soup.find_all("a", href=True):
        href = normalize_url(a_tag["href"], index_url)
        # Keep only links within this section, not the index itself
        if f"/es/{section_path}/" in href and href != index_url:
            urls.append(href)

    urls = sorted(set(urls))
    log.info(f"Found {len(urls)} pages in {section_path}")
    return urls


def build_parallel_pairs(es_urls: list[str]) -> list[tuple[str, str]]:
    """For each Spanish URL, construct and verify the Ayoreo counterpart.

    Returns:
        List of (spanish_url, ayoreo_url) tuples where both exist.
    """
    pairs = []
    for es_url in es_urls:
        ayo_url = es_url.replace("/es/", "/ayo/")
        if url_exists(ayo_url):
            pairs.append((es_url, ayo_url))
            log.info(f"Parallel pair found: {es_url}")
        else:
            log.warning(f"No Ayoreo version: {es_url}")
    return pairs


def discover_all() -> list[tuple[str, str]]:
    """Discover all parallel page pairs across all configured sections.

    Returns:
        List of (spanish_url, ayoreo_url) tuples.
    """
    config = load_config("scraping")
    all_pairs = []

    for section in config.get("sections", []):
        path = section["path"]
        es_urls = discover_section_pages(path)
        pairs = build_parallel_pairs(es_urls)
        all_pairs.extend(pairs)

    log.info(f"Total parallel pairs discovered: {len(all_pairs)}")
    return all_pairs
