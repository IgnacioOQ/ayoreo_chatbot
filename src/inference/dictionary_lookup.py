"""Fast dictionary search for Ayoreo words."""

import json
from pathlib import Path

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)


class DictionaryLookup:
    """In-memory dictionary for fast Ayoreo-English word lookup."""

    def __init__(self):
        self.entries: dict[str, list[dict]] = {}  # lowercase key -> list of entries
        self._load()

    def _load(self) -> None:
        """Load dictionary and glossary data."""
        processed_dir = PROJECT_ROOT / "data" / "processed"

        # Load dictionary
        dict_path = processed_dir / "dictionary.json"
        if dict_path.exists():
            with open(dict_path, encoding="utf-8") as f:
                for entry in json.load(f):
                    key = entry.get("headword", "").lower()
                    self.entries.setdefault(key, []).append(entry)

        # Load glossaries
        gloss_path = processed_dir / "glossaries.json"
        if gloss_path.exists():
            with open(gloss_path, encoding="utf-8") as f:
                for entry in json.load(f):
                    key = entry.get("ayoreo", "").lower()
                    self.entries.setdefault(key, []).append({
                        "headword": entry["ayoreo"],
                        "definition_en": entry.get("english", entry.get("spanish", "")),
                        "source": "glossary",
                    })

        log.info(f"Dictionary loaded: {len(self.entries)} unique entries")

    def lookup(self, word: str) -> list[dict]:
        """Look up a word (case-insensitive)."""
        return self.entries.get(word.lower(), [])

    def search(self, query: str) -> list[dict]:
        """Search for entries containing the query string."""
        query_lower = query.lower()
        results = []
        for key, entries in self.entries.items():
            if query_lower in key:
                results.extend(entries)
        return results[:20]  # Limit results
