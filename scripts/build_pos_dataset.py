"""Build a Part-of-Speech tagging dataset from parallel sentences and dictionary."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def load_dictionary() -> dict[str, str]:
    """Load the cleaned Ayoreo-Spanish dictionary.
    
    Returns:
        Dict mapping Ayoreo word -> POS tag.
    """
    dict_path = PROCESSED_DIR / "dictionary_ayoreo_espanol.json"
    if not dict_path.exists():
        log.warning(f"Dictionary not found at {dict_path}. Run build_dictionary.py first.")
        return {}
        
    with open(dict_path, encoding="utf-8") as f:
        entries = json.load(f)
        
    pos_map = {}
    for entry in entries:
        word = entry["ayoreo"].lower().strip()
        # Some entries might be short phrases; we only map single words for POS tagging
        if " " not in word:
            pos_map[word] = entry["pos_tag"]
            
    log.info(f"Loaded POS mappings for {len(pos_map)} unique Ayoreo words.")
    return pos_map


def build_pos_dataset():
    """Create a dataset of Ayoreo sentences with POS tags where known."""
    corpus_path = PROCESSED_DIR / "parallel_corpus.jsonl"
    if not corpus_path.exists():
        log.error(f"Parallel corpus not found at {corpus_path}")
        return

    pos_map = load_dictionary()
    dataset = []

    with open(corpus_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            
            entry = json.loads(line)
            ayoreo_text = entry.get("ayoreo", "")
            
            if not ayoreo_text:
                continue
                
            # Tokenize: simple whitespace and punctuation split
            # We keep punctuation as separate tokens
            tokens = re.findall(r"[\wáéíóúñü]+|[^\w\s]", ayoreo_text.lower())
            
            pos_tags = []
            for token in tokens:
                # If it's punctuation
                if not re.match(r"[\wáéíóúñü]+", token):
                    pos_tags.append("PUNCT")
                # If it's a known word in our dictionary
                elif token in pos_map:
                    pos_tags.append(pos_map[token])
                # Unknown word
                else:
                    pos_tags.append("UNK")
            
            # Form final tokens matching original case where possible
            original_tokens = re.findall(r"[\wÁÉÍÓÚÑÜáéíóúñü]+|[^\w\s]", ayoreo_text)
            
            if len(original_tokens) == len(pos_tags):
                dataset.append({
                    "id": entry.get("id", ""),
                    "tokens": original_tokens,
                    "pos_tags": pos_tags,
                    "spanish_translation": entry.get("spanish", "")
                })

    # Save to disk
    out_path = PROCESSED_DIR / "pos_sentences.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    log.info(f"Generated POS dataset with {len(dataset)} sentences in {out_path}.")
    
    # Calculate coverage stats
    total_tokens = sum(len(d["tokens"]) for d in dataset)
    unk_tokens = sum(t == "UNK" for d in dataset for t in d["pos_tags"])
    known_tokens = total_tokens - unk_tokens
    
    if total_tokens > 0:
        coverage = (known_tokens / total_tokens) * 100
        log.info(f"POS tag coverage: {coverage:.1f}% ({known_tokens}/{total_tokens} tokens mapped)")


def main():
    build_pos_dataset()


if __name__ == "__main__":
    main()
