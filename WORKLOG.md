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

## 2026-05-12 — Reference-docs cleanup, BIBLE_CORPUS_REF, README and HOUSEKEEPING refresh
- status: done
- type: task
- id: ayoreo_chatbot.worklog.2026_05_12_docs_cleanup
- last_checked: 2026-05-12
<!-- content -->
**Agent:** Claude (Opus 4.7, Claude Code) + user (bulk deletions)
**Task:** Consolidate `docs/reference/` so it only contains project-specific specs, add a dedicated Bible-corpus reference, and refresh the README and the HOUSEKEEPING protocol to match the new state.

**Deletions (by user)**

The following files were removed from `docs/reference/` because they were either generic agent guides that belong in the kb_mcp knowledge base or duplicates of KB content:

- `AGENTS.md` — generic working-norms doc; the project now uses `README.md` + `WORKLOG.md` + `TODO_WORKFLOW.md` for this role, with the KB workflow (`content/workflows/CODING_AGENT_MAIN_WORKFLOW.md`) governing session protocol.
- `MD_CONVENTIONS.md` — local copy of the KB's authoritative `MD_CONVENTIONS.md`; KB is now the only source of truth.
- `GCLOUD_AGENT.md`, `LATENCY_AGENT.md`, `MCP_AGENT.md`, `PYUI_AGENT.md`, `RAGS_AGENT.md`, `TOKENOPT_SKILL.md` — generic Claude-agent how-tos; KB-only.
- `HTML_SCRAPING_SKILL.md` — already noted as superseded by [AYOREO_SCRAPING_REF.md](docs/reference/AYOREO_SCRAPING_REF.md) in the prior worklog entry; deletion completes that migration.
- `SCRAPER_AGENT.md` — documented an unrelated project's scraper; never used here.

**Additions**

- [docs/reference/BIBLE_CORPUS_REF.md](docs/reference/BIBLE_CORPUS_REF.md) — new project reference for the Bible side of the corpus: Bible.com sources and versions (Ayoré 2825 / Spanish 3291 / English 1932), scraping mechanics, on-disk file layout, `bible.json` entry schema, `alignment_map` format, the generalized header-deterministic alignment algorithm, current coverage snapshot (759 chapters / 261 mismatched / 261 aligned / 0 still needing Gemini / 0 broken), and usable EN↔AYO pair counts. Follows MD_CONVENTIONS: `type: reference`, `_REF.md` suffix, root-only metadata, `scope: project-specific`. After initial draft, surfaced the headline pair counts in the preamble and added a verse-level vs block-level breakdown — both interpretations now explicit: **20,324 EN verses with Ayoré coverage** (the count to use for seq2seq training, since each EN verse becomes one row), or equivalently **19,838 alignment blocks** with both sides non-empty (the count if each Ayoré chunk is one row, preserving the 436 fused multi-verse cases), plus 105 EN verses with no Ayoré coverage.
- [docs/reference/AYOREO_TRANSLATION_PLAN.md](docs/reference/AYOREO_TRANSLATION_PLAN.md) — new project plan (authored by the user) for the NLLB-200 + LoRA + hybrid RAG-refinement translation pipeline. Staged rollout with measurable artifacts at each phase. Status `in-progress`.

**Retrofits**

- [docs/reference/AYOREO_SCRAPING_REF.md](docs/reference/AYOREO_SCRAPING_REF.md) gained the schema-compliant root metadata block it was missing (`type`, `id`, `description`, `label`, `injection`, `volatility`, `scope`, `last_checked`) and a cross-reference paragraph pointing at the new BIBLE_CORPUS_REF.

**README**

[README.md](README.md) updated to reflect:

- Three root-level governance files now visible in the project-structure tree: `HOUSEKEEPING.md`, `WORKLOG.md`, `TODO_WORKFLOW.md`.
- More accurate scraping module descriptions (hybrid positional + WPML pairing — the corrector model, not pure WPML).
- New scripts surfaced in the tree: `align_bible_llm.py` and `verify_bible_completeness.py`.
- New **Documentación de referencia** section listing all project-specific reference docs with one-line descriptions, plus an explicit note that generic agent guides live in the KB (`kb_mcp`), not in this repo.
- `Fuentes de datos` section gained a `bible.com` line and a pointer to `BIBLE_CORPUS_REF.md`.

**HOUSEKEEPING**

[HOUSEKEEPING.md](HOUSEKEEPING.md) Phase 1 had stale references to the now-deleted `docs/reference/AGENTS.md` and `docs/reference/MD_CONVENTIONS.md`. Rewrote both steps:

- Step 1 now points at the trio of root governance files (`README.md`, `WORKLOG.md`, `TODO_WORKFLOW.md`) and explicitly states there is no separate `AGENTS.md`.
- Step 2 now instructs the agent to load `MD_CONVENTIONS.md` from the KB via `knowledge_base_read(path="MD_CONVENTIONS.md", intro_only=True)`, since the repo no longer keeps a local copy.

**No code changes this session.** Pure documentation/governance hygiene.

---

## 2026-05-12 — Split scraping docs: KB stays generic, project specifics moved local
- status: done
- type: task
- id: ayoreo_chatbot.worklog.2026_05_12_split_scraping_docs
- last_checked: 2026-05-12
<!-- content -->
**Agent:** Claude (Opus 4.7, Claude Code)
**Task:** Reconcile scraping documentation between the KB and `docs/reference/`. Enforce the rule that the knowledge base must remain generic; project-specific specifications belong in this repository.

**Findings (grounded in code, not docs):**
- The crawler ([src/scraping/crawler.py](src/scraping/crawler.py)) pairs EN+AYO positionally as a first guess; the page scraper ([src/scraping/page_scraper.py:255-271](src/scraping/page_scraper.py#L255-L271)) then reads the EN page's WPML switcher and **overwrites** any mismatched sibling URL with the switcher value (logged warning). This hybrid was misrepresented in both the KB and the prior local docs as either pure-positional or pure-WPML.
- Anchor language is EN, not ES (ES is opt-in via `--scrape-es` or `scrape_es: true` in `configs/scraping.yaml`). `story_id` derives from the EN slug.
- Glossary key on ayore.org entries is `english`, not `spanish` (consistent with the EN anchor).
- UTF-8 is enforced in `src/scraping/utils.fetch_page` for ayore.org; the Bible scraper now sets `response.encoding = "utf-8"` in `extract_chapter_data` too.

**KB changes — [content/how-to/WEB_SCRAPING_SKILL.md](knowledge_base/content/how-to/WEB_SCRAPING_SKILL.md):**
- Stripped all `ayore.org`/`bible.com` content (URL tables, sections list, output schemas, percent-encoding note, production run log, single-output-file rule).
- Generalized the WPML section: removed `ayore.org` URLs and the specific "13 of 14" production figure; documented both **switcher-only** and **hybrid (positional + WPML corrector)** strategies.
- Replaced the `Linked-List Traversal: Bible.com` section with a generic `Linked-List Traversal Pattern` (safe resumption, cross-version mirroring, validation layers, translator-merge handling).
- Cleaned the verification checklist of ayore-specific items.
- MCMP-specific blocks left in place; flagged for the MCMP repo to clean up.

**Local docs changes (in this repo):**
- **Wrote** [docs/reference/AYOREO_SCRAPING_REF.md](docs/reference/AYOREO_SCRAPING_REF.md) — authoritative project spec covering ayore.org and bible.com, grounded in current code: hybrid pairing strategy, EN-anchor, EN-slug `story_id`, English glossary key, full schemas, traversal mechanics, validation, safe resumption.
- **Deleted** `docs/reference/HTML_SCRAPING_SKILL.md` (content split between generic-KB and the new local doc; was internally stale on anchor language and pairing strategy).
- **Deleted** `docs/reference/SCRAPER_AGENT.md` (documented the MCMP/LMU events scraper from a different project; not used here).
- Updated [README.md](README.md) references from `HTML_SCRAPING_SKILL.md` → `AYOREO_SCRAPING_REF.md`.

**Code change:** [scripts/scrape_bible.py](scripts/scrape_bible.py) now sets `response.encoding = "utf-8"` in `extract_chapter_data` before `BeautifulSoup` parsing (matches the policy already enforced in `src/scraping/utils.fetch_page`). User added the actual line with an explanatory comment.

**Follow-up:** MCMP-specific blocks (events/people schemas, single-class `MCMPScraper` architecture, MCP field-name anti-pattern) remain in the KB doc. They belong in the MCMP repo's own reference file by the same logic applied here.

---

## 2026-05-12 — Generalized try_header_alignment + UTF-8 hardening for Bible scraper
- status: done
- type: task
- id: ayoreo_chatbot.worklog.2026_05_12_generalize_header_alignment
- last_checked: 2026-05-12
<!-- content -->
**Agent:** Claude (Opus 4.7, Claude Code)
**Task:** Eliminate the remaining Gemini fallback in the Bible alignment pipeline by generalizing the header-deterministic algorithm to cover the 11 chapters the strict version couldn't handle, plus close a latent UTF-8 risk in the Bible scraper.

**Generalized `try_header_alignment`** in [scripts/align_bible_llm.py](scripts/align_bible_llm.py):

- The canonical verse set is now the *union* of verse numbers across all three languages instead of a strict 1..N requirement on every language. Per-language verses must still be distinct.
- Each language may be a partial subset of the canon, so the previously-unhandled cases all resolve cleanly:
  - **Partial AYO** (8 chapters: isa-7, isa-9, isa-11, isa-50, hos-11, mic-5, zec-11, num-27). Verses without an AYO chunk get `"ayo": []` in the block.
  - **ES short at the end** (2 chapters: 3jn-1, rev-12). Trailing canonical verses without an ES chunk get `"es": []`.
  - **ES silently skips an interior verse** (1 chapter: 1sa-20, ES skips v.30). The v.30 block gets `"es": []`.
- Union-find still handles fused-chunk headers across any language.
- Validation unchanged: per-language full chunk-index coverage and monotonic ordering across blocks (skipping languages with no chunk in a given block).

**Regression-clean**: produces byte-identical maps for all 250 chapters the strict version already covered.

**Corpus impact**

| Metric | Before | After |
|---|---|---|
| Mismatched chapters resolvable via headers | 250/261 | **261/261** |
| Chapters still needing Gemini fallback | 11 | **0** |
| Maps with out-of-range chunk indices | 0 | 0 |
| Maps with duplicate/missing chunk references | 0 | 0 |

Two stored Gemini maps were replaced this session because the generalized header version is finer-grained:

- `bible__num-27`: stored had 11 blocks (verses 1–11 bundled into a single AYO-empty block); new has 21 blocks (one per canonical verse, AYO empty where Ayoré doesn't translate). Same coverage, uniform granularity.
- `bible__3jn-1`: stored bundled AYO chunks for v.14 and v.15 into a single 2:2 block; new gives one block per verse. Same Gemini-coarsening pattern fixed earlier for `bible__jdg-9`.

Backup written to `data/raw/bible/aligned_bible_backup_<ts>_pre_v2.json` before the two-chapter rewrite.

**UTF-8 hardening of [scripts/scrape_bible.py](scripts/scrape_bible.py)**

Added `response.encoding = "utf-8"` after the status check in `extract_chapter_data`, mirroring the defense already in `src/scraping/utils.py:25` for ayore.org. Bible.com currently serves `charset=utf-8`, and a full audit of `data/raw/bible/bible.json` found zero mojibake patterns and zero replacement characters — but the previous code relied on the server doing the right thing, which is brittle. No re-scrape needed.

**Net effect**

The Bible alignment pipeline can now reach 100% coverage on the current corpus with zero Gemini calls. The Gemini fallback path remains in place for any future chapters whose headers don't determine the alignment (e.g. malformed or missing headers).

---

## 2026-05-12 — Drafted Firebase migration plan for the sanity_app reviewer tool
- status: done
- type: task
- id: ayoreo_chatbot.worklog.2026_05_12_firebase_migration_plan
- last_checked: 2026-05-12
<!-- content -->
**Agent:** Claude (Opus 4.7, Claude Code)
**Task:** Produce a self-contained migration plan moving the Streamlit-based dataset reviewer ([sanity_app.py](sanity_app.py)) to a hosted web app on Firebase, so multiple allowlisted reviewers can verify and propose corrections to the semantic-alignment data without a local Python setup.

**Architectural decisions (elicited via clarifying questions before drafting)**

- **Access:** allowlisted reviewers via Google Sign-In, enforced both client-side and through Firestore security rules.
- **Source of truth:** `data/raw/ayoreoorg/aligned_ayoreoorg.json` and `data/raw/bible/aligned_bible.json` remain canonical. Firestore stores a snapshot plus per-reviewer proposed corrections under `datasets/{dataset_id}/stories/{story_id}/proposals/{reviewer_uid}`. A maintainer-run export script applies approved proposals back to JSON; the maintainer commits manually (no agent staging, per the project rule).
- **Frontend stack:** React + Vite on Firebase Hosting, matching the KB norm in `content/workflows/DEPLOY_FIREBASE_WORKFLOW.md` and `content/reference/FIREBASE_PLANNING_WEBAPP_REF.md`.
- **Granularity:** one Firestore doc per story (~891 docs total: 759 bible + 132 ayoreoorg). Average ~35 KB per doc, well under the 1 MB Firestore limit.

**Outcome**

- Created [docs/reference/FIREBASE_MIGRATION_PLAN.md](docs/reference/FIREBASE_MIGRATION_PLAN.md) — 10 sequenced tasks (provision → scaffold → auth → schema → seed → port UI → proposals/triage → export → deploy → decommission). Schema follows MD_CONVENTIONS (`_PLAN.md` suffix, metadata on root and every task node, valid labels only, dynamic-context loads embedded in the tasks that need them).
- Added one self-contained pickup task to [TODO_WORKFLOW.md](TODO_WORKFLOW.md) (`todo.firebase_migration_sanity_app`) that points future agents to the plan and instructs them to read it before executing.

**No code changes this session** — planning only. Task `task_1` (project provisioning) is a `human` task in the plan and was deferred at the user's request.

**KB context loaded**

- `content/workflows/CODING_AGENT_MAIN_WORKFLOW.md` (root protocol).
- `content/workflows/DEPLOY_FIREBASE_WORKFLOW.md` (intro only).
- `content/reference/FIREBASE_DEFINITIONS_REF.md` (intro only).
- `content/reference/FIREBASE_PLANNING_WEBAPP_REF.md` (TOC only, then referenced in plan tasks).
- `MD_CONVENTIONS.md` (intro only), plan template via `knowledge_base_get_template`.

**Follow-ups (not done this session)**

- All ten subtasks in the plan remain `todo`. Pickup is via `todo.firebase_migration_sanity_app` in [TODO_WORKFLOW.md](TODO_WORKFLOW.md).
- Consider whether `docs/reference/IMPROVE_SM_PLAN.md` overlaps with the new plan and should be linked or merged (called out in `task_10`).

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
