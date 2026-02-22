"""Run the full processing pipeline: clean, align, build corpus, split."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.processing.corpus_builder import build_corpus, save_corpus
from src.processing.glossary_extractor import extract_glossaries_from_pages, save_glossaries
from src.processing.splitter import split_corpus, save_splits
from src.utils.logger import get_logger

log = get_logger(__name__)


def main():
    log.info("Starting processing pipeline...")

    # 1. Extract and merge glossaries
    glossaries = extract_glossaries_from_pages()
    save_glossaries(glossaries)

    # 2. Build parallel corpus
    corpus = build_corpus()
    save_corpus(corpus)

    # 3. Split into train/val/test
    train, val, test = split_corpus(corpus)
    save_splits(train, val, test)

    log.info("Processing pipeline core complete.")
    
    # 4. Build Dictionary and POS dataset (Warning: Requires GOOGLE_API_KEY)
    log.info("Note: To build the Dictionary and POS dataset you must run `python scripts/build_dictionary.py` first (requires API key), followed by `python scripts/build_pos_dataset.py`.")
    log.info("Pipeline finished.")


if __name__ == "__main__":
    main()
