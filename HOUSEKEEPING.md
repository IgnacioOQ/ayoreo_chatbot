# Housekeeping Protocol
- status: recurring
- type: guideline
- label: [agent, core]
<!-- content -->
1. Read the `docs/reference/AGENTS.md` and `docs/reference/MD_CONVENTIONS.md` files.
2. Look at the dependency network of the project, namely which script refers to which one.
3. Update the dataset by running the scraper scripts (`python scripts/run_scraper.py` and `python scripts/scrape_bible.py`) and make sure things are in order.
4. Verify data consistency by checking that for each entry in `ayoreoorg.json`, the body decomposition has the exact same amount of items in each language (e.g., run `python scripts/check_ayoreoorg_consistency.py`).
5. Proceed doing different sanity checks and unit tests from root scripts to leaves (`pytest tests/`).
6. Compile all errors and test results into a report. Make sure that the report uses the proper syntax protocol as defined in `MD_CONVENTIONS.md`. If necessary, use the scripts in the language folder to help you with this.
7. Print that report in the Latest Report subsection below, overwriting previous reports.
8. Add that report to the `AGENTS_LOG.md`.
9. Commit and push the changes.

## Current Project Housekeeping
- status: active
- type: plan
- label: [agent, recurring]
<!-- content -->

## Dependency Network
- status: active
- type: task
- label: [agent]
<!-- content -->
Based on codebase analysis (as of 2026-03-02):

### 1. Application Layer (Entry Point)
- id: housekeeping_protocol.dependency_network.1_application_layer
- status: active
- type: documentation
- last_checked: 2026-03-02
- label: [agent]
<!-- content -->
- **`app.py`**: Main Streamlit application entry point handling UI and translation interfaces.
- **`sanity_app.py`**: Streamlit application dedicated to verifying and correcting the raw dataset.

### 2. Core Domain Layer (src)
- id: housekeeping_protocol.dependency_network.2_core_domain_layer
- status: active
- type: documentation
- last_checked: 2026-03-02
- label: [agent]
<!-- content -->
- **`src/scraping/`**: Web scrapers for `ayore.org` (`crawler.py`, `page_scraper.py`, `pdf_scraper.py`), WPML pairing, and UTF-8 enforcement.
- **`src/processing/`**: Logic for cleaning extracted text, alignment, and parallel corpus building.
- **`src/pos_tagging/`**: POS tagger for the Ayoreo language (hybrid approach).
- **`src/training/`**: LoRA trainer, fine-tuning scripts, and evaluation logic.
- **`src/inference/`**: Handling translation features (RAG, LoRA, Hybrid backends) and the dictionary.

### 3. Data Acquisition & Maintenance Scripts
- id: housekeeping_protocol.dependency_network.3_data_acquisition_scripts
- status: active
- type: documentation
- last_checked: 2026-03-02
- label: [agent]
<!-- content -->
- **`scripts/run_scraper.py`**: Entry point of the web scraping pipeline for `ayore.org`.
- **`scripts/scrape_bible.py`**: Script for scraping Genesis chapters from `Bible.com` (handles merged verses and resuming).
- **`scripts/run_processing.py`**: Process extracted multi-lingual data.
- **`scripts/run_finetune.py`**: Train neural adapter / LoRA adapter on local environment or prepare data for Gemini API.

## Latest Report
- status: todo
- type: task
- label: [agent]
<!-- content -->
**Execution Date:** [Date]

**Status Checks:**
1.  **Data Update (`scripts/run_scraper.py` / `scripts/scrape_bible.py`)**: [Pending]
2.  **Unit Tests (`tests/`)**: [Pending]

**Summary:**
[Pending first run]

**Action Items:**
- [ ] Run full housekeeping sequence.
