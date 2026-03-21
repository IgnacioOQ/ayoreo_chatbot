# AI Agent Logs
- id: ai_agent_logs
- status: active
- type: context
- last_checked: 2026-03-21
<!-- content -->
This file tracks major actions, architectural changes, and features implemented by AI agents functioning on this codebase.

## [2026-03-02] Semantic Alignment Protocol & Token Optimization
- id: ai_agent_logs.2026_03_02_semantic_alignment_token_optimization
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
**Agent**: Antigravity
**Task**: Design a heuristic alignment protocol for low-resource translation datasets and optimize its API cost payload.

### Summary
- id: ai_agent_logs.2026_03_02_semantic_alignment_token_optimization.summary
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
Implemented a two-part semantic matching protocol using Gemini to map opaque Ayoreo text against high-resource English/Spanish anchors. Addressed high API token consumption during early runs by introducing payload minification and swapping the model from `gemini-2.5-pro` to `gemini-2.5-flash`, resulting in a ~95% cost reduction.

### Changes
- id: ai_agent_logs.2026_03_02_semantic_alignment_token_optimization.changes
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
-   **Semantic Alignment Tooling**: Created `scripts/align_mismatches_llm.py` and `scripts/align_bible_llm.py` to enforce structured JSON output grouping mapped sentence chunks.
-   **Heuristic Fallbacks**: Added size-matching and prefix-omission heuristics to the agent prompt to prevent LLMs from inaccurately mapping massive paragraphs to single-sentence meta-comments.
-   **Cost Optimization**: Edited generation scripts to use `json.dumps(..., separators=(',', ':'))` rather than `indent=2`, saving thousands of whitespace tokens per API call. Swapped to `gemini-2.5-flash` for structural reasoning.
-   **UI Integration**: Completely rewrote the "Parallel (Aligned)" tab in `sanity_app.py` to parse the dynamic alignment maps instead of relying on a naive max-length zip algorithm.

### Verification
- id: ai_agent_logs.2026_03_02_semantic_alignment_token_optimization.verification
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
-   Verified `sanity_app.py` correctly renders parsed map dictionaries for "Al pie del Totem" story without crashing.
-   Verified execution logs showing cost drops to ~$0.27 per 3.69M tokens.

---

## [2026-03-21] Paragraph-Level Semantic Granularity & Corpus Builder Fix
- id: ai_agent_logs.2026_03_21_paragraph_granularity
- status: active
- type: context
- last_checked: 2026-03-21
<!-- content -->
**Agent**: Claude Sonnet 4.6 (Claude Code)
**Task**: Fix semantic matching granularity and wire up corpus builder to the new data source.

### Summary
The alignment was operating at section level (3-4 chunks per story) instead of versicle/paragraph level. The `body_decomposition` was grouping all `\n\n`-separated paragraphs under a bold section header into a single chunk. Fixed by rewriting `extract_sections()` to emit one chunk per paragraph. Also removed Spanish from the alignment prompt (was causing 5000+ bogus index outputs due to massive ES decomposition), and updated `corpus_builder.py` to read from `ayoreoorg.json` instead of the legacy `data/raw/pages/` directory.

### Changes
- **`scripts/add_body_decomposition.py`**: Rewrote `extract_sections()` — each `\n\n`-delimited paragraph is now its own chunk (one semantic unit). Bold header lines attach to the next paragraph as the `header` field. Stories went from ~4 chunks to ~20 chunks each.
- **`scripts/align_mismatches_llm.py`**: Removed Spanish (`es`) from the alignment prompt and from the `AlignmentBlock` Pydantic schema entirely. Spanish data was bloating prompts with thousands of indices and causing Gemini structured output truncation.
- **`src/processing/corpus_builder.py`**: Updated to read from `data/raw/ayoreoorg/aligned_ayoreoorg.json` (falling back to `ayoreoorg.json`) instead of the legacy `data/raw/pages/*.json` directory. When `alignment_map` is present, uses it with `body_decomposition` to produce clean paragraph-level EN↔AYO pairs. Falls back to `align_sentences()` for stories without an alignment map.

### Verification
- `body_decomposition` for `creencias__creencias-al-pie-del-totem`: EN=21 chunks, AYO=22 chunks (was EN=4, AYO=3).
- Alignment run: 109/132 stories aligned successfully, ~1.9M tokens used (within 4M budget).
- Corpus: **1,795 segments** (was 366 — glossaries only). Now includes 1,143+ narrative pairs.
- Splits: 1,435 train / 178 val / 182 test.
- 23 stories failed alignment (mostly `ensenanzas`) — retry run initiated; these fall back to `align_sentences()` in corpus builder.
