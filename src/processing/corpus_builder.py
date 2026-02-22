"""Assemble the final parallel corpus from all processed sources."""

import json
from pathlib import Path

from src.processing.aligner import align_sentences
from src.processing.cleaner import clean_text
from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)

RAW_PAGES_DIR = PROJECT_ROOT / "data" / "raw" / "pages"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def build_corpus() -> list[dict]:
    """Build parallel corpus from all scraped and processed sources.

    Returns:
        List of parallel segments: {id, ayoreo, spanish, source, type}.
    """
    corpus = []

    # 1. Process narrative pages
    for json_file in sorted(RAW_PAGES_DIR.glob("*.json")):
        with open(json_file, encoding="utf-8") as f:
            page = json.load(f)

        es_text = clean_text(page.get("body_es", ""))
        ayo_text = clean_text(page.get("body_ayo", ""))
        section = page.get("section", "unknown")

        if not es_text or not ayo_text:
            continue

        pairs = align_sentences(es_text, ayo_text)
        for i, (es_sent, ayo_sent) in enumerate(pairs):
            corpus.append({
                "id": f"{json_file.stem}_s{i:03d}",
                "ayoreo": ayo_sent,
                "spanish": es_sent,
                "source": section,
                "type": "narrative",
            })

    # 2. Add glossary entries
    glossary_path = PROCESSED_DIR / "glossaries.json"
    if glossary_path.exists():
        with open(glossary_path, encoding="utf-8") as f:
            glossaries = json.load(f)
        for entry in glossaries:
            corpus.append({
                "id": f"gloss_{entry['ayoreo'].lower().replace(' ', '_')}",
                "ayoreo": entry["ayoreo"],
                "spanish": entry["spanish"],
                "source": "glossary",
                "type": "lexical",
            })

    # 3. Add dictionary entries
    dict_path = PROCESSED_DIR / "dictionary.json"
    if dict_path.exists():
        with open(dict_path, encoding="utf-8") as f:
            dictionary = json.load(f)
        for entry in dictionary:
            corpus.append({
                "id": f"dict_{entry['headword'].lower().replace(' ', '_')}",
                "ayoreo": entry["headword"],
                "spanish": entry.get("definition_es", ""),
                "source": "dictionary",
                "type": "lexical",
            })

    log.info(f"Built corpus with {len(corpus)} segments")
    return corpus


def save_corpus(corpus: list[dict]) -> None:
    """Save corpus as JSONL file."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = PROCESSED_DIR / "parallel_corpus.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for entry in corpus:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    log.info(f"Saved corpus to {path}")
