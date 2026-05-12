# Ayoreo Chatbot Worklog
- status: active
- type: log
- id: ayoreo_chatbot.worklog
- description: Append-only history of significant changes, architectural decisions, and major tasks executed by AI agents on the Ayoreo chatbot codebase.
- label: [agent]
- injection: excluded
- volatility: evolving
- last_checked: 2026-05-12
<!-- content -->
Append-only working history. Newest entries first.
Add an entry whenever you solve a difficult problem, make a significant change, or complete a major task.

This file supersedes the legacy `AGENT_LOGS.md`. The entries below preserve the full content of the prior log; new entries should be added at the top in the format used by `content/templates/WORKLOG_TEMPLATE.md` in the knowledge base.

---

## 2026-05-12 — Repaired 41 corrupt stored Bible alignment maps
- status: done
- type: task
- id: ayoreo_chatbot.worklog.2026_05_12_repair_corrupt_bible_maps
- last_checked: 2026-05-12
<!-- content -->
**Agent:** Claude (Opus 4.7, Claude Code)
**Task:** Replace the 41 stored Bible alignment maps that disagreed with the header-deterministic method, using the same header method.

**Why they were broken**

- **39 chapters** had stored maps referencing chunk indices that don't exist (e.g. `en[31]` when EN has only 31 chunks at indices 0..30). Out-of-bounds Gemini hallucinations from earlier runs.
- **`bible__1sa-18`** had a stored map that referenced AYO chunk 26 twice and never referenced AYO chunk 27 — duplicate/missing coverage.
- **`bible__jdg-9`** had a stored map that was technically valid but bunched two adjacent 1:1 verse pairs into a single 2:2 block (Judges 9,4 and 9,5 each have their own EN/AYO chunk, separately labeled in the headers). The header method produces finer-grained, more useful blocks for training.

**Change**

For each of the 41 chapters where `try_header_alignment` succeeds and disagrees with the stored map, replaced the stored map with the header-derived map. Created a timestamped backup (`aligned_bible_backup_<ts>_pre_realign_41.json`) before writing. Pure local operation, no API calls.

**Verification**

Re-audited the full set of 261 mismatched aligned chapters after the rewrite:
- Maps referencing out-of-range indices: **0** (was 39)
- Maps with duplicate or missing chunk references: **0** (was 2)

**Files changed**

- `data/raw/bible/aligned_bible.json` — 41 `alignment_map` entries replaced.
- `data/raw/bible/aligned_bible_backup_<ts>_pre_realign_41.json` — pre-write backup.

---

## 2026-05-12 — Header-deterministic shortcut wired into align_bible_llm.py
- status: done
- type: task
- id: ayoreo_chatbot.worklog.2026_05_12_header_shortcut_align_bible
- last_checked: 2026-05-12
<!-- content -->
**Agent:** Claude (Opus 4.7, Claude Code)
**Task:** Avoid Gemini API calls on Bible chapters whose alignment is already determined by the chunk headers.

**Change**

Added `try_header_alignment()` to `scripts/align_bible_llm.py` and rewrote `main()` to use it as the primary strategy. Gemini is now a fallback that only fires when the headers don't determine the alignment. The Gemini client and the cached system prompt are created lazily, on first need — a fully header-deterministic run issues zero API calls (and pays nothing for cache setup).

**Algorithm**

1. Parse the trailing verse spec on each chunk's header (`X,N`, `X,N-M`, `X,N-M-O`).
2. For each language, the union of all per-chunk verse ranges must equal the contiguous set 1..N. If any chunk lacks a parseable spec, or the three languages disagree on N, bail and return None.
3. Build a union-find partition of verses: two verses are equivalent if any single chunk in any language fuses them. Each equivalence class becomes one block; ES/EN/AYO indices in the block are the chunks (in each language) that cover those verses.
4. Validate full coverage and monotonicity. Any failure → return None.

**Verification (local, no API)**

- Module imports cleanly.
- `try_header_alignment` reproduces all 10 of today's hand-built maps byte-for-byte.
- Corpus-wide: **250/261** mismatched chapters are resolvable via headers (96%). The remaining 11 still need Gemini.

**Side discovery: 39 broken stored maps**

While comparing the header method against the existing 261 stored Gemini maps, 41 disagreed. An out-of-range audit found that **39 of those 41 stored maps reference chunk indices that don't exist** (e.g. `en[31]` when EN has only 31 chunks at positions 0..30) — Gemini hallucinations from earlier runs. Not fixed in this session; recorded as a follow-up.

**Follow-ups (not done this session)**

- Re-align the 39 chapters whose stored maps reference out-of-range chunk indices. The header method should produce a valid map for nearly all of them (already-verified for the 209 that match).
- Decide what to do about the 11 chapters where the header method fails — most are likely missing chunk headers; a small targeted Gemini run, or manual review, may be cheaper than the current full re-run.

---

## 2026-05-12 — Bible alignment finished without Gemini (header-based deterministic fill)
- status: done
- type: task
- id: ayoreo_chatbot.worklog.2026_05_12_bible_alignment_completion
- last_checked: 2026-05-12
<!-- content -->
**Agent:** Claude (Opus 4.7, Claude Code)
**Task:** Finish the 10 remaining Bible chapters that had a `Translation Verse Mismatch` warning but no `alignment_map`.

**Insight**

`scripts/align_bible_llm.py` was sending these to Gemini, but the Ayoré translation always labels fused verses in the chunk header itself — e.g. `Éxodo 39,16-17-18` or `Efésios 1,15-16`. Combined with the fact that ES and EN have one chunk per verse (no fusions) and headers form a contiguous 1..N sequence, the alignment is fully determined by the headers; no LLM is needed.

**Strategy**

1. Parse the verse spec at the end of each chunk header (`X,N`, `X,N-M`, `X,N-M-O`) for all three languages.
2. Verify every chapter's per-language verse sequence is contiguous and that ES/EN totals match the verse count (they did, for all 10).
3. For each AYO chunk, emit one block `{"es": [...], "en": [...], "ayo": [i]}` where `es`/`en` are the 0-indexed positions of the verses the AYO header claims to cover. Since ES/EN are 1:1 with verse numbers, verse `v` maps to position `v-1`.
4. Validate: every ES/EN/AYO index must appear exactly once across the map (full coverage) and be monotonic.

**Verification**

- Spot-read content for 5 fused passages (Ephesians 1,15-16 / 1,17-18 / 1,19-20 and Exodus 39,16-17-18 / 19-20-21). All AYO chunks semantically cover the EN verses claimed in the header (proper nouns, verbs, and topic match).
- Programmatic check: every chunk index covered exactly once, monotonic order preserved.
- Final tally: **261/261 mismatched chapters aligned**, 0 unaligned.

**Changes**

- `data/raw/bible/aligned_bible.json`: added `alignment_map` for `bible__exo-7`, `bible__exo-20`, `bible__exo-22`, `bible__exo-39`, `bible__1sa-19`, `bible__neh-8`, `bible__est-4`, `bible__est-7`, `bible__dan-1`, `bible__eph-1`.
- Backup written to `data/raw/bible/aligned_bible_backup_<timestamp>_pre_claude_align.json` before mutating the file.
- No code changes — one-shot fill via an inline script.

**Cost**

Zero Gemini API tokens. Done with header parsing and human-readable validation.

**Follow-up (not done this session)**

`scripts/align_bible_llm.py` could be improved to detect header-deterministic chapters upfront and skip the LLM call entirely. The vast majority of mismatched chapters in this dataset are header-deterministic (Ayoré is the only translation that fuses, and it labels its fusions). Worth doing as a future task if the dataset grows.

---

## 2026-05-12 — Governance refresh and test-suite repair
- status: done
- type: task
- id: ayoreo_chatbot.worklog.2026_05_12_governance_refresh
- last_checked: 2026-05-12
<!-- content -->
**Agent:** Claude (Opus 4.7, Claude Code)
**Task:** Re-onboard after ~7 weeks away; bring root governance files in line with the knowledge base's MD_CONVENTIONS, and confirm the codebase is operational.

**Outcome**

- **Tests:** `pytest tests/` collected 20 tests, all passing. Two stale test modules were repaired:
  - `tests/test_scraping.py` was importing `pair_pages_by_position` from `src/scraping/crawler.py`; the function was replaced by `pair_pages_trilingual` during the WPML migration. Rewrote two tests to call the new three-list API and assert against the `(url|title|slug)_(es|en|ayo)` keys.
  - `tests/test_inference.py` still exercised the legacy `ayo_to_es` / `es_to_ayo` directions with `"spanish"` example keys; the translator was pivoted to English as the anchor (`ayo_to_en` / `en_to_ayo`, `"english"` keys). Updated both tests accordingly.
- **AGENT_LOGS.md → WORKLOG.md:** migrated the file under a new schema-compliant header (`type: log`, `injection: excluded`, root-only metadata per `MD_CONVENTIONS.md`); preserved all three prior entries verbatim. Deleted `AGENT_LOGS.md`.
- **TODO_WORKFLOW.md:** bootstrapped from `content/templates/TODO_WORKFLOW_TEMPLATE.md` in the KB. Used during this session to track the test-repair task, then cleared on completion.
- **HOUSEKEEPING.md:** rewrote against `MD_CONVENTIONS.md`. Reclassified from invalid `type: guideline` to `type: workflow` (a recurring multi-phase procedure, per the workflow-vs-how-to decision test). Stripped per-subsection metadata blocks (workflow + content docs use root-only metadata). Replaced references to the old `AGENT_LOGS.md` with `WORKLOG.md`, added a pointer to `TODO_WORKFLOW.md`, and removed the "commit and push" step — the user handles git themselves per the global agent rules.

**Files changed**

- Added: `WORKLOG.md`, `TODO_WORKFLOW.md`.
- Deleted: `AGENT_LOGS.md`.
- Rewritten: `HOUSEKEEPING.md`.
- Updated: `tests/test_scraping.py`, `tests/test_inference.py`.

---

## 2026-03-21 — Alignment Completion: Windowed Batching & Safety Filter Handling
- status: done
- type: task
- id: ayoreo_chatbot.worklog.2026_03_21_alignment_completion
- last_checked: 2026-03-21
<!-- content -->
**Agent:** Claude Sonnet 4.6 (Claude Code)
**Task:** Fix the 23 remaining unaligned stories from the previous session.

**Summary**

Three distinct failure categories were identified and addressed. The core issue was that large stories (27–142 EN chunks) caused Gemini's structured output to generate enormous pretty-printed JSON, consistently hitting the 32k output token limit and truncating mid-object. The fix was to remove `response_schema` (switching to plain JSON mode, ~10x more compact output), reduce `WINDOW_SIZE` to 20 EN chunks per API call, and add explicit index bounds to the prompt. Additionally, 2 stories with EN=0 were short-circuited in code (no API call), and 5 stories were permanently blocked by Gemini's `PROHIBITED_CONTENT` safety filter on their text content.

**Root Causes & Fixes**

- **EN=0 stories (2):** `canciones-voy-a-cantar-un-poco` and `ayoreode-chuje-yai-nanique` have no English content — alignment is structurally impossible. Fixed by short-circuiting in `align_story()`: returns `[]` immediately without an API call, saved as `"alignment_map": "[]"`.
- **Output truncation (21 stories):** Gemini's `response_schema` forces pretty-printed JSON (one element per line). Even with `max_output_tokens=32768`, the model was producing 64k+ char outputs due to hallucinated index arrays. Fixed by:
  - Removing `response_schema` — plain JSON mode produces compact minified output (~10x smaller)
  - Reducing `WINDOW_SIZE` from 40 → 20 EN chunks per call
  - Setting `max_output_tokens=8192` (appropriate for compact 20-block output)
  - Adding explicit index bounds to the prompt header: `EN indices 0-{N-1} ({N} items)`
  - Implementing windowed batching: large stories split into 20-chunk EN windows with proportional AYO windows (ratio × 1.3 buffer); indices offset-adjusted and stitched
- **`PROHIBITED_CONTENT` blocks (5 stories + 1 parse error):** Gemini safety filter triggers on specific windows of `ensenanzas` content (Ayoreo religious teachings). Cannot be resolved by prompt engineering — the text itself is blocked. Accepted as permanent fallbacks to `align_sentences()` in corpus builder. These are ~4.5% of the dataset; `ensenanzas` texts are short and structured, making the naive aligner reasonably effective for them.
- **Fixed `if alignment_map:` → `if alignment_map is not None:`** in main loop so EN=0 stories (returning `[]`) get saved and skipped on future runs.

**Changes**

- **`scripts/align_mismatches_llm.py`:**
  - Added `WINDOW_SIZE = 20` constant
  - Removed Pydantic `AlignmentBlock`/`AlignmentResponse` schema classes
  - Rewrote `align_story()` with EN=0 short-circuit and windowed dispatch
  - Extracted `_call_align_window()` for single-window API calls with offset adjustment
  - Implemented `_align_windowed()` for large stories
  - Removed `response_schema` from config; switched to plain JSON mode
  - Updated system prompt: added compact JSON format example, index bounds rule, coverage rule
  - Fixed `if alignment_map is not None:` check in main loop

**Verification**

- Final alignment: **126/132 stories** (109 → 126, +17 this session)
- 2 EN=0 stories: saved as `[]`, permanently skipped
- 5 PROHIBITED_CONTENT + 1 parse error: permanent fallbacks to `align_sentences()`
- Token cost this session: **177,709 tokens** (~$0.04)
- Output tokens per story: 164–1,069 (compact JSON working correctly)

---

## 2026-03-21 — Paragraph-Level Semantic Granularity & Corpus Builder Fix
- status: done
- type: task
- id: ayoreo_chatbot.worklog.2026_03_21_paragraph_granularity
- last_checked: 2026-03-21
<!-- content -->
**Agent:** Claude Sonnet 4.6 (Claude Code)
**Task:** Fix semantic matching granularity and wire up corpus builder to the new data source.

**Summary**

The alignment was operating at section level (3-4 chunks per story) instead of versicle/paragraph level. The `body_decomposition` was grouping all `\n\n`-separated paragraphs under a bold section header into a single chunk. Fixed by rewriting `extract_sections()` to emit one chunk per paragraph. Also removed Spanish from the alignment prompt (was causing 5000+ bogus index outputs due to massive ES decomposition), and updated `corpus_builder.py` to read from `ayoreoorg.json` instead of the legacy `data/raw/pages/` directory.

**Changes**

- **`scripts/add_body_decomposition.py`:** Rewrote `extract_sections()` — each `\n\n`-delimited paragraph is now its own chunk (one semantic unit). Bold header lines attach to the next paragraph as the `header` field. Stories went from ~4 chunks to ~20 chunks each.
- **`scripts/align_mismatches_llm.py`:** Removed Spanish (`es`) from the alignment prompt and from the `AlignmentBlock` Pydantic schema entirely. Spanish data was bloating prompts with thousands of indices and causing Gemini structured output truncation.
- **`src/processing/corpus_builder.py`:** Updated to read from `data/raw/ayoreoorg/aligned_ayoreoorg.json` (falling back to `ayoreoorg.json`) instead of the legacy `data/raw/pages/*.json` directory. When `alignment_map` is present, uses it with `body_decomposition` to produce clean paragraph-level EN↔AYO pairs. Falls back to `align_sentences()` for stories without an alignment map.

**Verification**

- `body_decomposition` for `creencias__creencias-al-pie-del-totem`: EN=21 chunks, AYO=22 chunks (was EN=4, AYO=3).
- Alignment run: 109/132 stories aligned successfully, ~1.9M tokens used (within 4M budget).
- Corpus: **1,795 segments** (was 366 — glossaries only). Now includes 1,143+ narrative pairs.
- Splits: 1,435 train / 178 val / 182 test.
- 23 stories failed alignment (mostly `ensenanzas`) — retry run initiated; these fall back to `align_sentences()` in corpus builder.

---

## 2026-03-02 — Semantic Alignment Protocol & Token Optimization
- status: done
- type: task
- id: ayoreo_chatbot.worklog.2026_03_02_semantic_alignment_token_optimization
- last_checked: 2026-03-02
<!-- content -->
**Agent:** Antigravity
**Task:** Design a heuristic alignment protocol for low-resource translation datasets and optimize its API cost payload.

**Summary**

Implemented a two-part semantic matching protocol using Gemini to map opaque Ayoreo text against high-resource English/Spanish anchors. Addressed high API token consumption during early runs by introducing payload minification and swapping the model from `gemini-2.5-pro` to `gemini-2.5-flash`, resulting in a ~95% cost reduction.

**Changes**

- **Semantic Alignment Tooling:** Created `scripts/align_mismatches_llm.py` and `scripts/align_bible_llm.py` to enforce structured JSON output grouping mapped sentence chunks.
- **Heuristic Fallbacks:** Added size-matching and prefix-omission heuristics to the agent prompt to prevent LLMs from inaccurately mapping massive paragraphs to single-sentence meta-comments.
- **Cost Optimization:** Edited generation scripts to use `json.dumps(..., separators=(',', ':'))` rather than `indent=2`, saving thousands of whitespace tokens per API call. Swapped to `gemini-2.5-flash` for structural reasoning.
- **UI Integration:** Completely rewrote the "Parallel (Aligned)" tab in `sanity_app.py` to parse the dynamic alignment maps instead of relying on a naive max-length zip algorithm.

**Verification**

- Verified `sanity_app.py` correctly renders parsed map dictionaries for "Al pie del Totem" story without crashing.
- Verified execution logs showing cost drops to ~$0.27 per 3.69M tokens.
