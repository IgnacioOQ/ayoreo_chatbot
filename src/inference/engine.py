"""Main translation engine: orchestrates RAG retrieval, dictionary, and LLM."""

from src.inference.dictionary_lookup import DictionaryLookup
from src.inference.rag_retriever import RAGRetriever
from src.inference.translator import build_translation_prompt, translate_with_gemini
from src.pos_tagging.rule_engine import RuleBasedTagger, tokenize
from src.utils.logger import get_logger

log = get_logger(__name__)


class TranslationEngine:
    """Orchestrates the full translation pipeline.

    1. Retrieve similar examples from corpus (RAG)
    2. Look up words in dictionary
    3. Build few-shot prompt
    4. Call Gemini for translation
    """

    def __init__(self):
        self._retriever = None
        self._dictionary = None
        self._tagger = None

    @property
    def retriever(self) -> RAGRetriever:
        if self._retriever is None:
            self._retriever = RAGRetriever()
        return self._retriever

    @property
    def dictionary(self) -> DictionaryLookup:
        if self._dictionary is None:
            self._dictionary = DictionaryLookup()
        return self._dictionary

    @property
    def tagger(self) -> RuleBasedTagger:
        if self._tagger is None:
            self._tagger = RuleBasedTagger()
        return self._tagger

    def translate(self, text: str, direction: str = "ayo_to_es") -> str:
        """Translate text between Ayoreo and Spanish.

        Args:
            text: Input text.
            direction: 'ayo_to_es' or 'es_to_ayo'.

        Returns:
            Translated text.
        """
        # 1. Retrieve similar examples
        examples = self.retriever.retrieve(text, k=8)

        # 2. Dictionary lookup for individual words
        tokens = tokenize(text)
        dict_entries = []
        for token in tokens:
            results = self.dictionary.lookup(token)
            dict_entries.extend(results)

        # 3. Build prompt
        prompt = build_translation_prompt(text, examples, dict_entries, direction)

        # 4. Call LLM
        return translate_with_gemini(prompt)

    def lookup_word(self, word: str) -> list[dict]:
        """Look up a word in the dictionary."""
        return self.dictionary.lookup(word)

    def search_dictionary(self, query: str) -> list[dict]:
        """Search the dictionary for partial matches."""
        return self.dictionary.search(query)

    def pos_tag(self, text: str) -> list[tuple[str, str]]:
        """POS-tag Ayoreo text."""
        tokens = tokenize(text)
        return self.tagger.tag(tokens)
