"""Rule-based POS tagger for Ayoreo using dictionary + morphological rules."""

import re

from src.utils.logger import get_logger

log = get_logger(__name__)


class RuleBasedTagger:
    """POS tagger that combines dictionary lookup with suffix-based rules.

    The dictionary provides known word-to-POS mappings.
    Suffix rules handle unknown words based on morphological patterns
    extracted from the Ayoreo grammar.
    """

    def __init__(
        self,
        dictionary: dict[str, str] | None = None,
        suffix_rules: list[tuple[str, str]] | None = None,
    ):
        """
        Args:
            dictionary: Mapping of lowercase word -> POS tag.
            suffix_rules: List of (suffix_pattern, POS_tag) ordered by priority.
        """
        self.dictionary = dictionary or {}
        self.suffix_rules = suffix_rules or []

    def tag_token(self, token: str) -> str:
        """Assign POS tag to a single token."""
        # 1. Dictionary lookup
        if token.lower() in self.dictionary:
            return self.dictionary[token.lower()]

        # 2. Suffix rules
        for suffix, pos in self.suffix_rules:
            if token.lower().endswith(suffix):
                return pos

        # 3. Fallback
        return "X"

    def tag(self, tokens: list[str]) -> list[tuple[str, str]]:
        """Tag a list of tokens.

        Returns:
            List of (token, POS_tag) tuples.
        """
        return [(token, self.tag_token(token)) for token in tokens]


def tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer for Ayoreo text."""
    tokens = re.findall(r"\w+|[^\w\s]", text, re.UNICODE)
    return tokens
