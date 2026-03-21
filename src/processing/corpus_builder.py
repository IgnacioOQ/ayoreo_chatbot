"""Assemble the final parallel corpus from all processed sources."""

import json
from pathlib import Path

from src.processing.aligner import align_sentences
from src.processing.cleaner import clean_text
from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)

AYOREOORG_PATH = PROJECT_ROOT / "data" / "raw" / "ayoreoorg" / "aligned_ayoreoorg.json"
AYOREOORG_FALLBACK = PROJECT_ROOT / "data" / "raw" / "ayoreoorg" / "ayoreoorg.json"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def _pairs_from_alignment(story_id: str, entry: dict) -> list[tuple[str, str]]:
    """Extract EN↔AYO pairs using alignment_map + body_decomposition."""
    deco = entry.get("body_decomposition", {})
    en_chunks  = deco.get("en",  [])
    ayo_chunks = deco.get("ayo", [])
    alignment  = json.loads(entry["alignment_map"])

    pairs = []
    for block in alignment:
        en_texts  = [clean_text(en_chunks[i]["text"])  for i in block.get("en",  []) if i < len(en_chunks)]
        ayo_texts = [clean_text(ayo_chunks[i]["text"]) for i in block.get("ayo", []) if i < len(ayo_chunks)]
        en_combined  = " ".join(t for t in en_texts  if t)
        ayo_combined = " ".join(t for t in ayo_texts if t)
        if en_combined and ayo_combined:
            pairs.append((en_combined, ayo_combined))
    return pairs


def build_corpus() -> list[dict]:
    """Build parallel corpus from all scraped and processed sources.

    Returns:
        List of parallel segments: {id, ayoreo, english, source, type}.
    """
    corpus = []

    # 1. Process narrative stories from ayoreoorg.json
    load_path = AYOREOORG_PATH if AYOREOORG_PATH.exists() else AYOREOORG_FALLBACK
    if load_path.exists():
        with open(load_path, encoding="utf-8") as f:
            dataset = json.load(f)

        for story_id, entry in dataset.items():
            en_text  = clean_text(entry.get("body_en",  ""))
            ayo_text = clean_text(entry.get("body_ayo", ""))
            section  = story_id.split("__")[0] if "__" in story_id else "unknown"

            if not en_text or not ayo_text:
                continue

            # Use alignment_map for clean semantic-unit pairs when available
            if entry.get("alignment_map"):
                try:
                    pairs = _pairs_from_alignment(story_id, entry)
                except Exception:
                    pairs = align_sentences(en_text, ayo_text)
            else:
                pairs = align_sentences(en_text, ayo_text)

            for i, (en_sent, ayo_sent) in enumerate(pairs):
                corpus.append({
                    "id":      f"{story_id}_s{i:03d}",
                    "ayoreo":  ayo_sent,
                    "english": en_sent,
                    "source":  section,
                    "type":    "narrative",
                })
    else:
        log.warning(f"No ayoreoorg dataset found at {load_path}")

    # 2. Add glossary entries
    glossary_path = PROCESSED_DIR / "glossaries.json"
    if glossary_path.exists():
        with open(glossary_path, encoding="utf-8") as f:
            glossaries = json.load(f)
        for entry in glossaries:
            corpus.append({
                "id":      f"gloss_{entry['ayoreo'].lower().replace(' ', '_')}",
                "ayoreo":  entry["ayoreo"],
                "english": entry.get("english", ""),
                "source":  "glossary",
                "type":    "lexical",
            })

    # 3. Add dictionary entries
    dict_path = PROCESSED_DIR / "dictionary.json"
    if dict_path.exists():
        with open(dict_path, encoding="utf-8") as f:
            dictionary = json.load(f)
        for entry in dictionary:
            corpus.append({
                "id":      f"dict_{entry['headword'].lower().replace(' ', '_')}",
                "ayoreo":  entry["headword"],
                "english": entry.get("definition_en", ""),
                "source":  "dictionary",
                "type":    "lexical",
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
