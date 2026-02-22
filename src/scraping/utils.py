"""Scraping utilities: HTTP helpers, rate limiting, URL normalization."""

import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.utils.logger import get_logger

log = get_logger(__name__)

DEFAULT_DELAY = 1.5  # seconds between requests
DEFAULT_TIMEOUT = 30


def fetch_page(url: str, delay: float = DEFAULT_DELAY) -> BeautifulSoup | None:
    """Fetch a URL and return parsed BeautifulSoup, respecting rate limits."""
    time.sleep(delay)
    try:
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.encoding = "utf-8"  # Force UTF-8 for Ayoreo characters
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")
    except requests.RequestException as e:
        log.error(f"Failed to fetch {url}: {e}")
        return None


def normalize_url(href: str, base_url: str) -> str:
    """Normalize a relative or absolute URL against a base URL."""
    return urljoin(base_url, href)


def url_exists(url: str) -> bool:
    """Check if a URL returns HTTP 200."""
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return response.status_code == 200
    except requests.RequestException:
        return False


def get_language_from_url(url: str) -> str | None:
    """Extract language code from URL path (es, ayo, en)."""
    path = urlparse(url).path
    parts = path.strip("/").split("/")
    if parts and parts[0] in ("es", "ayo", "en"):
        return parts[0]
    return None
