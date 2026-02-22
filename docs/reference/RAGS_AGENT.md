# RAG Optimization Agent Skill
- status: active
- type: agent_skill
- id: rags-agent
- context_dependencies: {"conventions": "MD_CONVENTIONS.md"}
- last_checked: 2025-01-28
<!-- content -->
This document defines an **agent skill** for analyzing, configuring, and improving Retrieval-Augmented Generation (RAG) systems across different projects. The agent equipped with this skill can diagnose RAG performance issues and implement cost-effective improvements.

## Core Competencies
- status: active
- type: guideline
- id: rags-agent.competencies
<!-- content -->
An agent with this skill can:

1. **Audit** existing RAG implementations for common failure modes
2. **Recommend** retrieval strategies matched to data characteristics
3. **Implement** chain-of-thought and multi-step retrieval patterns
4. **Design** MCP-based structured data access layers
5. **Optimize** the cost/quality tradeoff for production systems

## RAG Fundamentals
- status: active
- type: guideline
- id: rags-agent.fundamentals
<!-- content -->
Before optimizing, ensure the foundational RAG architecture is sound. This section covers the essential components and common pitfalls.

### What RAG Actually Does
- status: active
- type: context
- id: rags-agent.fundamentals.definition
<!-- content -->
RAG combines three operations:

1. **Retrieval**: Given a query, find relevant documents from a corpus using semantic similarity (embeddings) or keyword matching (BM25)
2. **Augmentation**: Inject the retrieved documents into the LLM's context window as grounding information
3. **Generation**: The LLM produces a response conditioned on both the query and the retrieved context

The quality of a RAG system is bounded by retrieval quality. If relevant documents are not retrieved, the LLM cannot use them regardless of its capability.

### Essential Components
- status: active
- type: guideline
- id: rags-agent.fundamentals.components
<!-- content -->
A well-structured RAG system requires:

| Component | Purpose | Common Choices |
|:----------|:--------|:---------------|
| Document Store | Raw text storage | JSON files, PostgreSQL, S3 |
| Vector Database | Embedding storage and similarity search | ChromaDB, Pinecone, Weaviate, pgvector |
| Embedding Model | Convert text to vectors | `all-MiniLM-L6-v2`, OpenAI `text-embedding-3-small`, Cohere |
| Chunking Strategy | Split documents into retrievable units | Fixed-size, semantic, recursive |
| Retrieval Logic | Query the vector DB and rank results | Top-k, MMR, hybrid |
| LLM | Generate responses from context | GPT-4, Claude, Gemini, Llama |

### Chunking Strategy Guidelines
- status: active
- type: guideline
- id: rags-agent.fundamentals.chunking
<!-- content -->
Chunk size directly impacts retrieval quality:

- **Too small** (< 100 tokens): Loses context, retrieves fragments
- **Too large** (> 1000 tokens): Dilutes relevance signal, wastes context window
- **Sweet spot**: 200-500 tokens with 10-20% overlap

Recommended approaches by content type:

| Content Type | Strategy | Chunk Size | Overlap |
|:-------------|:---------|:-----------|:--------|
| Documentation | Recursive by headers | 300-500 tokens | 50 tokens |
| Code | By function/class | Natural boundaries | None |
| Conversations | By turn or topic | 200-400 tokens | 1-2 turns |
| Academic papers | By section | 400-600 tokens | 100 tokens |

### Embedding Model Selection
- status: active
- type: guideline
- id: rags-agent.fundamentals.embeddings
<!-- content -->
Choose embedding models based on your constraints:

| Model | Dimensions | Speed | Quality | Cost |
|:------|:-----------|:------|:--------|:-----|
| `all-MiniLM-L6-v2` | 384 | Fast | Good | Free |
| `all-mpnet-base-v2` | 768 | Medium | Better | Free |
| `text-embedding-3-small` | 1536 | Fast | Very Good | $0.02/1M tokens |
| `text-embedding-3-large` | 3072 | Medium | Excellent | $0.13/1M tokens |

For most projects, `all-MiniLM-L6-v2` or `text-embedding-3-small` provides the best cost/quality ratio.

### Common Failure Modes
- status: active
- type: guideline
- id: rags-agent.fundamentals.failures
<!-- content -->
Diagnose RAG issues by checking these failure modes in order:

1. **Retrieval Miss**: Relevant documents exist but are not retrieved
   - *Symptom*: LLM says "I don't have information about X" when X is in the corpus
   - *Cause*: Query/document embedding mismatch, poor chunking, insufficient top-k

2. **Context Dilution**: Too many irrelevant chunks crowd out relevant ones
   - *Symptom*: Vague or generic answers despite good data
   - *Cause*: top-k too high, no reranking, poor chunk boundaries

3. **Lost in the Middle**: Relevant info retrieved but ignored by LLM
   - *Symptom*: Correct chunks in context but answer ignores them
   - *Cause*: Critical info buried in middle of long context
   - *Fix*: Place most relevant chunks first and last

4. **Hallucination Despite Context**: LLM invents information
   - *Symptom*: Confident wrong answers
   - *Cause*: Weak grounding prompt, context not authoritative enough

### Implementation Optimizations
- status: active
- type: guideline
- id: rags-agent.fundamentals.optimizations
<!-- content -->
Small implementation details can have significant performance impact at scale.

#### List vs Set for Duplicate Checking
- status: active
- type: context
- id: rags-agent.fundamentals.optimizations.set-check
<!-- content -->
When checking for duplicates during document ingestion or retrieval deduplication, prefer **set-based lookups** over **list-based lookups**.

**Problem**: List membership checks (`item in list`) perform a linear scan O(N), leading to O(N²) complexity when checking each item against a growing list.

**Solution**: Use a set for lookups (`item in set`) which provides O(1) average-case complexity, reducing overall complexity to O(N).

```python
# ❌ Bad: O(N²) - list-based duplicate check
ids = []
for doc in documents:
    doc_id = generate_id(doc)
    while doc_id in ids:  # Linear scan each time!
        doc_id = regenerate_id(doc_id)
    ids.append(doc_id)

# ✅ Good: O(N) - set-based duplicate check  
ids = []
used_ids = set()  # Separate set for O(1) lookups
for doc in documents:
    doc_id = generate_id(doc)
    while doc_id in used_ids:  # O(1) lookup
        doc_id = regenerate_id(doc_id)
    ids.append(doc_id)
    used_ids.add(doc_id)
```

**Impact**: This optimization becomes critical for large ingestion batches. For 10,000 documents, the list-based approach performs ~50 million comparisons vs ~10,000 for the set-based approach.

> **Note**: This optimization is implemented in `src/core/vector_store.py` for document ID deduplication during ingestion.

## Retrieval Improvements
- status: active
- type: plan
- id: rags-agent.retrieval
<!-- content -->
This section covers techniques to improve what documents are retrieved for a given query.

### Semantic Similarity Fundamentals
- status: active
- type: guideline
- id: rags-agent.retrieval.semantic-similarity
- priority: high
<!-- content -->
Understanding how semantic similarity works is essential for optimizing RAG retrieval. The query-retrieval function in RAG systems is **primarily** done by semantic similarity, though modern systems use hybrid approaches.

#### Core Mechanism
- status: active
- type: context
- id: rags-agent.retrieval.semantic-similarity.mechanism
<!-- content -->
The semantic similarity process involves three steps:

1. **Document Encoding**: Documents are split into chunks and converted to dense vector embeddings using a model. These embeddings capture semantic meaning in high-dimensional space.

2. **Query Encoding**: User queries are encoded into the same vector space using the same embedding model.

3. **Similarity Search**: The system calculates distance/similarity between the query vector and all document vectors, returning the top-k most similar chunks.

#### Similarity Metrics
- status: active
- type: guideline
- id: rags-agent.retrieval.semantic-similarity.metrics
<!-- content -->
Different metrics measure vector similarity in different ways:

```python
import numpy as np
from typing import List

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Most common metric in RAG systems.
    Measures the cosine of the angle between vectors.
    Range: -1 to 1 (higher is more similar)
    
    Args:
        vec1: First embedding vector
        vec2: Second embedding vector
    
    Returns:
        Similarity score between -1 and 1
    """
    dot_product = np.dot(vec1, vec2)
    norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
    return dot_product / norm_product

def euclidean_distance(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Measures straight-line distance between vectors.
    Lower values = more similar
    
    Args:
        vec1: First embedding vector
        vec2: Second embedding vector
    
    Returns:
        Distance (lower is more similar)
    """
    return np.linalg.norm(vec1 - vec2)

def dot_product(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Simple multiplication and sum.
    Higher values = more similar
    Often used with normalized vectors
    
    Args:
        vec1: First embedding vector
        vec2: Second embedding vector
    
    Returns:
        Dot product score
    """
    return np.dot(vec1, vec2)
```

**Metric Selection Guidelines**:

| Metric | Use Case | Pros | Cons |
|:-------|:---------|:-----|:-----|
| Cosine Similarity | Default choice for most RAG systems | Scale-invariant, intuitive | Ignores magnitude |
| Euclidean Distance | When magnitude matters | Considers vector length | Sensitive to scale |
| Dot Product | Normalized embeddings | Fast computation | Requires normalization |

#### Why Semantic Similarity Works
- status: active
- type: context
- id: rags-agent.retrieval.semantic-similarity.rationale
<!-- content -->
Semantic embeddings capture meaning beyond exact keyword matches. For example:

- **Query**: "How do I reset my password?"
- **Matching doc**: "Instructions for recovering account access"
- **Why it works**: Embedding models learn that these concepts are related through training on vast text corpora, even with no word overlap

This allows RAG systems to retrieve relevant documents even when query terms don't appear verbatim in the documents.

### Hybrid Search
- status: active
- type: task
- id: rags-agent.retrieval.hybrid
- priority: high
- estimate: 2h
<!-- content -->
Combine semantic search with traditional keyword search (BM25) for better retrieval accuracy. This addresses the limitations of pure semantic similarity.

#### When to Use Hybrid Search
- status: active
- type: guideline
- id: rags-agent.retrieval.hybrid.use-cases
<!-- content -->
Hybrid search excels when:

- Documents contain specific entities, numbers, or product codes that embeddings may not capture well
- Queries include technical terminology or acronyms
- Domain-specific jargon is important
- You need to balance semantic understanding with exact term matching

#### Implementation
- status: active
- type: task
- id: rags-agent.retrieval.hybrid.implementation
- estimate: 1h
<!-- content -->
```python
from rank_bm25 import BM25Okapi
import numpy as np
from typing import List

class HybridRetriever:
    """
    Combines semantic search with traditional keyword search (BM25)
    for better retrieval accuracy.
    
    The alpha parameter controls the balance between semantic and keyword
    matching, allowing tuning for different document types.
    """
    
    def __init__(self, documents: List[str], embeddings: np.ndarray, alpha: float = 0.5):
        """
        Initialize hybrid retriever with documents and embeddings.
        
        Args:
            documents: List of text chunks
            embeddings: Corresponding semantic embeddings
            alpha: Weight for semantic vs keyword (0=pure keyword, 1=pure semantic)
        """
        self.documents = documents
        self.embeddings = embeddings
        self.alpha = alpha
        
        # Tokenize documents for BM25 keyword search
        tokenized_docs = [doc.lower().split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized_docs)
    
    def retrieve(self, query: str, query_embedding: np.ndarray, top_k: int = 5) -> List[str]:
        """
        Retrieve documents using hybrid scoring.
        
        Combines semantic similarity scores with BM25 keyword scores
        to get the best of both approaches.
        
        Args:
            query: Query string
            query_embedding: Query embedding vector
            top_k: Number of results to return
        
        Returns:
            List of top-k most relevant documents
        """
        # Semantic scores (cosine similarity)
        semantic_scores = np.array([
            cosine_similarity(query_embedding, doc_emb) 
            for doc_emb in self.embeddings
        ])
        
        # Keyword scores (BM25)
        tokenized_query = query.lower().split()
        keyword_scores = np.array(self.bm25.get_scores(tokenized_query))
        
        # Normalize scores to 0-1 range for fair combination
        semantic_scores = (semantic_scores - semantic_scores.min()) / (
            semantic_scores.max() - semantic_scores.min() + 1e-10
        )
        keyword_scores = (keyword_scores - keyword_scores.min()) / (
            keyword_scores.max() - keyword_scores.min() + 1e-10
        )
        
        # Combine scores using alpha weighting
        final_scores = self.alpha * semantic_scores + (1 - self.alpha) * keyword_scores
        
        # Get top-k indices
        top_indices = np.argsort(final_scores)[-top_k:][::-1]
        
        return [self.documents[i] for i in top_indices]
```

**Alpha Tuning Guidelines**:

| Document Type | Recommended Alpha | Rationale |
|:--------------|:------------------|:----------|
| Technical docs with code | 0.3-0.5 | Exact terms matter |
| General documentation | 0.5-0.7 | Balance both approaches |
| Conversational text | 0.7-0.9 | Semantic meaning dominates |
| Product catalogs | 0.2-0.4 | Exact IDs/names critical |

**Cost Impact**: Negligible (BM25 is local computation)

### Reranking
- status: active
- type: task
- id: rags-agent.retrieval.reranking
- priority: high
- estimate: 1h
<!-- content -->
Use a two-stage retrieval process: fast semantic search followed by accurate reranking. This improves precision without sacrificing recall.

#### When to Use Reranking
- status: active
- type: guideline
- id: rags-agent.retrieval.reranking.use-cases
<!-- content -->
Reranking is effective when:

- Initial retrieval returns too many marginally relevant results
- Precision is more critical than recall
- You can afford slightly higher latency for better quality
- Context window size is limited and you need the best chunks

#### Implementation with Cross-Encoders
- status: active
- type: task
- id: rags-agent.retrieval.reranking.implementation
- estimate: 45m
<!-- content -->
```python
from sentence_transformers import CrossEncoder
import numpy as np
from typing import List

class RerankedRetriever:
    """
    Two-stage retrieval: fast semantic search + accurate reranking.
    
    Stage 1: Bi-encoder retrieves ~20-50 candidates quickly
    Stage 2: Cross-encoder reranks candidates for accuracy
    
    Cross-encoders are more accurate but slower, so we use them
    only on pre-filtered candidates.
    """
    
    def __init__(self, reranker_model: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        """
        Initialize reranker with a cross-encoder model.
        
        Args:
            reranker_model: HuggingFace cross-encoder model name
        """
        self.reranker = CrossEncoder(reranker_model)
    
    def retrieve_and_rerank(
        self, 
        query: str, 
        candidate_docs: List[str], 
        top_k: int = 5
    ) -> List[str]:
        """
        Rerank candidate documents using cross-encoder.
        
        The cross-encoder jointly processes query and document,
        producing more accurate relevance scores than bi-encoders.
        
        Args:
            query: Query string
            candidate_docs: Pre-filtered candidate documents (from semantic search)
            top_k: Number of final results to return
        
        Returns:
            Top-k reranked documents
        """
        # Create query-document pairs for cross-encoder
        pairs = [[query, doc] for doc in candidate_docs]
        
        # Get reranking scores (cross-encoder processes pairs jointly)
        scores = self.reranker.predict(pairs)
        
        # Sort by score and return top-k
        ranked_indices = np.argsort(scores)[-top_k:][::-1]
        return [candidate_docs[i] for i in ranked_indices]


class FullRetrievalPipeline:
    """
    Complete retrieval pipeline combining semantic search and reranking.
    
    This is the recommended production approach for high-quality retrieval.
    """
    
    def __init__(self, vector_store, reranker_model: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        """
        Initialize pipeline with vector store and reranker.
        
        Args:
            vector_store: Vector database instance
            reranker_model: Cross-encoder model name
        """
        self.vector_store = vector_store
        self.reranker = RerankedRetriever(reranker_model)
    
    def retrieve(self, query: str, initial_k: int = 20, final_k: int = 5) -> List[str]:
        """
        Two-stage retrieval with reranking.
        
        Stage 1: Retrieve initial_k candidates using fast semantic search
        Stage 2: Rerank to final_k using accurate cross-encoder
        
        Args:
            query: Query string
            initial_k: Number of candidates to retrieve (typically 3-5x final_k)
            final_k: Number of final results
        
        Returns:
            Top final_k reranked documents
        """
        # Stage 1: Fast semantic retrieval
        results = self.vector_store.query(query_texts=[query], n_results=initial_k)
        candidates = results['documents'][0]
        
        # Stage 2: Accurate reranking
        return self.reranker.retrieve_and_rerank(query, candidates, top_k=final_k)
```

**Model Selection for Reranking**:

| Model | Speed | Quality | Use Case |
|:------|:------|:--------|:---------|
| `ms-marco-MiniLM-L-6-v2` | Fast | Good | General purpose |
| `ms-marco-MiniLM-L-12-v2` | Medium | Better | Higher quality needed |
| `ms-marco-electra-base` | Slower | Best | Maximum quality |

**Cost Impact**: None (local model inference)
**Latency Impact**: +50-200ms depending on model and candidate count

### Metadata Filtering
- status: active
- type: task
- id: rags-agent.retrieval.metadata-filtering
- priority: medium
- estimate: 1h
<!-- content -->
Combine semantic search with metadata filtering to narrow results based on document properties like source, date, category, or access permissions.

#### When to Use Metadata Filtering
- status: active
- type: guideline
- id: rags-agent.retrieval.metadata-filtering.use-cases
<!-- content -->
Metadata filtering is essential when:

- Documents have distinct categories or sources (e.g., "research papers" vs "blog posts")
- Temporal relevance matters (e.g., "only documents from 2024")
- Access control is required (e.g., "only documents user has permissions for")
- Domain-specific attributes exist (e.g., "only Python code examples")

#### Implementation
- status: active
- type: task
- id: rags-agent.retrieval.metadata-filtering.implementation
- estimate: 45m
<!-- content -->
```python
from typing import Dict, Any, List
import numpy as np

class MetadataFilteredRetriever:
    """
    Combines semantic search with metadata filtering.
    
    Applies filters first to reduce search space, then performs
    semantic similarity within the filtered set.
    """
    
    def __init__(self, documents: List[str], embeddings: np.ndarray, metadata: List[Dict[str, Any]]):
        """
        Initialize retriever with documents, embeddings, and metadata.
        
        Args:
            documents: Text chunks
            embeddings: Semantic embeddings
            metadata: Associated metadata dicts (e.g., {'source': 'research', 'year': 2023})
        """
        self.documents = documents
        self.embeddings = embeddings
        self.metadata = metadata
    
    def retrieve_with_filters(
        self, 
        query_embedding: np.ndarray, 
        filters: Dict[str, Any] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve semantically similar documents that match metadata filters.
        
        Filtering happens before similarity computation for efficiency.
        
        Args:
            query_embedding: Query embedding vector
            filters: Metadata conditions (e.g., {'source': 'research_papers', 'year': 2023})
            top_k: Number of results to return
        
        Returns:
            List of documents with metadata
        
        Example:
            >>> retriever.retrieve_with_filters(
            ...     query_emb,
            ...     filters={'category': 'python', 'difficulty': 'beginner'},
            ...     top_k=5
            ... )
        """
        # Apply metadata filters first
        valid_indices = []
        for i, meta in enumerate(self.metadata):
            if filters is None:
                valid_indices.append(i)
            else:
                # Check if all filter conditions are met
                if all(meta.get(key) == value for key, value in filters.items()):
                    valid_indices.append(i)
        
        if not valid_indices:
            return []  # No documents match filters
        
        # Calculate similarities only for valid documents
        valid_embeddings = self.embeddings[valid_indices]
        similarities = np.array([
            cosine_similarity(query_embedding, emb) 
            for emb in valid_embeddings
        ])
        
        # Get top-k from filtered set
        k = min(top_k, len(valid_indices))
        top_filtered_indices = np.argsort(similarities)[-k:][::-1]
        top_original_indices = [valid_indices[i] for i in top_filtered_indices]
        
        # Return documents with metadata
        return [
            {
                'text': self.documents[i],
                'metadata': self.metadata[i],
                'similarity': similarities[top_filtered_indices[j]]
            }
            for j, i in enumerate(top_original_indices)
        ]


class DynamicFilterRetriever:
    """
    Advanced retriever that suggests filters based on query content.
    
    Uses an LLM to extract filter conditions from natural language queries.
    """
    
    def __init__(self, base_retriever: MetadataFilteredRetriever, llm_client):
        """
        Initialize dynamic filter retriever.
        
        Args:
            base_retriever: Metadata-filtered retriever instance
            llm_client: LLM client for filter extraction
        """
        self.retriever = base_retriever
        self.llm = llm_client
    
    def extract_filters(self, query: str) -> Dict[str, Any]:
        """
        Extract metadata filters from natural language query.
        
        Example:
            Query: "Show me Python examples from 2024"
            Extracted: {'language': 'python', 'year': 2024}
        
        Args:
            query: Natural language query
        
        Returns:
            Dictionary of extracted filters
        """
        prompt = f"""Extract metadata filters from this query. 
Return only valid JSON with filter keys and values.

Query: "{query}"

Available filter keys: source, year, category, language, difficulty, author

JSON:"""
        
        response = self.llm.generate_content(prompt)
        
        try:
            import json
            filters = json.loads(response.text.strip())
            return filters
        except:
            return {}  # No valid filters extracted
    
    def retrieve(self, query: str, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve using automatically extracted filters.
        
        Args:
            query: Natural language query
            query_embedding: Query embedding
            top_k: Number of results
        
        Returns:
            Filtered and ranked documents
        """
        filters = self.extract_filters(query)
        return self.retriever.retrieve_with_filters(query_embedding, filters, top_k)
```

**Common Metadata Schema Examples**:

```python
# Documentation metadata
metadata = {
    'source': 'official_docs',
    'category': 'tutorial',
    'language': 'python',
    'version': '3.11',
    'last_updated': '2024-01-15'
}

# Research paper metadata
metadata = {
    'source': 'arxiv',
    'year': 2024,
    'authors': ['Smith, J.', 'Doe, A.'],
    'field': 'machine_learning',
    'peer_reviewed': True
}

# Code example metadata
metadata = {
    'source': 'github',
    'language': 'python',
    'difficulty': 'intermediate',
    'topic': 'async_programming',
    'lines_of_code': 45
}
```

**Cost Impact**: Varies based on filter extraction method:
- Static filters: No cost
- LLM-extracted filters: +1 small LLM call (~5-10% increase)

### Advanced Retrieval Strategies
- status: active
- type: guideline
- id: rags-agent.retrieval.advanced
- priority: medium
<!-- content -->
Beyond basic semantic similarity, several advanced strategies can further improve retrieval quality.

#### Maximal Marginal Relevance (MMR)
- status: active
- type: context
- id: rags-agent.retrieval.advanced.mmr
<!-- content -->
MMR balances relevance with diversity to avoid retrieving redundant documents. Instead of just taking the top-k most similar documents, MMR iteratively selects documents that are relevant to the query but diverse from already-selected documents.

**Use when**: Retrieved documents are very similar to each other, lacking diverse perspectives.

**Trade-off**: Slightly lower average relevance per document, but better overall coverage.

#### Parent Document Retrieval
- status: active
- type: context
- id: rags-agent.retrieval.advanced.parent-doc
<!-- content -->
Retrieve small chunks for precision, but return larger parent documents for context. This gives you the best of both worlds: accurate matching with sufficient surrounding context.

**Implementation approach**:
1. Index small chunks (100-200 tokens) for precise matching
2. Store references to parent documents
3. When a chunk matches, return the full parent section (500-1000 tokens)

**Use when**: Chunks are too small and lack necessary context, but larger chunks hurt retrieval precision.

#### Sentence Window Retrieval
- status: active
- type: context
- id: rags-agent.retrieval.advanced.sentence-window
<!-- content -->
Similar to parent document retrieval, but retrieves individual sentences for matching, then expands to include surrounding sentences (e.g., 2 sentences before and after).

**Use when**: You need precise sentence-level matching but want to preserve local context.

### Query-Retrieval Optimization Summary
- status: active
- type: guideline
- id: rags-agent.retrieval.summary
<!-- content -->
Decision matrix for choosing retrieval techniques:

| Problem | Primary Solution | Alternative |
|:--------|:-----------------|:------------|
| Poor entity/number matching | Hybrid Search | Metadata filtering |
| Low precision (too much noise) | Reranking | Reduce top-k |
| Need specific document types | Metadata Filtering | Query refinement |
| Redundant results | MMR | Increase diversity |
| Chunks too small | Parent Document Retrieval | Larger chunks |
| Complex queries | Query Decomposition (see below) | Step-back prompting |

**Typical Production Stack**:
1. **Stage 1**: Hybrid search (semantic + BM25) with metadata filtering → 20-50 candidates
2. **Stage 2**: Reranking with cross-encoder → Top 5-10 results
3. **Stage 3**: MMR for diversity (optional) → Final 3-5 results

**Performance Characteristics**:

| Technique | Quality Gain | Latency Impact | Cost Impact |
|:----------|:-------------|:---------------|:------------|
| Hybrid Search | +10-15% recall | Negligible | None |
| Reranking | +10-20% precision | +50-200ms | None |
| Metadata Filtering | Varies | Negligible | None |
| MMR | +5-10% coverage | +10-50ms | None |
| Parent Doc Retrieval | +15-25% context | Negligible | None |

### Query Decomposition
- status: active
- type: task
- id: rags-agent.retrieval.decomposition
- priority: high
- estimate: 15m
<!-- content -->
Break complex questions into simpler sub-queries before retrieval. This is the highest-impact, lowest-cost improvement.

**When to use**: Questions with multiple parts, comparisons, or implicit sub-questions.

**Implementation**:

```python
def decompose_query(question: str, llm_client) -> list[str]:
    """
    Decompose a complex question into simpler search queries.
    
    Args:
        question: The original user question
        llm_client: LLM client for decomposition
    
    Returns:
        List of 1-4 sub-queries including the original
    """
    # Minimal prompt to keep costs low
    prompt = f"""Break this question into 1-3 simple search queries:
"{question}"

Return ONLY the queries, one per line. If already simple, return as-is."""
    
    response = llm_client.generate_content(prompt)
    queries = [q.strip() for q in response.text.strip().split('\n') if q.strip()]
    
    # Always include original, cap at 4 total
    if question not in queries:
        queries.insert(0, question)
    return queries[:4]


def retrieve_with_decomposition(question: str, vector_store, llm_client, top_k: int = 3) -> list[dict]:
    """
    Retrieve documents using query decomposition.
    
    Searches for each sub-query and combines results.
    
    Args:
        question: Original question
        vector_store: Vector database
        llm_client: LLM client
        top_k: Results per sub-query
    
    Returns:
        Combined, deduplicated results
    """
    queries = decompose_query(question, llm_client)
    
    all_results = []
    seen_ids = set()
    
    for query in queries:
        results = vector_store.query(query_texts=[query], n_results=top_k)
        for doc, doc_id in zip(results['documents'][0], results['ids'][0]):
            if doc_id not in seen_ids:
                all_results.append({'text': doc, 'id': doc_id, 'query': query})
                seen_ids.add(doc_id)
    
    return all_results
```

**Example**:

| Original Question | Decomposed Queries |
|:------------------|:-------------------|
| "What are the differences between React and Vue for large-scale applications?" | 1. "React large-scale applications" <br> 2. "Vue large-scale applications" <br> 3. "React vs Vue comparison" |
| "How did the company perform in Q3 2023 compared to Q3 2022?" | 1. "Company Q3 2023 performance" <br> 2. "Company Q3 2022 performance" |

**Cost Impact**: +1 cheap LLM call (~5-10% increase)
**Quality Impact**: +15-25% recall for complex questions

### Step-Back Prompting
- status: active
- type: task
- id: rags-agent.retrieval.stepback
- priority: medium
- estimate: 30m
<!-- content -->
Generate a more abstract, higher-level question to retrieve broader context before answering the specific question.

**When to use**: Questions requiring background knowledge or context that might not be directly in the corpus.

**Implementation**:

```python
def generate_stepback_question(question: str, llm_client) -> str:
    """
    Generate a step-back question for broader context retrieval.
    
    Args:
        question: Original specific question
        llm_client: LLM client
    
    Returns:
        Higher-level, more abstract question
    """
    prompt = f"""Given this specific question, generate a more general question 
that would help understand the background context.

Specific question: "{question}"

Step-back question (more general):"""
    
    response = llm_client.generate_content(prompt)
    return response.text.strip()


def retrieve_with_stepback(question: str, vector_store, llm_client, top_k: int = 3) -> dict:
    """
    Retrieve using both original and step-back questions.
    
    Args:
        question: Original question
        vector_store: Vector database
        llm_client: LLM client
        top_k: Results per query
    
    Returns:
        Dictionary with context and background results
    """
    # Get step-back question
    stepback_q = generate_stepback_question(question, llm_client)
    
    # Retrieve for both
    original_results = vector_store.query(query_texts=[question], n_results=top_k)
    stepback_results = vector_store.query(query_texts=[stepback_q], n_results=top_k)
    
    return {
        'context': original_results['documents'][0],
        'background': stepback_results['documents'][0],
        'stepback_question': stepback_q
    }
```

**Example**:

| Specific Question | Step-Back Question |
|:------------------|:-------------------|
| "Why did the 2008 financial crisis cause unemployment?" | "What are the general mechanisms by which financial crises affect labor markets?" |
| "How do I fix error X in library Y?" | "How does error handling work in library Y?" |

**Cost Impact**: +1 LLM call (~5-10% increase)
**Quality Impact**: +10-20% for questions requiring background knowledge

## Generation Improvements
- status: active
- type: plan
- id: rags-agent.generation
<!-- content -->
This section covers techniques to improve how the LLM uses retrieved context to generate answers.

### Self-Ask Pattern
- status: active
- type: task
- id: rags-agent.generation.self-ask
- priority: high
- estimate: 1h
<!-- content -->
Let the LLM iteratively ask and answer sub-questions, retrieving new context at each step.

**When to use**: Complex multi-hop questions where the answer to one part determines what to search for next.

**Implementation**:

```python
class SelfAskRAG:
    """
    RAG system that lets the LLM iteratively ask follow-up questions.
    
    For complex queries, the LLM may need to answer intermediate questions
    before it can answer the main question. This pattern supports that.
    """
    
    def __init__(self, vector_store, llm_client, max_iterations: int = 3):
        """
        Initialize self-ask RAG.
        
        Args:
            vector_store: Vector database
            llm_client: LLM client
            max_iterations: Maximum follow-up questions
        """
        self.vector_store = vector_store
        self.llm = llm_client
        self.max_iterations = max_iterations
    
    def answer(self, question: str) -> dict:
        """
        Answer question with iterative self-asking.
        
        The LLM decides whether it needs more information and generates
        follow-up questions as needed.
        
        Args:
            question: User question
        
        Returns:
            Dictionary with final answer and reasoning trace
        """
        context_history = []
        reasoning_trace = []
        
        current_question = question
        
        for i in range(self.max_iterations):
            # Retrieve context for current question
            results = self.vector_store.query(query_texts=[current_question], n_results=3)
            context = "\n".join(results['documents'][0])
            context_history.append(context)
            
            # Ask LLM if it can answer or needs more info
            prompt = f"""Question: {question}

Current context:
{context}

Previous reasoning:
{chr(10).join(reasoning_trace)}

Can you answer the question with this context? 
If yes, provide the final answer.
If no, ask a follow-up question to get more information.

Response format:
ANSWER: [your answer] OR
FOLLOW_UP: [your follow-up question]"""
            
            response = self.llm.generate_content(prompt).text
            
            if response.startswith("ANSWER:"):
                return {
                    'answer': response.replace("ANSWER:", "").strip(),
                    'iterations': i + 1,
                    'reasoning': reasoning_trace
                }
            elif response.startswith("FOLLOW_UP:"):
                follow_up = response.replace("FOLLOW_UP:", "").strip()
                reasoning_trace.append(f"Iteration {i+1}: Asked '{follow_up}'")
                current_question = follow_up
            else:
                # LLM didn't follow format, treat as answer
                return {
                    'answer': response,
                    'iterations': i + 1,
                    'reasoning': reasoning_trace
                }
        
        # Max iterations reached, synthesize from what we have
        final_prompt = f"""Question: {question}

All gathered context:
{chr(10).join(context_history)}

Provide your best answer based on this context:"""
        
        return {
            'answer': self.llm.generate_content(final_prompt).text,
            'iterations': self.max_iterations,
            'reasoning': reasoning_trace
        }
```

**Example Flow**:

```
User: "What was the revenue of the company that acquired Twitter?"

Iteration 1:
- Search: "What was the revenue of the company that acquired Twitter?"
- No direct answer found
- Follow-up: "Which company acquired Twitter?"

Iteration 2:
- Search: "Which company acquired Twitter?"
- Found: "Twitter was acquired by X Corp (formerly Twitter, Inc.) led by Elon Musk"
- Follow-up: "What is X Corp revenue?"

Iteration 3:
- Search: "What is X Corp revenue?"
- Found revenue figures
- ANSWER: "X Corp's estimated revenue is..."
```

**Cost Impact**: +30-50% for complex questions (multiple iterations)
**Quality Impact**: +20-30% for multi-hop reasoning questions

### Verify-Then-Answer Pattern
- status: active
- type: task
- id: rags-agent.generation.verify
- priority: medium
- estimate: 30m
<!-- content -->
Have the LLM explicitly verify its claims against the retrieved context before outputting.

**Implementation**:

```python
def verify_then_answer(question: str, context: list[str], llm_client) -> dict:
    """
    Generate answer with explicit verification step.
    
    The LLM first generates a draft answer, then verifies each claim
    against the context, and finally outputs a verified answer.
    
    Args:
        question: User question
        context: Retrieved context chunks
        llm_client: LLM client
    
    Returns:
        Dictionary with verified answer and verification details
    """
    context_str = "\n\n".join(context)
    
    prompt = f"""Question: {question}

Context:
{context_str}

Follow these steps:
1. DRAFT: Write a draft answer based on the context
2. VERIFY: For each claim in your draft, check if it's supported by the context
3. FINAL: Write the final answer, removing or hedging unsupported claims

Format your response as:
DRAFT: [draft answer]
VERIFICATION: [list each claim and whether it's supported]
FINAL: [final verified answer]"""
    
    response = llm_client.generate_content(prompt).text
    
    # Parse response (simplified)
    parts = {}
    current_section = None
    for line in response.split('\n'):
        if line.startswith('DRAFT:'):
            current_section = 'draft'
            parts['draft'] = line.replace('DRAFT:', '').strip()
        elif line.startswith('VERIFICATION:'):
            current_section = 'verification'
            parts['verification'] = line.replace('VERIFICATION:', '').strip()
        elif line.startswith('FINAL:'):
            current_section = 'final'
            parts['final'] = line.replace('FINAL:', '').strip()
        elif current_section:
            parts[current_section] = parts.get(current_section, '') + ' ' + line
    
    return parts
```

**Cost Impact**: Negligible (single prompt with multiple sections)
**Quality Impact**: -10-20% hallucination rate

### Citation Generation
- status: active
- type: task
- id: rags-agent.generation.citations
- priority: medium
- estimate: 30m
<!-- content -->
Require the LLM to cite specific sources for each claim, improving traceability and trust.

**Implementation**:

```python
def answer_with_citations(question: str, chunks: list[dict], llm_client) -> dict:
    """
    Generate answer with inline citations.
    
    Each claim in the answer references a specific chunk from the context.
    
    Args:
        question: User question
        chunks: Retrieved chunks
        llm_client: LLM client
    
    Returns:
        Dictionary with answer and citations
    """
    context = "\n\n".join([f"[{i}] {chunk['text']}" for i, chunk in enumerate(chunks)])
    
    prompt = f"""Answer the question using ONLY the provided context. 
After each claim, cite the source using [0], [1], etc.

Question: {question}

Context:
{context}

Answer with citations:"""
    
    response = llm_client.generate_content(prompt)
    
    return {
        'answer': response.text,
        'chunks': chunks
    }
```

**Example output**:
"The company was founded in 2015 [0] and reached 1 million users in 2018 [2]."

## Structured Data Integration
- status: active
- type: plan
- id: rags-agent.structured
<!-- content -->
RAG systems often need to query structured data (databases, APIs) alongside documents. This section covers integration patterns, with particular focus on combining RAG with MCP (Model Context Protocol) for hybrid architectures.

### The Limitation of Pure RAG
- status: active
- type: context
- id: rags-agent.structured.limitation
<!-- content -->
Pure RAG retrieves semantically similar chunks, but the LLM has no structured way to navigate, filter, or reason over the underlying data schema. The LLM only sees whatever chunks the embedding search returns.

**Example problem**: For queries like "What talks are happening next week about epistemology?", retrieval might miss relevant events if the semantic overlap isn't strong enough, or it may retrieve talks about epistemology from last year.

The core issue is that the LLM can't "see the database" - it only sees whatever chunks the embedding search returns.

### When to Use Structured Queries
- status: active
- type: guideline
- id: rags-agent.structured.when
<!-- content -->
Semantic search fails for:

- Exact numerical comparisons ("sales > $1M")
- Aggregations ("average price by category")
- Complex filters ("products launched in Q3 2023 with rating > 4.5")
- Relational joins ("customers who bought X and Y")
- Date-based queries ("events next week", "talks this month")
- Enumeration queries ("list all reading groups", "how many speakers?")

For these, you need SQL/API queries or structured tools, not embeddings.

### RAG + MCP Hybrid Architecture
- status: active
- type: plan
- id: rags-agent.structured.hybrid-architecture
- priority: high
<!-- content -->
The combination of RAG and MCP addresses the fundamental limitation: MCP gives the LLM structured tools to navigate data intentionally, while RAG handles fuzzy semantic queries. Together, they cover more query types effectively than either alone.

#### Architecture Overview
- status: active
- type: guideline
- id: rags-agent.structured.hybrid-architecture.overview
<!-- content -->
The hybrid architecture gives the LLM two complementary retrieval mechanisms:

```
┌─────────────────────────────────────────────────────────────┐
│                        User Query                           │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LLM (with MCP tools)                     │
│                                                             │
│  The LLM decides HOW to answer:                             │
│  • Use MCP tools for structured queries (dates, filters)    │
│  • Use RAG for semantic/conceptual queries                  │
│  • Combine both for complex queries                         │
└────────────┬────────────────────────────┬───────────────────┘
             │                            │
             ▼                            ▼
┌────────────────────────┐    ┌────────────────────────────────┐
│    MCP Server          │    │         RAG Pipeline           │
│    (JSON operations)   │    │      (ChromaDB + embeddings)   │
│                        │    │                                │
│ • filter_by_date()     │    │ • semantic_search(query)       │
│ • get_speaker()        │    │ • retrieve_similar_chunks()    │
│ • list_topics()        │    │                                │
│ • get_upcoming()       │    │                                │
└────────────┬───────────┘    └────────────────┬───────────────┘
             │                                 │
             └────────────┬────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   data/*.json files   │
              │   (single source of   │
              │       truth)          │
              └───────────────────────┘
```

**Key insight**: Both MCP tools and the RAG pipeline operate on the same underlying data (JSON files), but provide different access patterns optimized for different query types.

#### When Each Approach Wins
- status: active
- type: guideline
- id: rags-agent.structured.hybrid-architecture.routing
<!-- content -->
The LLM learns to route queries to the appropriate retrieval mechanism:

| Query Type | Best Approach | Rationale |
|:-----------|:--------------|:----------|
| "What's happening next Tuesday?" | **MCP** (date filter) | Deterministic date comparison |
| "Tell me about decision theory research" | **RAG** (semantic) | Conceptual/thematic query |
| "Who's speaking about epistemology this month?" | **Both** | MCP filters dates, RAG finds topic matches |
| "What reading groups exist?" | **MCP** (list/enumerate) | Structured enumeration |
| "Explain the connection between X and Y" | **RAG** (semantic) | Conceptual understanding needed |
| "How many events are scheduled for January?" | **MCP** (aggregate) | Counting requires structured access |

#### Benefits of the Hybrid Approach
- status: active
- type: context
- id: rags-agent.structured.hybrid-architecture.benefits
<!-- content -->
1. **Better space partitioning**: The LLM can navigate the data structure intentionally rather than relying solely on embedding similarity.

2. **Deterministic operations where appropriate**: Date filtering is exact, not probabilistic. Counts are accurate.

3. **Reduced hallucination risk**: Structured tools return actual data, not "retrieved chunks that might be relevant."

4. **Composability**: The LLM can chain operations (filter by date → then semantic search within results).

5. **Schema awareness**: The LLM understands what fields and categories exist in the data.

### MCP Server for JSON Data
- status: active
- type: task
- id: rags-agent.structured.mcp-json
- priority: high
- estimate: 3h
<!-- content -->
Implement an MCP server that exposes structured operations over JSON data files, complementing the semantic search provided by RAG.

```python
"""
MCP Server that exposes structured operations over JSON data.

This gives the LLM direct, structured access to the data - complementing 
the semantic search provided by RAG. The LLM can now navigate the data
intentionally rather than relying solely on embedding similarity.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from mcp.server import Server
from mcp.types import Tool, TextContent

# Initialize MCP server
server = Server("json-data-tools")

# Path to your JSON data directory
DATA_DIR = Path("data/json")


def load_events() -> list[dict]:
    """
    Load all event data from JSON files.
    
    Returns:
        List of event dictionaries
    """
    events = []
    events_file = DATA_DIR / "events.json"
    if events_file.exists():
        with open(events_file) as f:
            events = json.load(f)
    return events


def load_people() -> list[dict]:
    """
    Load all people data from JSON files.
    
    Returns:
        List of people dictionaries
    """
    people_file = DATA_DIR / "people.json"
    if people_file.exists():
        with open(people_file) as f:
            return json.load(f)
    return []


# ============================================================
# MCP Tool Definitions
# ============================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    Expose available tools to the LLM.
    
    These tools allow structured queries that complement RAG's 
    semantic search capabilities.
    
    Returns:
        List of Tool definitions
    """
    return [
        Tool(
            name="get_events_by_date_range",
            description=(
                "Retrieve events within a specific date range. "
                "Use this for temporal queries like 'next week', 'this month', etc. "
                "Returns structured event data including title, date, speaker, and topic."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in ISO format (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in ISO format (YYYY-MM-DD)"
                    }
                },
                "required": ["start_date", "end_date"]
            }
        ),
        Tool(
            name="get_upcoming_events",
            description=(
                "Get the next N upcoming events, sorted chronologically. "
                "Use this for queries about 'upcoming', 'next', or 'soon'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of events to return (default: 5)",
                        "default": 5
                    }
                }
            }
        ),
        Tool(
            name="filter_events_by_type",
            description=(
                "Filter events by their type (e.g., 'talk', 'reading_group', "
                "'workshop', 'colloquium'). Use when user asks about specific "
                "event categories."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": "Type of event to filter for"
                    }
                },
                "required": ["event_type"]
            }
        ),
        Tool(
            name="get_speaker_info",
            description=(
                "Get detailed information about a specific person/speaker. "
                "Use when user asks about a specific researcher or speaker."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the person to look up"
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="list_event_types",
            description=(
                "List all distinct event types/categories available in the database. "
                "Use to understand what kinds of events exist."
            ),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="list_topics",
            description=(
                "List all distinct research topics/areas covered in events. "
                "Useful for exploring what research areas are active."
            ),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="count_events",
            description=(
                "Count events matching optional filters. "
                "Use for questions like 'how many talks?' or 'how many events this month?'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": "Optional: filter by event type"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Optional: count events after this date (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Optional: count events before this date (YYYY-MM-DD)"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Handle tool calls from the LLM.
    
    Each tool provides structured access to the JSON data,
    enabling operations that semantic search cannot perform well.
    
    Args:
        name: Tool name to execute
        arguments: Tool arguments from LLM
    
    Returns:
        List of TextContent with results
    """
    
    if name == "get_events_by_date_range":
        # Parse dates and filter events within the range
        start = datetime.fromisoformat(arguments["start_date"])
        end = datetime.fromisoformat(arguments["end_date"])
        
        events = load_events()
        filtered = [
            e for e in events
            if start <= datetime.fromisoformat(e.get("date", "1900-01-01")) <= end
        ]
        
        return [TextContent(
            type="text",
            text=json.dumps(filtered, indent=2, default=str)
        )]
    
    elif name == "get_upcoming_events":
        # Get next N events from today onwards
        limit = arguments.get("limit", 5)
        now = datetime.now()
        
        events = load_events()
        # Filter to future events and sort by date
        upcoming = sorted(
            [e for e in events 
             if datetime.fromisoformat(e.get("date", "1900-01-01")) >= now],
            key=lambda x: x.get("date", "")
        )[:limit]
        
        return [TextContent(
            type="text",
            text=json.dumps(upcoming, indent=2, default=str)
        )]
    
    elif name == "filter_events_by_type":
        # Filter events by their category/type field
        event_type = arguments["event_type"].lower()
        
        events = load_events()
        filtered = [
            e for e in events
            if e.get("type", "").lower() == event_type
        ]
        
        return [TextContent(
            type="text",
            text=json.dumps(filtered, indent=2, default=str)
        )]
    
    elif name == "get_speaker_info":
        # Fuzzy match on speaker/person name
        name_query = arguments["name"].lower()
        
        people = load_people()
        matches = [
            p for p in people
            if name_query in p.get("name", "").lower()
        ]
        
        return [TextContent(
            type="text",
            text=json.dumps(matches, indent=2, default=str)
        )]
    
    elif name == "list_event_types":
        # Enumerate all distinct event types
        events = load_events()
        types = list(set(e.get("type", "unknown") for e in events))
        
        return [TextContent(
            type="text",
            text=json.dumps({"event_types": sorted(types)}, indent=2)
        )]
    
    elif name == "list_topics":
        # Enumerate all distinct topics/tags
        events = load_events()
        all_topics = set()
        for e in events:
            topics = e.get("topics", []) or e.get("tags", [])
            all_topics.update(topics)
        
        return [TextContent(
            type="text",
            text=json.dumps({"topics": sorted(all_topics)}, indent=2)
        )]
    
    elif name == "count_events":
        # Count events with optional filters
        events = load_events()
        
        # Apply filters
        if arguments.get("event_type"):
            events = [e for e in events 
                     if e.get("type", "").lower() == arguments["event_type"].lower()]
        
        if arguments.get("start_date"):
            start = datetime.fromisoformat(arguments["start_date"])
            events = [e for e in events 
                     if datetime.fromisoformat(e.get("date", "1900-01-01")) >= start]
        
        if arguments.get("end_date"):
            end = datetime.fromisoformat(arguments["end_date"])
            events = [e for e in events 
                     if datetime.fromisoformat(e.get("date", "2100-01-01")) <= end]
        
        return [TextContent(
            type="text",
            text=json.dumps({"count": len(events)}, indent=2)
        )]
    
    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]


# Entry point for running the server
if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server
    
    async def main():
        """Run the MCP server over stdio."""
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream)
    
    asyncio.run(main())
```

### Hybrid RAG+MCP Engine
- status: active
- type: task
- id: rags-agent.structured.hybrid-engine
- priority: high
- estimate: 2h
<!-- content -->
Implement a hybrid engine that gives the LLM access to both MCP tools and RAG retrieval, letting it choose the best approach for each query.

```python
"""
Hybrid RAG + MCP engine.

The LLM can use structured MCP tools OR semantic RAG retrieval,
choosing the best approach based on the query type. It can also
combine both for complex queries.
"""

from typing import Any
import json


class HybridRAGMCPEngine:
    """
    Engine combining RAG semantic search with MCP structured tools.
    
    This gives the LLM two complementary retrieval mechanisms:
    - MCP tools for structured queries (dates, filters, counts, enumerations)
    - RAG for semantic/conceptual queries (topics, themes, meanings)
    
    The LLM decides which approach to use based on the query.
    """
    
    def __init__(self, vector_store, mcp_client, llm_client):
        """
        Initialize hybrid engine.
        
        Args:
            vector_store: Vector database for semantic search (e.g., ChromaDB)
            mcp_client: MCP client connected to the JSON tools server
            llm_client: LLM client for query processing and generation
        """
        self.vector_store = vector_store
        self.mcp_client = mcp_client
        self.llm = llm_client
    
    async def get_available_tools(self) -> list[dict]:
        """
        Get tool definitions from MCP server plus RAG as a pseudo-tool.
        
        Returns:
            List of tool definitions for the LLM
        """
        # Get MCP tools
        mcp_tools = await self.mcp_client.list_tools()
        
        # Add RAG as a tool the LLM can call
        rag_tool = {
            "name": "semantic_search",
            "description": (
                "Search for conceptually related content using semantic embeddings. "
                "Use for thematic queries, conceptual questions, or when looking for "
                "documents about a topic without exact filters. "
                "Returns text chunks ranked by semantic similarity."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query describing what you're looking for"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
        
        return mcp_tools + [rag_tool]
    
    async def process_query(self, user_query: str) -> str:
        """
        Process a user query using hybrid RAG + MCP approach.
        
        The LLM decides which tools/retrieval to use based on the query type.
        It may use MCP tools, RAG, or both.
        
        Args:
            user_query: The user's natural language question
        
        Returns:
            Generated answer string
        """
        # Get all available tools
        tools = await self.get_available_tools()
        
        # System prompt explaining the hybrid capabilities
        system_prompt = """You are an assistant with two ways to find information:

1. **Structured Tools (MCP)**: Use these for precise queries:
   - Date-based queries ("next week", "this month", "January events")
   - Filtering by type ("talks", "reading groups", "workshops")
   - Looking up specific people by name
   - Listing categories, topics, or event types
   - Counting events or aggregating data

2. **Semantic Search (RAG)**: Use this for conceptual queries:
   - Research topics ("decision theory", "philosophy of physics")
   - Abstract concepts or themes
   - When you need context about unfamiliar terms
   - Exploratory questions about what's available

You can combine both approaches for complex queries. For example:
- "Who's speaking about epistemology next month?" → Use date filter, then semantic search
- "What topics are covered in the reading groups?" → Use event type filter, then list topics

Always prefer structured tools when the query involves dates, names, counts, or categories.
Use semantic search when the query is conceptual or exploratory.
"""
        
        # Let LLM decide which tools to call
        response = await self.llm.generate_with_tools(
            system=system_prompt,
            user=user_query,
            tools=tools
        )
        
        # Execute tool calls and gather results
        all_results = []
        for tool_call in response.tool_calls:
            if tool_call.name == "semantic_search":
                # Execute RAG retrieval
                query = tool_call.parameters.get("query", user_query)
                top_k = tool_call.parameters.get("top_k", 5)
                
                results = self.vector_store.query(
                    query_texts=[query], 
                    n_results=top_k
                )
                all_results.append({
                    "tool": "semantic_search",
                    "query": query,
                    "results": results['documents'][0]
                })
            else:
                # Execute MCP tool
                result = await self.mcp_client.call_tool(
                    tool_call.name, 
                    tool_call.parameters
                )
                all_results.append({
                    "tool": tool_call.name,
                    "parameters": tool_call.parameters,
                    "results": result
                })
        
        # Synthesize final answer from all results
        synthesis_prompt = f"""Original question: {user_query}

Tool results:
{json.dumps(all_results, indent=2, default=str)}

Based on these results, provide a comprehensive answer to the user's question.
If some information wasn't found, acknowledge that clearly."""
        
        final_answer = await self.llm.generate_content(synthesis_prompt)
        return final_answer.text


class SimplifiedHybridEngine:
    """
    Simplified hybrid engine for cases where full MCP infrastructure is overkill.
    
    Uses direct function calls instead of MCP protocol, but maintains
    the same hybrid architecture pattern.
    """
    
    def __init__(self, vector_store, json_data_path: str, llm_client):
        """
        Initialize simplified hybrid engine.
        
        Args:
            vector_store: Vector database for RAG
            json_data_path: Path to JSON data directory
            llm_client: LLM client
        """
        self.vector_store = vector_store
        self.data_path = Path(json_data_path)
        self.llm = llm_client
        
        # Register structured query functions
        self.tools = {
            "get_upcoming_events": self._get_upcoming_events,
            "filter_by_type": self._filter_by_type,
            "search_by_date": self._search_by_date,
            "list_categories": self._list_categories,
            "semantic_search": self._semantic_search
        }
    
    def _load_data(self) -> list[dict]:
        """Load JSON data."""
        data_file = self.data_path / "events.json"
        if data_file.exists():
            with open(data_file) as f:
                return json.load(f)
        return []
    
    def _get_upcoming_events(self, limit: int = 5) -> list[dict]:
        """Get next N upcoming events."""
        from datetime import datetime
        events = self._load_data()
        now = datetime.now()
        upcoming = sorted(
            [e for e in events 
             if datetime.fromisoformat(e.get("date", "1900-01-01")) >= now],
            key=lambda x: x.get("date", "")
        )
        return upcoming[:limit]
    
    def _filter_by_type(self, event_type: str) -> list[dict]:
        """Filter events by type."""
        events = self._load_data()
        return [e for e in events if e.get("type", "").lower() == event_type.lower()]
    
    def _search_by_date(self, start_date: str, end_date: str) -> list[dict]:
        """Search events within date range."""
        from datetime import datetime
        events = self._load_data()
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        return [
            e for e in events
            if start <= datetime.fromisoformat(e.get("date", "1900-01-01")) <= end
        ]
    
    def _list_categories(self) -> list[str]:
        """List all event categories."""
        events = self._load_data()
        return list(set(e.get("type", "unknown") for e in events))
    
    def _semantic_search(self, query: str, top_k: int = 5) -> list[str]:
        """Perform RAG semantic search."""
        results = self.vector_store.query(query_texts=[query], n_results=top_k)
        return results['documents'][0]
    
    def answer(self, question: str) -> str:
        """
        Answer question using hybrid approach.
        
        Args:
            question: User question
        
        Returns:
            Answer string
        """
        # Build tool descriptions for LLM
        tool_descriptions = """Available tools:
- get_upcoming_events(limit): Get next N upcoming events
- filter_by_type(event_type): Filter events by category
- search_by_date(start_date, end_date): Find events in date range
- list_categories(): List all event types
- semantic_search(query, top_k): Search by meaning/topic"""
        
        # First pass: let LLM decide which tools to use
        routing_prompt = f"""{tool_descriptions}

Question: {question}

Which tool(s) should be used to answer this question?
Output as JSON: {{"tools": ["{{"name": "tool_name", "args": {{...}}}}"]}}"""
        
        routing_response = self.llm.generate_content(routing_prompt).text
        
        try:
            tool_calls = json.loads(routing_response).get("tools", [])
        except:
            # Fallback to semantic search if routing fails
            tool_calls = [{"name": "semantic_search", "args": {"query": question}}]
        
        # Execute tools
        results = []
        for call in tool_calls:
            tool_name = call.get("name")
            args = call.get("args", {})
            
            if tool_name in self.tools:
                result = self.tools[tool_name](**args)
                results.append({"tool": tool_name, "result": result})
        
        # Synthesize answer
        synthesis_prompt = f"""Question: {question}

Tool results:
{json.dumps(results, indent=2, default=str)}

Provide a helpful answer based on these results:"""
        
        return self.llm.generate_content(synthesis_prompt).text
```

### MCP-Based Tool Integration
- status: active
- type: task
- id: rags-agent.structured.mcp
- priority: high
- estimate: 2h
<!-- content -->
Use Model Context Protocol (MCP) to expose structured data sources as tools.

**Architecture**:
1. MCP server wraps your database/API
2. LLM decides when to use tools vs. semantic search
3. Results are combined before final answer

```python
"""
Example MCP tool wrapper for database queries.

This allows the LLM to query structured data when semantic search
isn't appropriate.
"""

from typing import Any, Dict

class DatabaseMCPTool:
    """
    MCP tool that exposes database queries to the LLM.
    
    The LLM can generate SQL queries or use predefined query templates.
    """
    
    def __init__(self, db_connection):
        """
        Initialize with database connection.
        
        Args:
            db_connection: Database connection object
        """
        self.db = db_connection
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Return MCP tool definition for the LLM.
        
        Returns:
            Tool schema with name, description, and parameters
        """
        return {
            "name": "query_database",
            "description": "Query structured data in the database. Use for exact filters, aggregations, or numerical comparisons.",
            "parameters": {
                "query_type": {
                    "type": "string",
                    "enum": ["filter", "aggregate", "join"],
                    "description": "Type of query to perform"
                },
                "table": {
                    "type": "string",
                    "description": "Table name"
                },
                "conditions": {
                    "type": "object",
                    "description": "Filter conditions (e.g., {'price': {'gt': 100}})"
                }
            }
        }
    
    def execute(self, query_type: str, table: str, conditions: Dict[str, Any]) -> list[dict]:
        """
        Execute database query based on LLM's parameters.
        
        Args:
            query_type: Type of query
            table: Table name
            conditions: Query conditions
        
        Returns:
            Query results
        """
        # Build SQL from structured parameters
        sql = self._build_sql(query_type, table, conditions)
        
        # Execute and return results
        cursor = self.db.execute(sql)
        return cursor.fetchall()
    
    def _build_sql(self, query_type: str, table: str, conditions: Dict[str, Any]) -> str:
        """
        Build safe SQL from structured parameters.
        
        Uses parameterized queries to prevent SQL injection.
        
        Args:
            query_type: Query type
            table: Table name
            conditions: Conditions dict
        
        Returns:
            SQL query string
        """
        # Implementation depends on your SQL builder/ORM
        # This is a simplified example
        if query_type == "filter":
            where_clauses = []
            for col, cond in conditions.items():
                if isinstance(cond, dict):
                    op = list(cond.keys())[0]
                    val = cond[op]
                    where_clauses.append(f"{col} {self._op_map[op]} {val}")
            
            where_str = " AND ".join(where_clauses)
            return f"SELECT * FROM {table} WHERE {where_str}"
        
        # Add other query types...
        
    _op_map = {
        'gt': '>',
        'lt': '<',
        'gte': '>=',
        'lte': '<=',
        'eq': '='
    }


class HybridRAGWithTools:
    """
    RAG system that combines semantic search with structured data tools.
    
    The LLM decides which approach to use based on the query.
    """
    
    def __init__(self, vector_store, db_tool: DatabaseMCPTool, llm_client):
        """
        Initialize hybrid RAG system.
        
        Args:
            vector_store: Vector database for semantic search
            db_tool: MCP tool for structured queries
            llm_client: LLM client with tool support
        """
        self.vector_store = vector_store
        self.db_tool = db_tool
        self.llm = llm_client
    
    def answer(self, question: str) -> str:
        """
        Answer question using the appropriate retrieval method.
        
        The LLM decides whether to use semantic search, database tools,
        or both based on the question type.
        
        Args:
            question: User question
        
        Returns:
            Answer string
        """
        # Provide tool definitions to LLM
        tools = [self.db_tool.get_tool_definition()]
        
        prompt = f"""Answer this question using the available tools.

Question: {question}

Tools available:
- semantic_search: For finding documents by meaning
- query_database: For exact filters, aggregations, numerical comparisons

Choose the appropriate tool(s) and provide the answer."""
        
        # LLM generates tool calls
        response = self.llm.generate_with_tools(prompt, tools)
        
        # Execute tools and combine results
        results = []
        for tool_call in response.tool_calls:
            if tool_call.name == "query_database":
                results.append(self.db_tool.execute(**tool_call.parameters))
            elif tool_call.name == "semantic_search":
                results.append(self.vector_store.query(**tool_call.parameters))
        
        # LLM synthesizes final answer
        synthesis_prompt = f"""Question: {question}

Results:
{results}

Synthesize a final answer:"""
        
        return self.llm.generate_content(synthesis_prompt).text
```

**When to use MCP vs. always using tools**:

| Scenario | Approach | Rationale |
|:---------|:---------|:----------|
| Mostly unstructured docs | RAG only | Tools add complexity with little benefit |
| Mixed structured + unstructured | Hybrid with MCP | LLM routes to appropriate backend |
| Mostly structured data | API/SQL directly | RAG adds unnecessary overhead |

### Lightweight Tool Runner
- status: active
- type: task
- id: rags-agent.structured.lightweight
- priority: medium
- estimate: 1h
<!-- content -->
For simple cases, implement tool calling without full MCP infrastructure.

```python
class SimpleTool:
    """
    Simple function tool that can be called by the LLM.
    
    Lighter weight than full MCP for simple use cases.
    """
    
    def __init__(self, name: str, description: str, function: callable):
        """
        Initialize simple tool.
        
        Args:
            name: Tool name
            description: What the tool does
            function: Python function to execute
        """
        self.name = name
        self.description = description
        self.function = function
    
    def execute(self, **kwargs) -> Any:
        """Execute the tool function."""
        return self.function(**kwargs)


class SimpleToolRunner:
    """
    Minimal tool calling system for RAG.
    
    Use when you need structured data access but don't want
    the overhead of MCP.
    """
    
    def __init__(self, vector_store, llm_client):
        """
        Initialize tool runner.
        
        Args:
            vector_store: Vector database
            llm_client: LLM client
        """
        self.vector_store = vector_store
        self.llm = llm_client
        self.tools = {}
    
    def register_tool(self, tool: SimpleTool) -> None:
        """
        Register a tool for use.
        
        Args:
            tool: SimpleTool instance
        """
        self.tools[tool.name] = tool
    
    def answer_with_tools(self, question: str) -> str:
        """
        Answer question with tool support.
        
        The LLM can call tools by outputting structured commands.
        
        Args:
            question: User question
        
        Returns:
            Final answer
        """
        tool_descriptions = "\n".join([
            f"- {name}: {tool.description}" 
            for name, tool in self.tools.items()
        ])
        
        prompt = f"""Answer this question. You can use these tools:

{tool_descriptions}

To call a tool, output:
TOOL_CALL: tool_name(param1=value1, param2=value2)

Question: {question}"""
        
        response = self.llm.generate_content(prompt).text
        
        # Parse and execute tool calls
        if "TOOL_CALL:" in response:
            # Extract tool call (simplified parsing)
            tool_call_line = [l for l in response.split('\n') if 'TOOL_CALL:' in l][0]
            tool_name = tool_call_line.split('(')[0].split(':')[1].strip()
            
            if tool_name in self.tools:
                # Execute tool (parameter parsing simplified)
                tool_result = self.tools[tool_name].execute()
                
                # LLM synthesizes with tool result
                synthesis_prompt = f"""{prompt}

Tool result:
{tool_result}

Final answer:"""
                
                return self.llm.generate_content(synthesis_prompt).text
        
        return response
```

### Challenges and Considerations
- status: active
- type: guideline
- id: rags-agent.structured.challenges
<!-- content -->
When implementing RAG + MCP hybrid systems, be aware of these challenges:

1. **Tool selection overhead**: The LLM needs to learn when to use which approach. Good system prompts and clear tool descriptions help.

2. **Schema dependency**: Your MCP tools need to match your JSON structure. Schema changes require updating MCP tools.

3. **Maintenance burden**: Two systems to maintain (RAG indexing + MCP tools). Consider which queries are most common to prioritize.

4. **Latency**: Multiple tool calls add latency. Consider caching and parallel execution where possible.

5. **Error handling**: MCP tools can fail. Implement fallback to RAG for robustness.

**Mitigation strategies**:

| Challenge | Mitigation |
|:----------|:-----------|
| Wrong tool selection | Clear tool descriptions, few-shot examples in prompt |
| Schema drift | Auto-generate tool definitions from JSON schema |
| Maintenance | Unified data layer, single source of truth |
| Latency | Parallel tool execution, caching frequent queries |
| Errors | Graceful fallback to RAG, retry logic |

## Cost Optimization
- status: active
- type: plan
- id: rags-agent.cost
<!-- content -->
RAG systems can get expensive with multiple LLM calls. This section covers cost reduction strategies.

### Query Caching
- status: active
- type: task
- id: rags-agent.cost.caching
- priority: high
- estimate: 1h
<!-- content -->
Cache common queries and their decompositions to avoid redundant LLM calls.

```python
"""
Caching layer for RAG queries.

Caches query decompositions, step-back questions, and even final answers
for repeated queries.
"""

import hashlib
import json
from typing import Optional, Any

class RAGCache:
    """
    Simple in-memory cache for RAG queries.
    
    For production, use Redis or similar for persistence and distribution.
    """
    
    def __init__(self):
        """Initialize empty cache."""
        self.cache = {}
    
    def _key(self, operation: str, query: str) -> str:
        """
        Generate cache key from operation and query.
        
        Args:
            operation: Operation type (e.g., 'decomposition', 'stepback')
            query: Query string
        
        Returns:
            Cache key
        """
        content = f"{operation}:{query}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, operation: str, query: str) -> Optional[Any]:
        """
        Get cached result if available.
        
        Args:
            operation: Operation type
            query: Query string
        
        Returns:
            Cached result or None
        """
        key = self._key(operation, query)
        return self.cache.get(key)
    
    def set(self, operation: str, query: str, result: Any) -> None:
        """
        Cache a result.
        
        Args:
            operation: Operation type
            query: Query string
            result: Result to cache
        """
        key = self._key(operation, query)
        self.cache[key] = result


class CachedRAGEngine:
    """
    RAG engine with caching support.
    
    Caches expensive operations like query decomposition and LLM calls.
    """
    
    def __init__(self, vector_store, llm_client):
        """
        Initialize cached RAG engine.
        
        Args:
            vector_store: Vector database
            llm_client: LLM client
        """
        self.vector_store = vector_store
        self.llm = llm_client
        self.cache = RAGCache()
    
    def decompose_query_cached(self, question: str) -> list[str]:
        """
        Decompose query with caching.
        
        Args:
            question: Original question
        
        Returns:
            List of sub-queries
        """
        # Check cache first
        cached = self.cache.get("decomposition", question)
        if cached:
            return cached
        
        # Not cached, perform decomposition
        prompt = f"""Break into search queries: "{question}"
Return ONLY queries, one per line."""
        
        response = self.llm.generate_content(prompt)
        queries = [q.strip() for q in response.text.split('\n') if q.strip()]
        
        if question not in queries:
            queries.insert(0, question)
        queries = queries[:4]
        
        # Cache result
        self.cache.set("decomposition", question, queries)
        return queries
```

**Cache hit rate impact**:
- 10% hit rate → ~3-5% cost reduction
- 50% hit rate → ~15-25% cost reduction
- 90% hit rate → ~27-45% cost reduction

### Model Tiering
- status: active
- type: guideline
- id: rags-agent.cost.tiering
- priority: medium
<!-- content -->
Use cheaper models for simple tasks, expensive models only for final generation.

| Task | Recommended Model | Rationale |
|:-----|:------------------|:----------|
| Query decomposition | `gemini-1.5-flash` / `gpt-4o-mini` | Simple task, cheap model sufficient |
| Step-back generation | `gemini-1.5-flash` / `gpt-4o-mini` | Simple task |
| Self-ask decisions | `gemini-1.5-flash` / `gpt-4o-mini` | Binary decision |
| Final answer | `gemini-1.5-pro` / `gpt-4o` / `claude-sonnet` | Quality matters here |
| Reranking | Local cross-encoder | No API cost |

**Implementation tip**: Pass different client instances for different operations:

```python
class TieredRAGEngine:
    """RAG engine using model tiering for cost optimization."""
    
    def __init__(self, cheap_client, expensive_client, vector_store):
        """
        Initialize with two LLM clients.
        
        Args:
            cheap_client: Fast/cheap model for simple tasks
            expensive_client: Quality model for final generation
            vector_store: Vector database
        """
        self.cheap = cheap_client
        self.expensive = expensive_client
        self.vector_store = vector_store
    
    def answer(self, question: str) -> str:
        """
        Answer question using tiered models.
        
        Args:
            question: User question
        
        Returns:
            Answer string
        """
        # Use cheap model for decomposition
        decomp_prompt = f'Break into search queries: "{question}"'
        queries = self.cheap.generate_content(decomp_prompt).text.split('\n')
        
        # Retrieve context
        context = []
        for q in queries[:3]:
            results = self.vector_store.query(query_texts=[q.strip()], n_results=3)
            context.extend(results['documents'][0])
        
        # Use expensive model for final answer
        final_prompt = f"""Answer: {question}

Context:
{chr(10).join(context)}"""
        
        return self.expensive.generate_content(final_prompt).text
```

## Evaluation Framework
- status: active
- type: plan
- id: rags-agent.evaluation
<!-- content -->
Measure RAG performance to guide optimization efforts.

### Key Metrics
- status: active
- type: guideline
- id: rags-agent.evaluation.metrics
<!-- content -->
Track these metrics to evaluate RAG quality:

| Metric | What It Measures | How to Compute |
|:-------|:-----------------|:---------------|
| **Retrieval Recall** | % of relevant docs retrieved | Manual annotation of test set |
| **Retrieval Precision** | % of retrieved docs that are relevant | Manual annotation |
| **Answer Correctness** | Is the final answer correct? | Compare to gold answers |
| **Faithfulness** | Is the answer grounded in context? | Check claims against retrieved docs |
| **Latency** | End-to-end response time | Timing measurement |
| **Cost per Query** | API costs per query | Sum of LLM calls × token prices |

### Simple Evaluation Script
- status: active
- type: task
- id: rags-agent.evaluation.script
- priority: low
- estimate: 1h
<!-- content -->
```python
"""
Simple RAG evaluation framework.

Create a test set of questions with expected answers,
then measure how well your RAG system performs.
"""

import json
import time
from typing import Callable
from dataclasses import dataclass

@dataclass
class TestCase:
    """A single test case for RAG evaluation."""
    question: str
    expected_answer: str
    relevant_doc_ids: list[str]  # IDs of docs that should be retrieved

@dataclass  
class EvalResult:
    """Results from evaluating a single test case."""
    question: str
    retrieved_ids: list[str]
    generated_answer: str
    retrieval_recall: float
    retrieval_precision: float
    answer_correct: bool  # Requires manual check or LLM judge
    latency_ms: float


def evaluate_rag(
    test_cases: list[TestCase],
    rag_function: Callable[[str], tuple[str, list[str]]],  # Returns (answer, retrieved_ids)
    judge_function: Callable[[str, str, str], bool] = None  # (question, expected, actual) -> correct
) -> list[EvalResult]:
    """
    Evaluate a RAG system on a test set.
    
    Args:
        test_cases: List of test cases
        rag_function: RAG system to evaluate
        judge_function: Optional LLM judge for correctness
    
    Returns:
        List of evaluation results
    """
    results = []
    
    for tc in test_cases:
        start = time.time()
        answer, retrieved_ids = rag_function(tc.question)
        latency = (time.time() - start) * 1000
        
        # Compute retrieval metrics
        retrieved_set = set(retrieved_ids)
        relevant_set = set(tc.relevant_doc_ids)
        
        true_positives = len(retrieved_set & relevant_set)
        recall = true_positives / len(relevant_set) if relevant_set else 1.0
        precision = true_positives / len(retrieved_set) if retrieved_set else 0.0
        
        # Judge answer correctness
        correct = False
        if judge_function:
            correct = judge_function(tc.question, tc.expected_answer, answer)
        
        results.append(EvalResult(
            question=tc.question,
            retrieved_ids=retrieved_ids,
            generated_answer=answer,
            retrieval_recall=recall,
            retrieval_precision=precision,
            answer_correct=correct,
            latency_ms=latency
        ))
    
    return results


def print_eval_summary(results: list[EvalResult]) -> None:
    """Print summary statistics from evaluation."""
    n = len(results)
    
    avg_recall = sum(r.retrieval_recall for r in results) / n
    avg_precision = sum(r.retrieval_precision for r in results) / n
    avg_latency = sum(r.latency_ms for r in results) / n
    accuracy = sum(r.answer_correct for r in results) / n
    
    print(f"=== RAG Evaluation Summary ({n} test cases) ===")
    print(f"Retrieval Recall:    {avg_recall:.2%}")
    print(f"Retrieval Precision: {avg_precision:.2%}")
    print(f"Answer Accuracy:     {accuracy:.2%}")
    print(f"Avg Latency:         {avg_latency:.0f}ms")
```

## Quick Reference
- status: active
- type: guideline
- id: rags-agent.quickref
<!-- content -->
Decision matrix for choosing improvements:

| If You Have... | Try First | Then Try |
|:---------------|:----------|:---------|
| Bad recall (missing relevant docs) | Query Decomposition | Hybrid Search |
| Bad precision (too much noise) | Reranking | Reduce top-k |
| Multi-part questions | Query Decomposition | Self-Ask |
| Specific terminology | Hybrid Search | Better chunking |
| Hallucinations | Verify-Then-Answer | Stronger grounding prompt |
| High costs | Caching, Model Tiering | Reduce iterations |
| Structured data | MCP Tools | Lightweight Tool Runner |
| Poor entity matching | Hybrid Search | Metadata Filtering |
| Redundant results | MMR | Increase diversity |
| Date/time queries | MCP Tools | Metadata Filtering |
| Enumeration queries | MCP Tools | Direct JSON access |

**Cost-quality tradeoffs**:

| Strategy | Quality Gain | Cost Increase |
|:---------|:-------------|:--------------|
| Query Decomposition | +15-25% recall | +5-10% |
| Step-Back Prompting | +10-20% recall | +5-10% |
| Hybrid Search | +10-15% recall | +0% (compute only) |
| Reranking | +10-20% precision | +0% (local model) |
| Metadata Filtering | Varies by use case | +0-5% (if using LLM extraction) |
| Self-Ask (2 iter) | +20-30% complex Q | +30-50% |
| MCP Tools | +25-40% structured | +30-50% |
| RAG + MCP Hybrid | +30-50% mixed queries | +40-60% |
| Caching | - | -20-50% |
| Model Tiering | - | -30-60% |
