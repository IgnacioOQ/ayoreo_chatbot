"""Tests for the scraping module."""

from src.scraping.utils import get_language_from_url, normalize_url


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
