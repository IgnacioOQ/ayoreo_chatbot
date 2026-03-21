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

---

## [2026-03-21] Alignment Completion: Windowed Batching & Safety Filter Handling
- id: ai_agent_logs.2026_03_21_alignment_completion
- status: active
- type: context
- last_checked: 2026-03-21
<!-- content -->
**Agent**: Claude Sonnet 4.6 (Claude Code)
**Task**: Fix the 23 remaining unaligned stories from the previous session.

### Summary
Three distinct failure categories were identified and addressed. The core issue was that large stories (27–142 EN chunks) caused Gemini's structured output to generate enormous pretty-printed JSON, consistently hitting the 32k output token limit and truncating mid-object. The fix was to remove `response_schema` (switching to plain JSON mode, ~10x more compact output), reduce `WINDOW_SIZE` to 20 EN chunks per API call, and add explicit index bounds to the prompt. Additionally, 2 stories with EN=0 were short-circuited in code (no API call), and 5 stories were permanently blocked by Gemini's `PROHIBITED_CONTENT` safety filter on their text content.

### Root Causes & Fixes
- **EN=0 stories (2)**: `canciones-voy-a-cantar-un-poco` and `ayoreode-chuje-yai-nanique` have no English content — alignment is structurally impossible. Fixed by short-circuiting in `align_story()`: returns `[]` immediately without an API call, saved as `"alignment_map": "[]"`.
- **Output truncation (21 stories)**: Gemini's `response_schema` forces pretty-printed JSON (one element per line). Even with `max_output_tokens=32768`, the model was producing 64k+ char outputs due to hallucinated index arrays. Fixed by:
  - Removing `response_schema` — plain JSON mode produces compact minified output (~10x smaller)
  - Reducing `WINDOW_SIZE` from 40 → 20 EN chunks per call
  - Setting `max_output_tokens=8192` (appropriate for compact 20-block output)
  - Adding explicit index bounds to the prompt header: `EN indices 0-{N-1} ({N} items)`
  - Implementing windowed batching: large stories split into 20-chunk EN windows with proportional AYO windows (ratio × 1.3 buffer); indices offset-adjusted and stitched
- **`PROHIBITED_CONTENT` blocks (5 stories + 1 parse error)**: Gemini safety filter triggers on specific windows of `ensenanzas` content (Ayoreo religious teachings). Cannot be resolved by prompt engineering — the text itself is blocked. Accepted as permanent fallbacks to `align_sentences()` in corpus builder. These are ~4.5% of the dataset; `ensenanzas` texts are short and structured, making the naive aligner reasonably effective for them.
- **Fixed `if alignment_map:` → `if alignment_map is not None:`** in main loop so EN=0 stories (returning `[]`) get saved and skipped on future runs.

### Changes
- **`scripts/align_mismatches_llm.py`**:
  - Added `WINDOW_SIZE = 20` constant
  - Removed Pydantic `AlignmentBlock`/`AlignmentResponse` schema classes
  - Rewrote `align_story()` with EN=0 short-circuit and windowed dispatch
  - Extracted `_call_align_window()` for single-window API calls with offset adjustment
  - Implemented `_align_windowed()` for large stories
  - Removed `response_schema` from config; switched to plain JSON mode
  - Updated system prompt: added compact JSON format example, index bounds rule, coverage rule
  - Fixed `if alignment_map is not None:` check in main loop

### Verification
- Final alignment: **126/132 stories** (109 → 126, +17 this session)
- 2 EN=0 stories: saved as `[]`, permanently skipped
- 5 PROHIBITED_CONTENT + 1 parse error: permanent fallbacks to `align_sentences()`
- Token cost this session: **177,709 tokens** (~$0.04)
- Output tokens per story: 164–1,069 (compact JSON working correctly)
