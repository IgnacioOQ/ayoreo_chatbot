"""Main translation engine: orchestrates RAG, neural (LoRA), dictionary, and LLM."""

from src.inference.dictionary_lookup import DictionaryLookup
from src.inference.rag_retriever import RAGRetriever
from src.inference.translator import build_translation_prompt, translate_with_gemini
from src.pos_tagging.rule_engine import RuleBasedTagger, tokenize
from src.utils.logger import get_logger

log = get_logger(__name__)

# Translation backends
BACKEND_RAG = "rag"       # RAG + few-shot prompting via Gemini API
BACKEND_NEURAL = "neural"  # Local LoRA adapter over Mistral/LLaMA
BACKEND_HYBRID = "hybrid"  # Neural translation + RAG context for LLM refinement


class TranslationEngine:
    """Orchestrates the full translation pipeline.

    Supports multiple backends:
    - 'rag': Retrieve similar examples -> few-shot prompt -> Gemini API
    - 'neural': Local LoRA adapter over open-source LLM (Mistral/LLaMA)
    - 'hybrid': Neural does first pass, RAG + LLM refines the output
    """

    def __init__(self, backend: str = BACKEND_RAG):
        """
        Args:
            backend: Translation backend ('rag', 'neural', or 'hybrid').
        """
        self.backend = backend
        self._retriever = None
        self._dictionary = None
        self._tagger = None
        self._lora_translator = None

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

    @property
    def lora_translator(self):
        if self._lora_translator is None:
            from src.inference.lora_translator import LoRATranslator
            self._lora_translator = LoRATranslator()
        return self._lora_translator

    def translate(self, text: str, direction: str = "ayo_to_en") -> str:
        """Translate text between Ayoreo and English.

        Args:
            text: Input text.
            direction: 'ayo_to_en' or 'en_to_ayo'.

        Returns:
            Translated text.
        """
        if self.backend == BACKEND_NEURAL:
            return self._translate_neural(text, direction)
        elif self.backend == BACKEND_HYBRID:
            return self._translate_hybrid(text, direction)
        else:
            return self._translate_rag(text, direction)

    def _translate_rag(self, text: str, direction: str) -> str:
        """RAG backend: retrieve examples -> few-shot prompt -> Gemini."""
        examples = self.retriever.retrieve(text, k=8)

        tokens = tokenize(text)
        dict_entries = []
        for token in tokens:
            dict_entries.extend(self.dictionary.lookup(token))

        prompt = build_translation_prompt(text, examples, dict_entries, direction)
        return translate_with_gemini(prompt)

    def _translate_neural(self, text: str, direction: str) -> str:
        """Neural backend: LoRA adapter over Mistral/LLaMA."""
        return self.lora_translator.translate(text, direction=direction)

    def _translate_hybrid(self, text: str, direction: str) -> str:
        """Hybrid backend: neural first pass, then RAG + LLM refinement.

        1. LoRA adapter generates initial translation
        2. RAG retrieves similar examples
        3. Gemini refines the translation using both
        """
        neural_output = self.lora_translator.translate(text, direction=direction)
        examples = self.retriever.retrieve(text, k=5)

        tokens = tokenize(text)
        dict_entries = []
        for token in tokens:
            dict_entries.extend(self.dictionary.lookup(token))

        if direction == "ayo_to_en":
            src_lang, tgt_lang = "Ayoreo", "English"
        else:
            src_lang, tgt_lang = "English", "Ayoreo"

        refinement_prompt = (
            f"A translation model produced this translation from {src_lang} to {tgt_lang}:\n\n"
            f"Original ({src_lang}): {text}\n"
            f"Automatic translation ({tgt_lang}): {neural_output}\n\n"
            f"Review and improve the translation using these reference examples:\n"
        )
        for ex in examples:
            src_key = "ayoreo" if direction == "ayo_to_en" else "english"
            tgt_key = "english" if direction == "ayo_to_en" else "ayoreo"
            refinement_prompt += (
                f"  {src_lang}: {ex[src_key]}\n  {tgt_lang}: {ex[tgt_key]}\n\n"
            )

        if dict_entries:
            refinement_prompt += "Vocabulary:\n"
            for entry in dict_entries[:10]:
                hw = entry.get("headword", entry.get("ayoreo", ""))
                defn = entry.get("definition_en", entry.get("english", ""))
                refinement_prompt += f"  {hw} = {defn}\n"

        refinement_prompt += (
            f"\nReturn only the improved translation in {tgt_lang}, without explanations:"
        )

        return translate_with_gemini(refinement_prompt)

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

    @property
    def neural_available(self) -> bool:
        """Check if a trained LoRA adapter is available."""
        try:
            return self.lora_translator.is_available
        except Exception:
            return False
