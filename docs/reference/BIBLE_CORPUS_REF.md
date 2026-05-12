# Bible Corpus Reference
- status: active
- type: reference
- id: ayoreo_chatbot.bible_corpus_ref
- description: Bible corpus for the Ayoreo chatbot — Bible.com sources and versions, scraping mechanics, output schema for raw and aligned data, alignment strategy (header-deterministic with Gemini fallback), current coverage stats, and usable EN↔AYO pair counts (~20k verse pairs as of 2026-05-12).
- label: [agent]
- injection: informational
- volatility: evolving
- scope: project-specific
- last_checked: 2026-05-12
<!-- content -->
Reference for the Bible side of the Ayoreo chatbot corpus. The Ayoré Bible is the second of the project's two data sources (the first is ayore.org cultural texts, documented in [AYOREO_SCRAPING_REF.md](AYOREO_SCRAPING_REF.md)). This file documents what was scraped, how it's organized on disk, how parallel verses are aligned across languages, and how many usable training pairs the corpus currently yields.

Read this when you need to know: which translations were used, what fields are in `bible.json`, what the `alignment_map` format means, or how many EN↔AYO pairs you can extract today. Read [AYOREO_SCRAPING_REF.md](AYOREO_SCRAPING_REF.md) for scraping mechanics shared across both sources (UTF-8 enforcement, anchor-fragment filtering, etc.).

**Headline numbers (snapshot — 2026-05-12):**
- **759 chapters** scraped, **261 aligned** with an explicit `alignment_map`, the other 498 trivially 1:1.
- **20,324 EN↔AYO verse pairs** available for training (every English verse that has any Ayoré coverage).
- Equivalently: **19,838 alignment blocks** where both EN and AYO sides are non-empty (counts each fused multi-verse block as one pair).
- **105 English verses** with no Ayoré translation (e.g. Isaiah 7 outside v.14) — no pair possible.

---

## 1. Sources and versions

The corpus is scraped from [bible.com](https://www.bible.com) in three parallel translations:

| Language | Version | Bible.com ID | URL pattern |
| :--- | :--- | :--- | :--- |
| Ayoré   | Ayore Biblia                                | `2825` | `bible.com/es-ES/bible/2825/GEN.1.AYORE` |
| Spanish | La Biblia: La Palabra de Dios para Todos     | `3291` | `bible.com/es-ES/bible/3291/GEN.1.VBL`   |
| English | Free Bible Version                          | `1932` | `bible.com/es-ES/bible/1932/GEN.1.FBV`   |

Ayoré is the canonical reference for *what to scrape*: the linked-list crawler in [scripts/scrape_bible.py](../../scripts/scrape_bible.py) walks chapters in the Ayoré edition (because only some books are translated), then mirrors each URL to the Spanish and English versions by swapping the version ID and the language-code suffix.

## 2. Scraping mechanics

Driver: [scripts/scrape_bible.py](../../scripts/scrape_bible.py). The shared generic patterns (linked-list traversal, safe resumption, UTF-8 enforcement, fused-verse handling, validation layers) are documented in `content/how-to/WEB_SCRAPING_SKILL.md` in the knowledge base. Project-specific points:

- **Traversal**: starts at Genesis 1 (Ayoré), reads the *next-chapter* link out of the rendered HTML, follows it. No hard-coded canon list. Skips books Ayoré does not translate. Stops when there is no next-chapter link.
- **Verse extraction**: every verse is a DOM element with `data-usfm="BOOK.CHAPTER.VERSE"`. The scraper strips the `ChapterContent-module__label` spans before reading `.get_text()` so verse numbers don't leak into the text.
- **Fused verses**: Bible.com encodes translator merges as `data-usfm="1SA.31.11+1SA.31.12"`. The scraper splits on `+`, generates a header with a verse range (`"1 Samuel 31,11-12"`), and stores the combined text under that header. The trailing range is preserved exactly — downstream alignment depends on it.
- **UTF-8**: `extract_chapter_data` forces `response.encoding = "utf-8"` in [scripts/scrape_bible.py](../../scripts/scrape_bible.py) before parsing, regardless of what the server's `Content-Type` claims. Defends against silent mojibake of Ayoré diacritics (`ĩ`, `ã`, `ṍ`, `ẽ`, combining acute/tilde) if Bible.com or a CDN ever drops the charset header.
- **Resumable**: after each chapter the script writes `bible.json` to disk. On restart it skips chapters already present.
- **Verse-count validation (inline)**: when a chapter's verse counts differ across the three languages, a `"Translation Verse Mismatch: {'es': X, 'en': Y, 'ayo': Z}"` warning is appended to the entry's `warnings` array and mirrored into the `mismatches` array of `bible_scraping_summary.json`. These are informational, not errors — they flag chapters where translators merged verses, and they are exactly the chapters that need an explicit `alignment_map`.
- **Canon validation (exogenous)**: [scripts/verify_bible_completeness.py](../../scripts/verify_bible_completeness.py) compares `bible.json` against the canonical 66 books / 1189 chapters and reports any gaps relative to the Ayoré edition's coverage.

## 3. File layout

```
data/raw/bible/
├── bible.json                       # Raw scraped data — chapters indexed by story_id
├── aligned_bible.json               # bible.json + per-mismatched-chapter alignment_map
├── bible_scraping_summary.json      # Scrape stats, mismatches index
└── aligned_bible_backup_<ts>_*.json # Timestamped pre-write backups (kept for safety)
```

Downstream consumers (e.g. [src/processing/corpus_builder.py](../../src/processing/corpus_builder.py)) should read `aligned_bible.json` and fall back to `bible.json` only when the aligned file is absent.

## 4. Entry schema

Each chapter is a single JSON object keyed by `story_id` (`bible__<book>-<chapter>`, e.g. `bible__gen-1`):

```json
{
  "bible__gen-1": {
    "story_id": "bible__gen-1",
    "url_en":  "https://www.bible.com/es-ES/bible/1932/GEN.1.FBV",
    "url_ayo": "https://www.bible.com/es-ES/bible/2825/GEN.1.AYORE",
    "type": "faith",
    "section": "Génesis",
    "chapter_usfm": "GEN.1",
    "title_en":  "Genesis 1",
    "title_ayo": "Génesis 1",
    "body_en":  "...",
    "body_ayo": "...",
    "body_decomposition": {
      "en":  [{"header": "Genesis 1,1", "text": "In the beginning..."}, ...],
      "ayo": [{"header": "Génesis 1,1", "text": "Iji taningai uje..."}, ...]
    },
    "warnings": [],
    "alignment_map": "[{\"es\": [0], \"en\": [0], \"ayo\": [0]}, ...]"   // only when warnings non-empty
  }
}
```

- `body_decomposition.{lang}` is the **chunk array** the aligner operates on: one element per verse in the source HTML, with `header` (e.g. `"Genesis 1,1"`, or a range like `"Exodus 7,8-9"` when verses were fused by the translator) and `text` (the verse content, label spans stripped).
- `alignment_map` is a JSON-stringified array of `{"es": [...], "en": [...], "ayo": [...]}` blocks. Each block's lists are 0-indexed chunk positions in `body_decomposition`. The map is present only for chapters with at least one `Translation Verse Mismatch` warning; chapters without a warning have equal counts and align trivially by chunk index.

## 5. Alignment strategy

The job: produce a verse-level mapping across ES/EN/AYO for the 261 chapters where translators didn't preserve a 1:1:1 verse count.

The Ayoré translation labels every fused verse range in its own chunk header (e.g. `"Éxodo 39,16-17-18"`). Spanish and English on the FBV/VBL editions almost always keep one chunk per verse. That makes the alignment **fully determined by the headers** for the vast majority of chapters — no LLM reasoning required.

Driver: [scripts/align_bible_llm.py](../../scripts/align_bible_llm.py). It tries the zero-cost header-deterministic strategy first and only falls back to Gemini if the headers don't determine the mapping (e.g. malformed headers, missing chunks).

### Algorithm — `try_header_alignment`

1. Parse the trailing verse spec from each chunk header (`X,N`, `X,N-M`, `X,N-M-O`) for all three languages. If any chunk lacks a parseable spec, bail.
2. Per language, verses must be distinct (no duplicates within one language).
3. The canonical verse set is the **union** of verse numbers across the three languages. Each language may be a partial subset (Ayoré is sometimes only one verse of a chapter, e.g. Isaiah 7:14; Spanish occasionally drops a trailing or interior verse).
4. Union-find on the canonical set: verses fused inside any single chunk in any language belong to the same alignment block.
5. Each equivalence class becomes one block. For each language and each block, list the chunk indices that cover any verse in the block (or `[]` if that language has no chunk there).
6. Validate: every chunk index per language appears exactly once across the blocks; ordering is monotonic.

### Gemini fallback

If `try_header_alignment` returns `None`, the script falls back to Gemini (`gemini-2.5-flash`, server-side cached system prompt). The Gemini client and the cache are created **lazily**, on first need — a fully header-deterministic run issues zero API calls and pays nothing for cache setup. As of this writing, the entire current corpus is header-deterministic; the fallback exists only for future, malformed-header cases.

## 6. Current coverage (snapshot — 2026-05-12)

| Metric | Count |
| :--- | ---: |
| Total chapters in `bible.json` | **759** |
| Chapters with `Translation Verse Mismatch` warning | **261** |
| Chapters with `alignment_map` | **261** |
| Header-resolvable (zero LLM) | **261 / 261** |
| Maps with out-of-range chunk indices | **0** |
| Maps with duplicate or missing chunk coverage | **0** |

The remaining 498 chapters have equal ES/EN/AYO verse counts and align 1:1 by position with no explicit map.

## 7. Usable EN↔AYO pairs

There are two natural ways to count "pairs," depending on how the downstream consumer plans to use them. Both are reported below.

### By English verse — **20,324 total**

One English verse that has *any* Ayoré coverage = one pair. This is the relevant count if each training row is keyed on a single EN verse (typical for sequence-to-sequence training).

| Source of EN-verse pairs | Count |
| :--- | ---: |
| Trivial 1:1 (no-warning chapters) | **12,327** |
| From `alignment_map` (mismatched chapters) | **7,997** |
| **Total EN verses with Ayoré coverage** | **20,324** |
| EN verses with no Ayoré translation (no pair possible) | 105 |

### By alignment block — **19,838 total**

One alignment block (which may fuse 2+ EN verses into a single Ayoré chunk) = one pair. This is the relevant count if each training row is keyed on a single Ayoré chunk, with the EN side possibly being multi-verse.

| Source of block pairs | Count |
| :--- | ---: |
| Trivial 1:1 (no-warning chapters) | **12,327** |
| From `alignment_map` (mismatched chapters) | **7,511** |
|   …of which clean 1:1 (single EN ↔ single AYO chunk) | 7,075 |
|   …of which fused (2+ EN verses ↔ 1 AYO chunk) | 436 |
| **Total block pairs** | **19,838** |
| Blocks with empty Ayoré (no pair) | 105 |

The difference between the two totals (**20,324 − 19,838 = 486**) is exactly the extra EN verses that share an Ayoré chunk inside the 436 fused blocks.

### Notes for downstream consumers

- **Trivial chapters**: read `body_decomposition.en[i]` and `body_decomposition.ayo[i]` for each `i` — they're already aligned.
- **Mismatched chapters**: iterate `alignment_map`. For each block where both `en` and `ayo` are non-empty, the EN side may have 1+ chunks and the AYO side has 1+ chunks. For training, choose:
  - **Concatenate the EN side** when fused: `" ".join(body_en[i] for i in block.en)` ↔ `body_ayo[block.ayo[0]]`. One training pair per block; preserves Ayoré's semantic unit.
  - **Duplicate the AYO side** when fused: emit one pair per EN chunk in the block, each pointing at the same AYO text. More pairs, but the AYO text is repeated.
- **Empty-AYO blocks** (`block.ayo == []`) are verses Ayoré doesn't translate (e.g. Isaiah 7 outside v.14). Skip them for EN↔AYO training.

## 8. Related files

- Scraping: [scripts/scrape_bible.py](../../scripts/scrape_bible.py), [scripts/verify_bible_completeness.py](../../scripts/verify_bible_completeness.py), [scripts/update_scraping_summary.py](../../scripts/update_scraping_summary.py).
- Alignment: [scripts/align_bible_llm.py](../../scripts/align_bible_llm.py).
- Corpus builder (parallel pair extraction): [src/processing/corpus_builder.py](../../src/processing/corpus_builder.py).
- Generic scraping patterns (KB): `content/how-to/WEB_SCRAPING_SKILL.md`.
- Sister source spec: [AYOREO_SCRAPING_REF.md](AYOREO_SCRAPING_REF.md).
- Semantic alignment protocol (used historically; superseded for Bible by the header method, still relevant for ayore.org): [SEMANTIC_MATCHING.md](SEMANTIC_MATCHING.md).
