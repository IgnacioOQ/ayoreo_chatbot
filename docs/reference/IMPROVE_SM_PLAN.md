# Plan: Improve Semantic Matching with Glossary Injection
- status: active
- type: plan
- created: 2026-03-24
<!-- content -->

## Problem

The current semantic matching in `scripts/align_mismatches_llm.py` gives the LLM raw EN and AYO text chunks with no vocabulary support. The LLM understands English natively (its anchor), but Ayoreo is completely opaque to it — it can only use proper nouns, numbers, and text-length heuristics to align chunks. This leads to alignment errors especially in stories where:
- Ayoreo chunks don't contain obvious proper nouns
- Chunk sizes are similar across a window, making length-matching ambiguous
- Cultural or ceremonial vocabulary appears in multiple places

**The fix:** Give the LLM a per-story AYO→EN mini-glossary at call time, so it can recognize Ayoreo words that appear in both the EN and AYO chunks and use them as anchors.

---

## Glossary: Current State

### Source 1 — Story-level glossaries (best source)
**Location:** `data/raw/ayoreoorg/aligned_ayoreoorg.json`, field `"glossary"` on each entry.
**Count:** 756 entries across 130 of 132 stories.
**Shape:**
```json
{"ayoreo": "Jnuruminone", "spanish": "pajei carubode (las cuerdas que se llevan alrededor de la cintura)"}
```
**Problem:** Spanish definitions only. No English. The alignment LLM uses English as anchor, so Spanish is not directly useful.

### Source 2 — Global processed glossary
**Location:** `data/processed/glossaries.json`
**Count:** 366 entries (deduplicated across all pages).
**Shape:**
```json
{"ayoreo": "Oidábiadé", "english": "", "source": "canciones-nativas___masthead"}
```
**Problem:** English field is **empty for all 366 entries**. The scraper only captured Spanish (the source pages are Spanish). This file is currently useless for EN-anchored alignment.

### Source 3 — Backup glossary (has Spanish)
**Location:** `data/processed_backup/glossaries.json`
**Shape:** `{"ayoreo": "...", "spanish": "...", "source": "..."}` — Spanish definitions present.

### Source 4 — Dictionary script (not yet run)
**Script:** `scripts/build_dictionary.py` — uses Gemini to clean glossary entries and add POS tags.
**Output:** `data/processed/dictionary_ayoreo_espanol.json` — **does not exist yet**.
**Problem:** Designed for Spanish output. Would need adaptation for English output.

### Summary Table

| Source | Count | AYO | EN | ES | Story-specific |
|--------|-------|-----|----|----|----------------|
| Story-level (`aligned_ayoreoorg.json`) | 756 | ✓ | ✗ | ✓ | ✓ |
| Global processed (`glossaries.json`) | 366 | ✓ | empty | ✗ | ✗ |
| Backup processed | 366 | ✓ | ✗ | ✓ | ✗ |

**Key insight:** The story-level glossaries (756 entries, all with Spanish) are the best raw material. They are contextually associated with the exact stories being aligned. We need to translate their Spanish definitions to English.

---

## Phase 1 — Build `glossary_ayo_en.json`

**Goal:** Produce a clean AYO→EN glossary file suitable for LLM injection.

### Step 1.1 — Extract and deduplicate all story-level glossaries

Write script `scripts/build_glossary_en.py` that:
1. Loads `data/raw/ayoreoorg/aligned_ayoreoorg.json`
2. Collects all `glossary` arrays from every story entry
3. Attaches `story_id` as source to each entry
4. Deduplicates by lowercase Ayoreo term (keep first occurrence + note all source story IDs)
5. Outputs an intermediate file: `data/processed/glossary_raw_es.json`

Expected shape:
```json
[
  {
    "ayoreo": "Jnuruminone",
    "spanish": "pajei carubode (las cuerdas que se llevan alrededor de la cintura)",
    "sources": ["creencias__creencias-al-pie-del-totem"]
  },
  ...
]
```

Expected count: ~400–500 unique Ayoreo terms after deduplication (from 756 raw entries).

### Step 1.2 — Translate Spanish definitions to English via Gemini

Extend `build_glossary_en.py` to batch-call Gemini Flash to translate each Spanish definition to English. Use structured output schema:

```python
class GlossaryEntry(BaseModel):
    ayoreo: str           # unchanged
    english: str          # translated definition
    pos_tag: str          # VERB, NOUN, ADJ, PHRASE, CULTURAL, OTHER
    is_valid: bool        # False if entry is a sentence/dialogue, not a word/phrase
```

**Prompt guidance for Gemini:**
- You are translating Ayoreo cultural glossary entries from Spanish to English.
- Preserve cultural specificity — do not oversimplify ceremonial or material-culture terms.
- `is_valid=False` for full narrative sentences (e.g. "Mi esposa dijo que..."). Valid entries are words, short phrases, or cultural terms (including multi-word compounds).
- For `pos_tag`, use `CULTURAL` for material culture items (tools, garments, ceremonies) that don't fit standard POS.

**Token efficiency:**
- Batch size: 40 entries per call (same as `build_dictionary.py`)
- Minify JSON: `json.dumps(..., separators=(',', ':'))`
- Estimated total: ~500 entries / 40 = 13 calls. Negligible cost.

### Step 1.3 — Save clean output

Output: `data/processed/glossary_ayo_en.json`

Final shape:
```json
[
  {
    "ayoreo": "jnuruminone",
    "english": "belt cords worn around the waist (pajei carubode)",
    "pos_tag": "CULTURAL",
    "sources": ["creencias__creencias-al-pie-del-totem"]
  },
  ...
]
```

Normalize Ayoreo key to lowercase for matching. Preserve original casing for display.

**Validation check after build:**
- Count valid entries (expect 350–450)
- Spot-check 10 random entries for translation quality
- Flag any entry where `len(english) < 3` (missed translation)

---

## Phase 2 — Inject Glossary into Semantic Matching

### Strategy: Per-story inline injection (no MCP, no vector search)

**Why inline over MCP/vector search:**
- The story-level glossaries are already associated with specific stories — no retrieval needed.
- Average story has ~5–10 glossary entries; even with the full global glossary, injection stays small.
- MCP adds latency and complexity for a problem that is solvable with ~100 extra tokens per call.
- Gemini Flash context window is large enough (1M tokens); injection overhead is negligible.

### Step 2.1 — Build per-story glossary lookup in `align_mismatches_llm.py`

At script startup, after loading the dataset, also load `glossary_ayo_en.json` and build an index:
```python
# Index by story_id for O(1) lookup
glossary_by_story: dict[str, list[dict]] = defaultdict(list)
for entry in glossary_ayo_en:
    for sid in entry["sources"]:
        glossary_by_story[sid].append(entry)
```

### Step 2.2 — Filter to relevant entries

Before injecting the glossary into the prompt, filter to entries where the Ayoreo term actually appears in the AYO chunks being aligned:

```python
def get_relevant_glossary(story_id: str, ayo_chunks: list[str]) -> list[dict]:
    ayo_text = " ".join(ayo_chunks).lower()
    candidates = glossary_by_story.get(story_id, [])
    return [g for g in candidates if g["ayoreo"].lower() in ayo_text]
```

This ensures we only send terms the LLM will actually encounter in the chunks. If the story has no specific glossary, fall back to scanning the global glossary for terms present in the AYO text (capped at 20 entries by frequency/length heuristic).

### Step 2.3 — Format and inject into user prompt

Update `_call_align_window()` to accept a `glossary` argument and append it to the prompt:

```python
def format_glossary(entries: list[dict]) -> str:
    if not entries:
        return ""
    items = "; ".join(f"{e['ayoreo']}={e['english']}" for e in entries)
    return f"\nGLOSS: {items}"
```

Updated prompt structure:
```python
prompt = (
    f"Story ID: {story_id} | EN indices 0-{n_en-1} ({n_en} items) | AYO indices 0-{n_ayo-1} ({n_ayo} items)"
    f"{format_glossary(relevant_glossary)}"
    f"\n\nEN: {json.dumps(en_slice, separators=(',', ':'), ensure_ascii=False)}"
    f"\nAYO: {json.dumps(ayo_slice, separators=(',', ':'), ensure_ascii=False)}"
)
```

### Step 2.4 — Update SYSTEM_PROMPT to explain glossary

Add a new rule to the system prompt in `align_mismatches_llm.py`:

```
8. Glossary (if present): The GLOSS line lists known Ayoreo word translations (ayoreo_term=english_meaning).
   Use these as additional anchors: if an Ayoreo chunk contains a glossed term and an English chunk
   references the same concept, that is strong evidence they align. Glossary anchors override length
   heuristics but still respect monotonicity.
```

### Step 2.5 — Update SEMANTIC_MATCHING.md

Add a new step to the Anchor Heuristic Protocol:

**Step 3b: Glossary Anchoring (when glossary is provided)**
- Between Steps 3 and 4, scan the GLOSS entries.
- For each glossed term found in an AYO chunk, look for the English meaning in EN chunks.
- Treat a glossary match as a high-confidence anchor (stronger than length heuristic, weaker than named-entity exact match).

---

## Phase 3 — Validation

After running the updated script on a subset of stories:

1. **Qualitative check** — Use `sanity_app.py` to visually inspect alignment results before/after on 10 stories known to have poor alignment.
2. **Coverage metric** — Track what % of alignment calls had at least 1 glossary entry injected.
3. **Token overhead** — Measure average token increase per call. Expected: +50–150 tokens per call (negligible vs. typical prompt size).

---

## Implementation Order

```
[ ] 1. Write scripts/build_glossary_en.py
       - Extract story-level glossaries → glossary_raw_es.json
       - Translate ES → EN via Gemini Flash (structured output)
       - Save data/processed/glossary_ayo_en.json

[ ] 2. Validate glossary_ayo_en.json manually (spot-check 10 entries)

[ ] 3. Update scripts/align_mismatches_llm.py
       - Load glossary_ayo_en.json at startup
       - Build glossary_by_story index
       - Add get_relevant_glossary() helper
       - Add format_glossary() helper
       - Pass glossary to _call_align_window()
       - Inject into prompt string
       - Add rule 8 to SYSTEM_PROMPT

[ ] 4. Update docs/reference/SEMANTIC_MATCHING.md
       - Add Step 3b: Glossary Anchoring to protocol

[ ] 5. Run on a small test batch (--max-tokens 200000)
       - Inspect results in sanity_app.py
       - Confirm token overhead is acceptable

[ ] 6. Full re-alignment run if results look good
```

---

## Token Cost Estimate

| Phase | Calls | Avg tokens/call | Total |
|-------|-------|-----------------|-------|
| Phase 1 (build glossary) | ~13 | ~800 | ~10,400 |
| Phase 2 overhead per story | ~132 stories | +100 tokens | ~13,200 |
| **Total additional cost** | — | — | **~23,600 tokens** |

Negligible relative to a full alignment run (~3–4M tokens).

---

## Files Changed / Created

| File | Action |
|------|--------|
| `scripts/build_glossary_en.py` | **New** — extracts + translates glossary |
| `data/processed/glossary_raw_es.json` | **New** — intermediate (AYO+ES, deduplicated) |
| `data/processed/glossary_ayo_en.json` | **New** — final clean AYO→EN glossary |
| `scripts/align_mismatches_llm.py` | **Modified** — glossary loading + injection |
| `docs/reference/SEMANTIC_MATCHING.md` | **Modified** — Step 3b added to protocol |
