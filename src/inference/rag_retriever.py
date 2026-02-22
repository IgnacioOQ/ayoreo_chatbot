"""RAG retriever: finds similar parallel examples for few-shot translation."""

import json
from pathlib import Path

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)


class RAGRetriever:
    """Retrieves similar translation examples from the parallel corpus.

    Uses sentence-transformers for embedding and chromadb for vector storage.
    """

    def __init__(self, collection_name: str = "ayoreo_corpus"):
        self.collection_name = collection_name
        self._collection = None
        self._model = None

    def _ensure_loaded(self) -> None:
        """Lazy-load the embedding model and vector store."""
        if self._collection is not None:
            return

        import chromadb
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )

        client = chromadb.Client()
        self._collection = client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Index corpus if collection is empty
        if self._collection.count() == 0:
            self._index_corpus()

    def _index_corpus(self) -> None:
        """Index the parallel corpus into the vector store."""
        corpus_path = PROJECT_ROOT / "data" / "processed" / "parallel_corpus.jsonl"
        if not corpus_path.exists():
            log.warning(f"Corpus not found at {corpus_path} — skipping indexing")
            return

        entries = []
        with open(corpus_path, encoding="utf-8") as f:
            for line in f:
                entries.append(json.loads(line))

        if not entries:
            return

        # Embed both Spanish and Ayoreo text for bidirectional retrieval
        texts = [f"{e['spanish']} {e['ayoreo']}" for e in entries]
        embeddings = self._model.encode(texts, show_progress_bar=True).tolist()

        self._collection.add(
            ids=[e["id"] for e in entries],
            embeddings=embeddings,
            documents=texts,
            metadatas=[
                {"ayoreo": e["ayoreo"], "spanish": e["spanish"], "source": e["source"]}
                for e in entries
            ],
        )
        log.info(f"Indexed {len(entries)} entries into vector store")

    def retrieve(self, query: str, k: int = 8) -> list[dict]:
        """Retrieve the k most similar parallel examples.

        Args:
            query: Input text (in either language).
            k: Number of examples to retrieve.

        Returns:
            List of dicts with 'ayoreo', 'spanish', 'source' keys.
        """
        self._ensure_loaded()

        embedding = self._model.encode([query]).tolist()
        results = self._collection.query(
            query_embeddings=embedding,
            n_results=k,
        )

        examples = []
        if results["metadatas"]:
            for meta in results["metadatas"][0]:
                examples.append({
                    "ayoreo": meta["ayoreo"],
                    "spanish": meta["spanish"],
                    "source": meta["source"],
                })

        return examples
