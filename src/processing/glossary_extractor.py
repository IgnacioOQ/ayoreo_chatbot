"""Extract and merge glossary entries from scraped pages."""

import json
from pathlib import Path

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)

RAW_PAGES_DIR = PROJECT_ROOT / "data" / "raw" / "pages"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def extract_glossaries_from_pages() -> list[dict]:
    """Load all scraped page JSONs and merge their glossary entries.

    Returns:
        Deduplicated list of glossary entries: {ayoreo, spanish, source}.
    """
    seen = set()
    glossaries = []

    for json_file in sorted(RAW_PAGES_DIR.glob("*.json")):
        with open(json_file, encoding="utf-8") as f:
            page = json.load(f)

        for entry in page.get("glossary", []):
            key = entry.get("ayoreo", "").lower()
            if key and key not in seen:
                seen.add(key)
                glossaries.append({
                    "ayoreo": entry["ayoreo"],
                    "spanish": entry.get("spanish", ""),
                    "source": json_file.stem,
                })

    log.info(f"Extracted {len(glossaries)} unique glossary entries")
    return glossaries


def save_glossaries(glossaries: list[dict]) -> None:
    """Save merged glossaries to processed directory."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = PROCESSED_DIR / "glossaries.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(glossaries, f, ensure_ascii=False, indent=2)
    log.info(f"Saved glossaries to {path}")
