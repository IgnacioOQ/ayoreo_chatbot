# Housekeeping Protocol
- status: active
- type: workflow
- id: ayoreo_chatbot.housekeeping
- description: Recurring multi-phase protocol an agent runs to confirm the Ayoreo chatbot repo is operational — env check, dependency map, dataset refresh, consistency checks, test suite, and report capture.
- label: [agent, core]
- injection: procedural
- volatility: evolving
- last_checked: 2026-05-12
<!-- content -->
This workflow defines the recurring housekeeping pass for the Ayoreo chatbot repository. An agent runs it to confirm the codebase is operational, the dataset is consistent, and the tests pass. It is **complementary** to `content/workflows/CODING_AGENT_MAIN_WORKFLOW.md` in the knowledge base — the main workflow governs every session; this protocol is a periodic health check the user (or an agent on the user's request) executes against this specific repo.

The output of every housekeeping pass is a dated report appended to `WORKLOG.md` and, if any tasks remain unfinished, blocks added to `TODO_WORKFLOW.md`.

## Phase 1 — Load conventions

1. Read `docs/reference/AGENTS.md` for the project's working norms.
2. Read `docs/reference/MD_CONVENTIONS.md` so any new or updated markdown follows the Markdown-JSON hybrid schema. The authoritative reference for the schema also lives in the knowledge base at `MD_CONVENTIONS.md`.

## Phase 2 — Map the dependency network

Confirm the high-level architecture is intact. Open the relevant directories and verify each layer below is present; flag any gap in the report.

**Application layer (entry points):**
- `app.py` — Streamlit UI: translation, dictionary, POS, chat.
- `sanity_app.py` — dataset verification and annotation UI.

**Core domain (`src/`):**
- `src/scraping/` — `crawler.py`, `page_scraper.py`, `pdf_scraper.py`, `utils.py`. Uses the WPML widget for bilingual pairing.
- `src/processing/` — cleaning, alignment, parallel corpus building.
- `src/pos_tagging/` — Ayoreo POS tagger (hybrid rules + EN transfer).
- `src/training/` — LoRA fine-tuning and evaluation.
- `src/inference/` — translation backends (RAG, LoRA, hybrid) and dictionary lookup.

**Scripts (`scripts/`):**
- Scrapers: `run_scraper.py`, `scrape_bible.py`, `verify_bible_completeness.py`, `update_scraping_summary.py`.
- Alignment: `align_mismatches_llm.py`, `align_bible_llm.py`, `add_body_decomposition.py`.
- Corpus & training: `run_processing.py`, `run_finetune.py`, `build_dictionary.py`, `build_pos_dataset.py`.
- Consistency: `check_ayoreoorg_consistency.py`.

## Phase 3 — Refresh the dataset

Skip this phase if no upstream change is expected. Otherwise:

1. `python scripts/run_scraper.py` — re-scrape `ayore.org` (EN+AYO by default).
2. `python scripts/scrape_bible.py` — resumable; only fetches missing chapters.
3. Re-run `python scripts/align_mismatches_llm.py` if new stories were scraped or `body_decomposition` changed.

## Phase 4 — Verify data consistency

1. `python scripts/check_ayoreoorg_consistency.py` — checks that for each entry in `data/raw/ayoreoorg/ayoreoorg.json` the `body_decomposition` has matching item counts across languages where alignment expects equality.
2. `python scripts/verify_bible_completeness.py` — confirms `bible.json` covers the canonical 66 books / 1189 chapters (modulo the Ayoré translations actually available on Bible.com).

## Phase 5 — Run the test suite

1. `pytest tests/` — run from root to leaves.
2. Investigate any failures. If a test is broken because the underlying code intentionally changed (renamed symbol, removed function, refactored API), ask the user whether to update the test or defer; do not silently delete coverage.

## Phase 6 — Capture the report

Update the **Latest Report** section below in place (overwriting the previous report), then append the same report as a new entry at the top of `WORKLOG.md` using the format defined in `content/templates/WORKLOG_TEMPLATE.md`. If the run surfaced any work that cannot be completed immediately, add it to `TODO_WORKFLOW.md` per the template at the bottom of that file.

The agent does NOT commit or push — the user reviews diffs and runs `git add` / `git commit` / `git push` themselves. See the development rules in `content/workflows/CODING_AGENT_MAIN_WORKFLOW.md` (KB).

## Latest Report

**Execution date:** _Pending_

**Status checks:**
1. Conventions loaded (Phase 1): Pending
2. Dependency network verified (Phase 2): Pending
3. Dataset refresh (Phase 3): Pending
4. Consistency checks (Phase 4): Pending
5. Test suite (Phase 5): Pending

**Summary:** _Pending first housekeeping run under this protocol._

**Follow-ups:** see `TODO_WORKFLOW.md` for any open items.
