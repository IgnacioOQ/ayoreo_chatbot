"""Tests for the scraping module."""

from src.scraping.utils import get_language_from_url, normalize_url
from src.scraping.crawler import pair_pages_trilingual
from src.scraping.page_scraper import _extract_metadata


def test_get_language_from_url_spanish():
    assert get_language_from_url("https://ayore.org/es/cultura/") == "es"


def test_get_language_from_url_ayoreo():
    assert get_language_from_url("https://ayore.org/ayo/cultura/") == "ayo"


def test_get_language_from_url_none():
    assert get_language_from_url("https://ayore.org/fotos/") is None


def test_normalize_url_relative():
    result = normalize_url("/es/cultura/ensenanzas/", "https://ayore.org")
    assert result == "https://ayore.org/es/cultura/ensenanzas/"


def test_normalize_url_absolute():
    result = normalize_url(
        "https://ayore.org/es/cultura/", "https://ayore.org"
    )
    assert result == "https://ayore.org/es/cultura/"


def test_pair_pages_trilingual_equal_count():
    es = [
        {"url": "https://ayore.org/es/a/", "title": "A-es", "slug": "a"},
        {"url": "https://ayore.org/es/b/", "title": "B-es", "slug": "b"},
    ]
    en = [
        {"url": "https://ayore.org/a/", "title": "A-en", "slug": "a"},
        {"url": "https://ayore.org/b/", "title": "B-en", "slug": "b"},
    ]
    ayo = [
        {"url": "https://ayore.org/ayo/a/", "title": "A-ayo", "slug": "a"},
        {"url": "https://ayore.org/ayo/b/", "title": "B-ayo", "slug": "b"},
    ]
    pairs = pair_pages_trilingual(es, en, ayo)
    assert len(pairs) == 2
    assert pairs[0]["url_es"] == "https://ayore.org/es/a/"
    assert pairs[0]["url_en"] == "https://ayore.org/a/"
    assert pairs[0]["url_ayo"] == "https://ayore.org/ayo/a/"
    assert pairs[1]["slug_en"] == "b"


def test_pair_pages_trilingual_unequal_count():
    es = []
    en = [
        {"url": "https://ayore.org/a/", "title": "A-en", "slug": "a"},
        {"url": "https://ayore.org/b/", "title": "B-en", "slug": "b"},
        {"url": "https://ayore.org/c/", "title": "C-en", "slug": "c"},
    ]
    ayo = [
        {"url": "https://ayore.org/ayo/a/", "title": "A-ayo", "slug": "a"},
    ]
    pairs = pair_pages_trilingual(es, en, ayo)
    assert len(pairs) == 3
    assert pairs[0]["url_en"] is not None and pairs[0]["url_ayo"] is not None
    assert pairs[1]["url_en"] is not None and pairs[1]["url_ayo"] is None
    assert pairs[2]["url_en"] is not None and pairs[2]["url_ayo"] is None
    # ES is omitted from this run — all url_es should be None
    assert all(p["url_es"] is None for p in pairs)


def test_extract_metadata_narrator():
    text = "Narrador: Cajoide, Campo Loro, Paraguay, 1985\nTranscribed by: Maxine Morarie"
    meta = _extract_metadata(text)
    assert "narrator" in meta
    assert "Campo Loro" in meta.get("location", "")
    assert meta.get("year") == "1985"


def test_extract_metadata_empty():
    meta = _extract_metadata("Just some regular text without metadata.")
    assert meta == {}
