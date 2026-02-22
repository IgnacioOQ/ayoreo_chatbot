"""Structured extraction from dictionary PDF text."""

from src.utils.logger import get_logger

log = get_logger(__name__)


def parse_dictionary_entries(raw_text: str) -> list[dict]:
    """Parse dictionary PDF text into structured entries.

    Expected format varies — this needs to be adapted after inspecting
    the actual dictionary PDF from ayore.org.

    Returns:
        List of dicts with keys: headword, pos, definition_es, examples.
    """
    entries = []
    # TODO: Implement parsing once dictionary PDF structure is analyzed
    # The dictionary is ~30 pages; parsing logic depends on its layout
    log.warning("Dictionary parsing not yet implemented — inspect PDF first")
    return entries
