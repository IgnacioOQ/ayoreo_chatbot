# Token Optimization Skill
- id: tokenopt_skill
- status: active
- type: agent_skill
- last_checked: 2026-03-02
- label: [agent, guide, core]
<!-- content -->
This document outlines critical guardrails and techniques that all AI Agents operating on this repository must enforce when designing prompts, building API payloads, or writing automation scripts. Due to the high volume of text data processed in this project (e.g., hundreds of parsed semantic chapters), inefficient token usage can result in catastrophic API cost overruns.

Token optimization operates across three dimensions: **input tokens** (what you send), **output tokens** (what the model generates), and **infrastructure** (how you route, cache, and batch). Every script touching the `google.genai` SDK must address all three.

## Core Optimization Principles
- id: tokenopt_skill.core_optimization_principles
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
When writing Python scripts that invoke `google.genai` or when formulating prompts, agents must adhere to the following rules:

### 1. Payload Minification (JSON Serialization)
- id: tokenopt_skill.core_optimization_principles.payload_minification
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: Never inject "pretty-printed" JSON or heavily formatted dictionaries into an LLM prompt.

**Why**: Formatting parameters like `indent=2` or `indent=4` inject thousands of meaningless space characters, tabs, and newlines into the prompt. LLMs tokenize these whitespace characters, artificially inflating the context window and the resulting cost by 20% to 30%.

**Implementation**: Always serialize datasets using `separators=(',', ':')` before injection.

*Bad Example (High Token Cost):*
```python
# BAD: Pretty-printed JSON wastes tokens on whitespace
prompt = f"Align this data:\n{json.dumps(data, indent=2)}"
```

*Good Example (Token Optimized):*
```python
# GOOD: Compact serialization strips all unnecessary whitespace
prompt = f"Align this data:\n{json.dumps(data, separators=(',', ':'))}"
```

**Additional Minification Rules**:
- When injecting lists of strings, prefer comma-separated values over JSON arrays when the model does not need to parse structure. Example: `"Items: alpha,beta,gamma"` instead of `'Items: ["alpha", "beta", "gamma"]'`.
- For tabular data destined for an LLM prompt, prefer CSV or TSV format over JSON. CSV can reduce token consumption by 40% to 50% compared to equivalent JSON for the same records.
- Strip `null` or empty fields from JSON objects before injection. Keys with no meaningful value still consume tokens.

### 2. Model Selection (Cost-to-Reasoning Ratio)
- id: tokenopt_skill.core_optimization_principles.model_selection
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: Default to lightweight, fast models (e.g., `gemini-2.5-flash`) for structural parsing, metadata extraction, semantic mapping, and data formatting.

**Why**: Reasoning models like `gemini-2.5-pro` cost significantly more (often 10x to 15x higher per million tokens). Structural alignment tasks (like zipping arrays or mapping known entities) do not require deep logical reasoning or world knowledge.

**Implementation**: Reserve `pro` models *only* for deep creative tasks, complex philosophical translation inference, or abstract architectural planning. For batch processing over the `bible.json` or `ayoreoorg.json` datasets, `flash` is mandatory.

**Model Routing Decision Table**:

| Task Type | Recommended Model | Rationale |
| :--- | :--- | :--- |
| Structural parsing / JSON alignment | `gemini-2.5-flash` | No deep reasoning needed |
| Metadata extraction / classification | `gemini-2.5-flash` | Pattern matching is sufficient |
| Semantic mapping / entity alignment | `gemini-2.5-flash` | Well within flash capabilities |
| Conversation titles / simple labels | `gemini-2.5-flash` (or `-lite`) | Minimal output, trivial task |
| Complex translation inference | `gemini-2.5-pro` | Requires nuance and world knowledge |
| Abstract architectural planning | `gemini-2.5-pro` | Benefits from deep reasoning |
| Creative writing / philosophical analysis | `gemini-2.5-pro` | Quality-sensitive, low volume |

**Thinking Budget Control**: When using reasoning models, set `thinking_level` (or legacy `thinking_budget`) to control how many tokens the model spends on internal chain-of-thought. For straightforward tasks on a `pro` model, set it to `"minimal"` or a low token budget. Only use `"high"` for genuinely complex multi-step reasoning.

```python
# GOOD: Constrain thinking tokens when using a reasoning model for a simpler task
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=prompt,
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_level="MINIMAL"  # Options: MINIMAL, LOW, MEDIUM, HIGH
        )
    )
)
```

### 3. Prompt Verbosity
- id: tokenopt_skill.core_optimization_principles.prompt_verbosity
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: Eliminate conversational filler from `SYSTEM_PROMPT` strings inside scripts.

**Why**: Instructing the model with "Please take a look at the following data and tell me what you think..." adds redundant tokens.

**Implementation**: Be highly directive. Use protocols (e.g., "Extract X. Output Y.").

**Prompt Compression Checklist**:
- Remove politeness tokens ("please", "kindly", "could you", "I would like you to").
- Remove hedging language ("perhaps", "maybe", "if possible", "try to").
- Collapse multi-sentence instructions into imperative commands.
- Use abbreviations and shorthand the model understands (e.g., "lang" for "language", "fmt" for "format").
- Never repeat the same instruction in different words for emphasis within a system prompt.

*Bad Example (Verbose):*
```python
SYSTEM_PROMPT = """
Please carefully analyze the following data structure. I would like you
to look at each entry and determine if the semantic alignment is correct.
If you find any issues, please describe them in detail. Try to be as
thorough as possible in your analysis.
"""
```

*Good Example (Directive):*
```python
SYSTEM_PROMPT = (
    "For each entry: verify semantic alignment. "
    "Output: {index, status: ok|mismatch, note: <reason if mismatch>}."
)
```

### 4. Output Token Control
- id: tokenopt_skill.core_optimization_principles.output_token_control
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: Always set `max_output_tokens` to the minimum value that covers your expected response size. Never leave it at the default.

**Why**: Output tokens are typically 3x to 5x more expensive than input tokens. An unconstrained model may generate verbose explanations, preambles, or markdown formatting that you never use. Excess output tokens are the single largest source of hidden cost.

**Implementation**:
- For classification tasks (returning a label or short JSON): set `max_output_tokens` between 64 and 256.
- For structured extraction (returning a known schema): estimate the JSON character count, divide by 3.5 (avg chars per token), and add a 30% buffer.
- For generative tasks (translation, summaries): benchmark a sample of 10 responses to find the 95th-percentile token count, use that as your cap.

```python
# GOOD: Cap output for a classification task
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        max_output_tokens=128  # Classification label + short JSON
    )
)
```

**Instruct the model to be concise in the prompt itself**: Pair `max_output_tokens` with an explicit instruction like `"Respond with JSON only. No preamble."` to prevent the model from wasting output tokens on natural-language wrapping.

### 5. Structured Output Schemas
- id: tokenopt_skill.core_optimization_principles.structured_output
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: When you expect JSON or structured data back, use the API's native structured output mode (`response_mime_type` + `response_json_schema`) instead of asking the model in prose to return JSON.

**Why**: Native structured output eliminates wasted tokens on markdown fences, preambles ("Here is the JSON..."), and malformed responses that require retries. It also enforces the schema server-side, preventing hallucinated fields.

**Implementation**:
```python
from pydantic import BaseModel
from typing import List

# Define the expected output schema with Pydantic
class AlignmentResult(BaseModel):
    index: int
    status: str  # "ok" or "mismatch"
    note: str

class AlignmentResponse(BaseModel):
    results: List[AlignmentResult]

# Use structured output mode
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=AlignmentResponse.model_json_schema()
    )
)

# Parse directly — no regex, no cleanup
data = AlignmentResponse.model_validate_json(response.text)
```

**Benefits**: Eliminates retry loops caused by malformed JSON. Reduces output tokens by removing prose wrapping. Makes downstream parsing deterministic.

## Data Preparation Techniques
- id: tokenopt_skill.data_preparation
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
Before data reaches a prompt, it should be preprocessed to minimize token footprint.

### 6. Field Pruning and Flattening
- id: tokenopt_skill.data_preparation.field_pruning
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: Only include fields in the prompt payload that the model actually needs for the task. Strip all metadata, internal IDs, timestamps, and nested structures that are irrelevant.

**Why**: Deeply nested JSON creates significant overhead from repeated keys and braces. Flattening a 3-level nested object to a flat record can reduce token count by 50% to 70%.

**Implementation**:
```python
# BAD: Sending the full record with irrelevant fields
record = {
    "id": "abc-123",
    "created_at": "2026-01-15T10:30:00Z",
    "updated_at": "2026-02-28T14:22:00Z",
    "metadata": {"source": "api", "version": 3},
    "content": {"book": "Genesis", "chapter": 1, "verse": 1, "text_es": "...", "text_ayo": "..."}
}

# GOOD: Extract only what the model needs
record_slim = {
    "book": "Genesis",
    "ch": 1,
    "v": 1,
    "es": "...",
    "ayo": "..."
}
```

- Use short key names in prompt payloads (e.g., `"es"` instead of `"spanish_text"`, `"ch"` instead of `"chapter_number"`). The model understands context from the system prompt.
- For repeated structures (e.g., 530 chapters), even saving 5 tokens per record saves 2,650 tokens per batch.

### 7. Numerical Precision Reduction
- id: tokenopt_skill.data_preparation.precision_reduction
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: Round floating-point numbers to the minimum precision required for the task before injecting them into prompts.

**Why**: A number like `0.8734521` tokenizes into more tokens than `0.87`. Across thousands of records, precision-aware formatting can reduce numerical token consumption by 30% to 40%.

**Implementation**:
```python
# Round scores/probabilities to 2 decimal places
data["score"] = round(data["score"], 2)

# For integer-safe values, cast to int
data["count"] = int(data["count"])
```

### 8. Format Selection by Task
- id: tokenopt_skill.data_preparation.format_selection
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: Choose the most token-efficient serialization format for the data type being sent.

**Format Efficiency Ranking** (most to least efficient for tabular data):
1. **CSV/TSV** — Best for homogeneous tabular data. ~40-50% fewer tokens than JSON.
2. **Compact JSON** (`separators=(',',':')`) — Best for heterogeneous or nested data.
3. **YAML** — Slightly less overhead than pretty JSON, but still verbose.
4. **Pretty JSON** (`indent=2`) — **Never use in prompts.**

```python
import csv
import io

# GOOD: Convert records to CSV for the prompt
def records_to_csv(records: list[dict]) -> str:
    """Convert a list of dicts to a compact CSV string for prompt injection."""
    if not records:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=records[0].keys())
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue().strip()

prompt = f"Align the following verses:\n{records_to_csv(slim_records)}"
```

## Infrastructure Optimization
- id: tokenopt_skill.infrastructure
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
Beyond prompt-level optimization, infrastructure-level strategies can yield dramatic cost reductions by avoiding redundant computation entirely.

### 9. Context Caching
- id: tokenopt_skill.infrastructure.context_caching
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: When the same large context (system instructions, reference documents, datasets) is reused across multiple API calls, use Gemini's explicit context caching to avoid re-sending and re-processing those tokens.

**Why**: Cached tokens cost only 10% of standard input token price on Gemini 2.5+ models (a 90% discount). For a workflow that sends the same 50,000-token reference document with 100 different queries, caching saves ~4.5 million redundant input tokens.

**When to Use**:
- The shared context exceeds the minimum token threshold (check model docs; typically 4,096+ tokens for Gemini 2.5 models).
- You are making multiple queries against the same reference data (e.g., bible.json, ayoreoorg.json).
- The reference data does not change between calls.

**Implementation**:
```python
from google import genai
from google.genai import types

client = genai.Client()

# Step 1: Create the cache with the large static context
cache = client.caches.create(
    model="gemini-2.5-flash",
    config=types.CreateCachedContentConfig(
        display_name="bible_reference_cache",
        system_instruction="You are a semantic alignment expert for biblical texts.",
        contents=[large_reference_json],  # The big payload — sent once
        ttl="3600s"  # Cache lives for 1 hour
    )
)

# Step 2: Make multiple queries referencing the cache
for query in alignment_queries:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=query,
        config=types.GenerateContentConfig(
            cached_content=cache.name  # Tokens are NOT re-sent or re-billed
        )
    )
```

**Cache Lifecycle Management**:
- Set TTL to match your processing window. For a batch run that takes ~30 minutes, a 1-hour TTL is safe.
- Wrap cache usage in try/except to handle 404 errors from expired caches.
- Implicit caching is enabled by default on Gemini 2.5+ models and provides automatic savings when prompts share a common prefix. Place static content (system instructions, reference data) at the **beginning** of the prompt to maximize implicit cache hits.

### 10. Batch API
- id: tokenopt_skill.infrastructure.batch_api
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: For non-latency-critical workloads (dataset processing, evaluations, bulk generation), use the Gemini Batch API instead of synchronous calls.

**Why**: Batch API is priced at 50% of the standard interactive API cost. Combined with implicit caching within batches, savings can compound significantly. It also provides higher rate limits and eliminates the need for client-side queuing or retry logic.

**When to Use**:
- Processing the full `bible.json` or `ayoreoorg.json` datasets.
- Running evaluations or quality checks over many records.
- Any task where results are not needed in real-time.

**Implementation**:
```python
import json

# Step 1: Prepare a JSONL file with all requests
requests = []
for i, chapter in enumerate(chapters):
    requests.append({
        "key": f"chapter_{i}",
        "request": {
            "contents": [{"parts": [{"text": build_prompt(chapter)}]}],
            "generationConfig": {
                "maxOutputTokens": 256,
                "responseMimeType": "application/json"
            }
        }
    })

with open("batch_requests.jsonl", "w") as f:
    for req in requests:
        f.write(json.dumps(req, separators=(',', ':')) + "\n")

# Step 2: Upload and submit the batch job
uploaded = client.files.upload(file="batch_requests.jsonl")
batch_job = client.batches.create(
    model="gemini-2.5-flash",
    src=uploaded.name,
    config={"display_name": "semantic_alignment_batch"}
)

# Step 3: Poll and retrieve results (within 24h, often much faster)
```

**Batch + Cache Synergy**: Context caching works within batch requests. If all requests in a batch share a common prefix (e.g., the same system prompt and reference data), implicit caching triggers automatically, stacking the 90% cache discount on top of the 50% batch discount.

### 11. Local Response Caching
- id: tokenopt_skill.infrastructure.local_caching
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: Cache API responses locally (file-based or in-memory) to prevent re-processing identical inputs during development, debugging, or re-runs.

**Why**: During development, scripts are often run multiple times against the same data. Without local caching, every re-run sends the same tokens and incurs the same cost. A simple hash-based file cache eliminates this entirely.

**Implementation**:
```python
import hashlib
import json
import os

CACHE_DIR = ".llm_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cached_or_call(prompt: str, model: str, call_fn) -> str:
    """
    Check local file cache before making an API call.
    Returns cached response if available, otherwise calls the API and caches the result.
    """
    # Create a unique hash from the prompt + model combination
    cache_key = hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.json")

    # Return cached result if it exists
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            return json.load(f)["response"]

    # Otherwise, make the API call
    response = call_fn(prompt, model)

    # Cache the result for future runs
    with open(cache_path, "w") as f:
        json.dump({"prompt_hash": cache_key, "response": response}, f)

    return response
```

**When to Invalidate**: Clear the cache directory when the prompt template changes, the model version is updated, or the underlying data is modified.

### 12. Semantic Caching (Vector-Based)
- id: tokenopt_skill.infrastructure.semantic_caching
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: For user-facing or RAG-based workflows where different users ask semantically equivalent questions in different words, implement a semantic cache that matches queries by meaning (vector similarity) rather than by exact string.

**Why**: Local hash-based caching (Rule #11) only catches *identical* prompts. But in practice, queries like `"What does Genesis 1:1 say in Ayoreo?"` and `"Translate the first verse of Genesis to Ayoreo"` have the same intent and should return the same cached response. A semantic cache converts queries into vector embeddings and uses cosine similarity to find matches, eliminating redundant LLM calls even when the wording varies. Production systems report cache hit rates of 50% to 67% on real workloads, with latency dropping from seconds to milliseconds on hits.

**Architecture**: A semantic cache consists of three components:
1. **Embedding Model** — Converts text queries into dense vector representations. Use a lightweight local model (e.g., `sentence-transformers/all-MiniLM-L6-v2`) to avoid adding API cost on every cache lookup. Avoid using the LLM itself as the embedding model — the computational overhead defeats the purpose.
2. **Vector Store** — Stores embeddings and performs approximate nearest-neighbor (ANN) search. Options range from in-process (FAISS) to hosted (Qdrant, pgvector, Milvus, ChromaDB).
3. **Similarity Threshold** — A cosine similarity cutoff (typically 0.90 to 0.95) that determines whether a match is "close enough" to serve from cache.

**When to Use**:
- RAG pipelines where users ask overlapping questions against the same knowledge base.
- Chatbot or API endpoints with repetitive query patterns.
- Translation lookups where the same source verse may be requested in varied phrasing.

**When NOT to Use**:
- Batch processing scripts with unique, non-repeating prompts (use local hash caching instead).
- Tasks where the response must reflect real-time or constantly changing data.
- Contexts where even slight semantic drift could produce an incorrect answer (e.g., distinguishing "Genesis 1:1" from "Genesis 1:2").

**Implementation (Lightweight — FAISS + sentence-transformers)**:
```python
import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer

# --- Configuration ---
SIMILARITY_THRESHOLD = 0.92  # Cosine similarity cutoff for cache hits
CACHE_FILE = ".semantic_cache/cache_store.json"
INDEX_FILE = ".semantic_cache/embeddings.npy"

class SemanticCache:
    """
    A lightweight semantic cache using sentence-transformers for embeddings
    and numpy for cosine similarity search. No external vector DB required.
    Suitable for small-to-medium caches (< 100k entries).
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        threshold: float = SIMILARITY_THRESHOLD
    ):
        # Load a small, fast embedding model (~80MB, runs on CPU)
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
        self.entries = []       # List of {"query": str, "response": str}
        self.embeddings = None  # numpy array of shape (n, dim)
        self._load_cache()

    def _load_cache(self):
        """Load persisted cache from disk if available."""
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        if os.path.exists(CACHE_FILE) and os.path.exists(INDEX_FILE):
            with open(CACHE_FILE, "r") as f:
                self.entries = json.load(f)
            self.embeddings = np.load(INDEX_FILE)

    def _save_cache(self):
        """Persist cache to disk after updates."""
        with open(CACHE_FILE, "w") as f:
            json.dump(self.entries, f, separators=(',', ':'))
        if self.embeddings is not None:
            np.save(INDEX_FILE, self.embeddings)

    def _cosine_similarity(self, query_emb: np.ndarray) -> np.ndarray:
        """Compute cosine similarity between a query and all cached embeddings."""
        if self.embeddings is None or len(self.embeddings) == 0:
            return np.array([])
        # Normalize for cosine similarity
        query_norm = query_emb / np.linalg.norm(query_emb)
        cache_norms = self.embeddings / np.linalg.norm(
            self.embeddings, axis=1, keepdims=True
        )
        return cache_norms @ query_norm

    def get(self, query: str) -> str | None:
        """
        Look up a semantically similar query in the cache.
        Returns the cached response if similarity >= threshold, else None.
        """
        query_emb = self.model.encode(query, convert_to_numpy=True)
        similarities = self._cosine_similarity(query_emb)

        if len(similarities) == 0:
            return None

        best_idx = int(np.argmax(similarities))
        best_score = similarities[best_idx]

        if best_score >= self.threshold:
            return self.entries[best_idx]["response"]

        return None

    def set(self, query: str, response: str):
        """
        Store a new query-response pair in the cache.
        Call this after a successful LLM call on a cache miss.
        """
        query_emb = self.model.encode(query, convert_to_numpy=True)

        self.entries.append({"query": query, "response": response})

        if self.embeddings is None:
            self.embeddings = query_emb.reshape(1, -1)
        else:
            self.embeddings = np.vstack([self.embeddings, query_emb])

        self._save_cache()

    def clear(self):
        """Invalidate the entire cache."""
        self.entries = []
        self.embeddings = None
        self._save_cache()
```

**Usage Pattern**:
```python
# Initialize the cache (loads from disk if previously saved)
cache = SemanticCache(threshold=0.92)

def query_with_semantic_cache(query: str, llm_call_fn) -> str:
    """
    Check semantic cache before calling the LLM.
    On miss, call the LLM and store the result for future hits.
    """
    # Step 1: Check cache
    cached = cache.get(query)
    if cached is not None:
        logger.info(f"SEMANTIC CACHE HIT for: {query[:80]}")
        return cached

    # Step 2: Cache miss — call the LLM
    logger.info(f"SEMANTIC CACHE MISS for: {query[:80]}")
    response = llm_call_fn(query)

    # Step 3: Store for future hits
    cache.set(query, response)
    return response
```

**Threshold Tuning Guide**:
- **0.95+** — Very strict. Low false-positive risk, but many near-duplicates will miss. Good for high-stakes tasks (translation, legal).
- **0.90–0.95** — Balanced. Recommended starting range. Monitor for false positives.
- **0.85–0.90** — Aggressive. Higher hit rate but increased risk of serving semantically "close but wrong" responses. Only suitable for FAQ-style tasks with broad answers.
- **Below 0.85** — Not recommended. False-positive rate becomes unacceptable.

Start at 0.92, log all cache hits with their similarity scores, and review hits below 0.95 manually during the first week. Adjust based on observed accuracy.

**Scaling Considerations**:
- For caches under ~50k entries, the numpy-based approach above is fast enough (sub-millisecond search).
- For caches over 50k entries, switch to FAISS (`faiss.IndexFlatIP`) for efficient ANN search, or use a hosted vector database (Qdrant, pgvector, ChromaDB).
- Embedding overhead is ~5-20ms per query using a local model on CPU. This is negligible compared to the 1-5 seconds saved by avoiding an LLM call.

**Cache Invalidation Strategy**:
- **TTL-based**: Expire entries after a configurable time window (e.g., 7 days for static reference data like biblical translations).
- **Version-based**: Clear the cache when the underlying dataset or prompt template changes (same as Rule #11).
- **Selective**: If a specific translation is corrected, remove only the affected entries rather than clearing the entire cache.

## Prompt Architecture Patterns
- id: tokenopt_skill.prompt_architecture
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
How you structure multi-turn and multi-step workflows has a direct impact on cumulative token cost.

### 13. Conversation History Compression
- id: tokenopt_skill.prompt_architecture.conversation_compression
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: In multi-turn workflows, compress or summarize prior conversation turns instead of sending the full raw history with every request.

**Why**: Token cost scales linearly with conversation length. A 20-turn conversation where each turn averages 500 tokens means the 20th request sends ~10,000 tokens of history — most of which is redundant context. Summarizing prior turns into a compact state object keeps the context window lean.

**Implementation**:
```python
def compress_history(turns: list[dict], max_recent: int = 3) -> str:
    """
    Keep the last N turns verbatim and summarize older turns
    into a compact state description.
    """
    if len(turns) <= max_recent:
        return json.dumps(turns, separators=(',', ':'))

    # Summarize old turns into key decisions/outcomes
    old_summary = summarize_turns(turns[:-max_recent])  # Use a cheap model for this
    recent = turns[-max_recent:]

    return json.dumps(
        {"prior_context": old_summary, "recent_turns": recent},
        separators=(',', ':')
    )
```

### 14. Chunking Strategy for Large Datasets
- id: tokenopt_skill.prompt_architecture.chunking_strategy
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: When processing datasets that exceed the context window, use semantic chunking rather than arbitrary fixed-size splits.

**Why**: Fixed-size chunking (e.g., "every 50 records") often splits semantically related records across chunks, forcing the model to re-process context or miss cross-references. Semantic chunking groups related records (e.g., by book, chapter, or topic), preserving coherence and reducing the need for overlap tokens between chunks.

**Implementation**:
```python
def chunk_by_book(records: list[dict]) -> list[list[dict]]:
    """
    Group records by their 'book' field for semantic coherence.
    Each chunk stays within the token budget.
    """
    from itertools import groupby

    chunks = []
    for book, group in groupby(records, key=lambda r: r["book"]):
        book_records = list(group)
        # Further split if a single book exceeds the token budget
        if estimate_tokens(book_records) > TOKEN_BUDGET:
            chunks.extend(split_within_budget(book_records, TOKEN_BUDGET))
        else:
            chunks.append(book_records)
    return chunks
```

**Token Budget Estimation**: Use the approximation of ~3.5 characters per token for English text and ~4 characters per token for Spanish. For Ayoreo text, benchmark a sample to establish the ratio since low-resource languages may tokenize differently.

### 15. Tool and Instruction Pruning
- id: tokenopt_skill.prompt_architecture.tool_pruning
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: When using function calling or tool definitions, include only the tools relevant to the current task in each request. Do not pass the full tool registry every time.

**Why**: Every tool definition (name, description, parameter schema) gets tokenized as part of the input. If you define 20 tools but only 2 are relevant to the current query, you are paying for 18 unused tool descriptions on every call. For complex schemas, this overhead can be 500+ tokens per unused tool.

**Implementation**:
```python
# BAD: Sending all tools every time
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=ALL_TOOLS  # 20 tools, only 2 are relevant
    )
)

# GOOD: Filter tools by task context
relevant_tools = select_tools_for_task(task_type, ALL_TOOLS)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=relevant_tools  # Only the 2 relevant tools
    )
)
```

Similarly, conditionally include system prompt sections. If a section like "When using the translation tool..." is only relevant when the translation tool is active, do not include it in requests that do not involve translation.

## Monitoring and Cost Tracking
- id: tokenopt_skill.monitoring
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
What gets measured gets optimized. Every script that calls the API must track token usage.

### 16. Response Metadata Logging
- id: tokenopt_skill.monitoring.response_metadata
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: After every API call, log the `usage_metadata` from the response. Track input tokens, output tokens, cached tokens, and total tokens over time.

**Why**: Without logging, cost overruns are invisible until the invoice arrives. Token logs allow you to detect regressions (e.g., a prompt change that doubled token usage), track cache hit rates, and validate that optimizations are working.

**Implementation**:
```python
import logging

logger = logging.getLogger("token_tracker")

def log_token_usage(response, task_name: str):
    """
    Extract and log token usage from a Gemini API response.
    Call this after every generate_content invocation.
    """
    meta = response.usage_metadata
    logger.info(
        f"[{task_name}] "
        f"input={meta.prompt_token_count} "
        f"output={meta.candidates_token_count} "
        f"cached={getattr(meta, 'cached_content_token_count', 0)} "
        f"total={meta.total_token_count}"
    )
    return {
        "task": task_name,
        "input_tokens": meta.prompt_token_count,
        "output_tokens": meta.candidates_token_count,
        "cached_tokens": getattr(meta, 'cached_content_token_count', 0),
        "total_tokens": meta.total_token_count
    }
```

### 17. Pre-Flight Token Estimation
- id: tokenopt_skill.monitoring.preflight_estimation
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: Before submitting a large batch or expensive request, estimate the total token cost and log a warning if it exceeds a configurable threshold.

**Why**: A single misconfigured batch run can consume millions of tokens. A pre-flight check acts as a circuit breaker.

**Implementation**:
```python
# Token estimation constants (approximate)
CHARS_PER_TOKEN = 3.5  # English average; adjust per language
COST_PER_M_INPUT = 0.075   # Gemini 2.5 Flash input ($/M tokens)
COST_PER_M_OUTPUT = 0.30   # Gemini 2.5 Flash output ($/M tokens)
COST_THRESHOLD_USD = 1.00  # Alert threshold

def estimate_batch_cost(
    prompts: list[str],
    avg_output_tokens: int = 200
) -> dict:
    """
    Estimate the total cost of a batch before submission.
    Raises a warning if cost exceeds the threshold.
    """
    total_input_chars = sum(len(p) for p in prompts)
    est_input_tokens = total_input_chars / CHARS_PER_TOKEN
    est_output_tokens = len(prompts) * avg_output_tokens

    est_cost = (
        (est_input_tokens / 1_000_000) * COST_PER_M_INPUT +
        (est_output_tokens / 1_000_000) * COST_PER_M_OUTPUT
    )

    result = {
        "num_requests": len(prompts),
        "est_input_tokens": int(est_input_tokens),
        "est_output_tokens": int(est_output_tokens),
        "est_cost_usd": round(est_cost, 4)
    }

    if est_cost > COST_THRESHOLD_USD:
        logger.warning(
            f"COST ALERT: Estimated batch cost ${est_cost:.2f} "
            f"exceeds threshold ${COST_THRESHOLD_USD:.2f}. "
            f"Review before submitting."
        )

    return result
```

## Error Handling and Retry Economy
- id: tokenopt_skill.error_handling
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
Failed requests waste tokens. Retries multiply that waste. Defensive coding prevents both.

### 18. Retry Strategies
- id: tokenopt_skill.error_handling.retry_strategies
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: Use exponential backoff with a maximum retry count. Never use infinite retry loops. On persistent failures, log the failing input and skip rather than burning tokens on a prompt the model cannot handle.

**Why**: A malformed prompt that triggers a 400 error will fail on every retry. Rate-limit errors (429) benefit from backoff, but content errors do not. Distinguishing between retryable and non-retryable errors prevents token waste.

**Implementation**:
```python
import time

def call_with_retry(
    call_fn,
    prompt: str,
    max_retries: int = 3,
    base_delay: float = 1.0
) -> str | None:
    """
    Retry with exponential backoff for transient errors only.
    Non-retryable errors are logged and skipped immediately.
    """
    for attempt in range(max_retries):
        try:
            return call_fn(prompt)
        except Exception as e:
            error_code = getattr(e, 'code', None)

            # Non-retryable: bad request, invalid content, etc.
            if error_code in (400, 403):
                logger.error(f"Non-retryable error ({error_code}): {e}")
                return None

            # Retryable: rate limit, server error
            delay = base_delay * (2 ** attempt)
            logger.warning(
                f"Retryable error (attempt {attempt + 1}/{max_retries}): {e}. "
                f"Waiting {delay}s."
            )
            time.sleep(delay)

    logger.error(f"Max retries exceeded for prompt (first 100 chars): {prompt[:100]}")
    return None
```

### 19. Output Validation Before Re-Querying
- id: tokenopt_skill.error_handling.output_validation
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: Validate the model's output against the expected schema *before* deciding to retry. If using structured output mode, parsing failures are rare and usually indicate a prompt issue, not a transient error.

**Why**: Re-sending a prompt because the output "looked wrong" is the most expensive form of retry. Often the issue is in the prompt design, not the model's response. Fix the prompt, do not retry blindly.

**Implementation**:
```python
def validate_and_extract(response_text: str, schema_class) -> dict | None:
    """
    Attempt to parse the response against the expected Pydantic schema.
    Returns the parsed object or None if validation fails.
    """
    try:
        return schema_class.model_validate_json(response_text)
    except Exception as e:
        logger.warning(f"Schema validation failed: {e}")
        return None
```

## Quick Reference: Optimization Checklist
- id: tokenopt_skill.checklist
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
Before submitting any script that calls `google.genai`, verify every item:

**Input Tokens**:
- [ ] JSON serialized with `separators=(',', ':')`
- [ ] No `indent` parameter anywhere in prompt-bound `json.dumps`
- [ ] Only task-relevant fields included in the payload
- [ ] Short key names used in prompt payloads
- [ ] Null/empty fields stripped
- [ ] Numerical values rounded to required precision
- [ ] CSV/TSV used for tabular data where possible
- [ ] System prompt is directive, no filler
- [ ] Tool definitions filtered to relevant subset
- [ ] Static context placed at the beginning of the prompt (for implicit caching)

**Output Tokens**:
- [ ] `max_output_tokens` explicitly set to a reasonable cap
- [ ] Structured output mode (`response_mime_type` + schema) used where applicable
- [ ] Prompt instructs "JSON only. No preamble."
- [ ] Thinking budget constrained on reasoning models for simple tasks

**Infrastructure**:
- [ ] Explicit context caching used for repeated large contexts
- [ ] Batch API used for non-latency-critical bulk processing
- [ ] Local response cache prevents duplicate calls during development
- [ ] Semantic cache evaluated for user-facing / RAG endpoints with repetitive queries
- [ ] Similarity threshold tuned and cache hits monitored for false positives
- [ ] `usage_metadata` logged after every API call
- [ ] Pre-flight cost estimation runs before large batches
- [ ] Retry logic distinguishes retryable vs. non-retryable errors
- [ ] `gemini-2.5-flash` is the default model; `pro` requires justification

## Known Incidents
- id: tokenopt_skill.known_incidents
- status: active
- type: log
- last_checked: 2026-03-02
<!-- content -->
- **March 2026 Semantic Alignment Bloat**: The initial semantic matching scripts processed 530 biblical chapters using `json.dumps(..., indent=2)` and `gemini-2.5-pro`. This consumed 3.69 million tokens at a cost of ~$26. Swapping to `gemini-2.5-flash` and stripping JSON whitespace reduced the footprint to a few cents per run.
