# Ayoreo Scraping Reference
- status: active
- type: reference
- id: ayoreo_chatbot.scraping_ref
- description: Project-specific scraping spec for the Ayoreo chatbot — ayore.org and bible.com URL structures, section catalog, hybrid positional+WPML pairing, EN-anchor and EN-slug story_id rule, output schemas, metadata regexes, UTF-8 enforcement, and current production state.
- label: [agent]
- injection: informational
- volatility: evolving
- scope: project-specific
- last_checked: 2026-05-12
<!-- content -->
Project-specific scraping specifications for the Ayoreo chatbot. Read this alongside the generic patterns in the knowledge base at `content/how-to/WEB_SCRAPING_SKILL.md` (WPML, UTF-8, anchor-fragment filtering, linked-list traversal, accumulation policy, etc.). This document covers only what is unique to this project: the two data sources (`ayore.org` and `bible.com`), the URL structures, the section catalog, the pairing strategy actually used in the code, output schemas, metadata regexes, and the current production state.

For Bible-specific schema, alignment strategy, and corpus statistics (EN↔AYO pair counts, header-deterministic algorithm, etc.), see the sister doc [BIBLE_CORPUS_REF.md](BIBLE_CORPUS_REF.md).

---

## 1. ayore.org

### Anchor language

The pipeline uses **English (EN) as the primary anchor**, not Spanish. The English translations on ayore.org are higher semantic quality and align better with Ayoré. Spanish scraping is **opt-in** via `--scrape-es` (CLI) or `scrape_es: true` in [configs/scraping.yaml](../../configs/scraping.yaml). Default: **EN + AYO**.

### URL structure

| Language | URL pattern | Notes |
| :--- | :--- | :--- |
| Spanish | `https://ayore.org/es/cultura/{section}/{slug}/` | Opt-in only |
| English | `https://ayore.org/culture/{section}/{slug}/` | **No language prefix** |
| Ayoré | `https://ayore.org/ayo/culture/{section}/{slug}/` | `ayo/` prefix |

EN and AYO share the same section path slugs; ES uses Spanish slugs (e.g. `relatos-personales` ↔ `first-person-narratives`).

AYO URLs often contain percent-encoded characters (e.g. `cotate-e-ye%cc%83ra-yu` where `%cc%83` is the combining tilde). These are valid; do not double-encode.

### Content sections

Defined in [configs/scraping.yaml](../../configs/scraping.yaml):

| ES path | EN/AYO path | Type | Estimated pages |
| :--- | :--- | :--- | ---: |
| `cultura/creencias` | `culture/beliefs` | belief | 11 |
| `cultura/relatos-personales` | `culture/first-person-narratives` | personal_narrative | 14 |
| `cultura/comidas` | `culture/foods` | food | 1 |
| `cultura/juegos` | `culture/games` | game | 6 |
| `cultura/medicina` | `culture/medicine` | medicine | 1 |
| `cultura/canciones-nativas` | `culture/native-songs` | song | 22 |
| `cultura/historia-oral` | `culture/oral-history` | oral_history | 12 |
| `cultura/tradiciones-orales` | `culture/oral-traditions` | oral_tradition | 15 |
| `cultura/ensenanzas` | `culture/teachings` | teaching | 50 |

### Pairing strategy: hybrid (positional + WPML corrector)

Two stages combined:

**1. Crawler (positional first-guess)** — [src/scraping/crawler.py](../../src/scraping/crawler.py)

For each section, `discover_section_pages()` fetches each enabled language's index page, applies anchor-fragment filtering and a language guard (`get_language_from_url`), and produces an ordered list per language. `pair_pages_trilingual()` then pairs the lists by list position. This is the cheap discovery step — no per-item page fetch.

**2. Page scraper (WPML corrector)** — [src/scraping/page_scraper.py](../../src/scraping/page_scraper.py)

For each paired item, `scrape_page()`:
1. Fetches the **EN page first** (EN is the anchor).
2. Calls `extract_language_urls()` on its soup to read the WPML language-switcher widget.
3. For each sibling-language URL the switcher reports:
   - If the crawler guess is missing → fill from WPML (logged `WPML filled missing url_*`).
   - If the crawler guess differs from WPML → **overwrite with WPML** and log a warning (`WPML URL mismatch for url_*: crawler=... wpml=... — using WPML`).
4. Then fetches AYO (and ES if `scrape_es=True`) using the corrected URLs.

This is the production strategy: cheap positional discovery, with the WPML switcher acting as a corrector that catches any drift between the EN and AYO indexes the moment it occurs.

**When positional pairing fails (historical):** Production run 2026-03-01 against the `relatos-personales` section using an **ES↔AYO** positional-only approach selected the wrong AYO URL for **13 of 14 stories**. The current EN↔AYO indexes appear to be in matching order, but the WPML corrector exists to catch any future drift without trusting the index order as the source of truth.

### `story_id`

Canonical key: `{section_name}__{slug_en}`, e.g. `first-person-narratives__cotade-i-gave-myself-to-him`. `section_name` is the EN/AYO section slug (e.g. `first-person-narratives`); `slug_en` is the last path segment of the EN URL. Fallbacks: AYO slug → ES slug → list index. See [src/scraping/crawler.py:152-154](../../src/scraping/crawler.py#L152-L154).

### WordPress content DOM

| Element | Selector | Notes |
| :--- | :--- | :--- |
| Main content | `div.entry-content` | Primary; falls back to `<article>`, `div.post-content`, `<main>`, `<body>` |
| Page title | `<h1>` | First `<h1>` on page |
| Body text | `<p>`, `<blockquote>` inside content div | Skipped if length < 10 chars |
| Bold/italic | `<b>`/`<strong>`, `<i>`/`<em>` | Converted to `**...**` / `*...*` before text extraction via `_html_to_markdown_basic()` |
| Glossary | `<strong>`/`<b>` term followed by sibling text after `–`/`-`/`:` | Ayoreo term → **English** definition (anchor language is EN, not ES) |
| Body decomposition | [scripts/add_body_decomposition.py](../../scripts/add_body_decomposition.py) | Post-scrape pass; splits each body at `\n\n` boundaries where the line starts with `**...**` or `***...***` headers |

### Metadata regex

```python
# Narrator
r"(?:Narr?ador|Narrator|Narrated by)[:\s]+(.+?)(?:\n|$)"

# Location + year
r"(?:Campo Loro|Tobité|Zapocó|Santa Cruz|Poza Verde|Rincón del Tigre)[,\s]+(?:Bolivia|Paraguay)[,\s]*(\d{4})?"

# Transcriber / translator
r"(?:Transcri(?:bed|to) (?:by|por))[:\s]+(.+?)(?:\n|$)"
r"(?:Translat(?:ed|ado) (?:to Spanish )?(?:by|por))[:\s]+(.+?)(?:\n|$)"
```

### Language guard (crawler)

When crawling the EN index (no `/en/` prefix), AYO and ES sibling links share the section path and must be filtered out via `get_language_from_url(href)` — see [src/scraping/crawler.py:62-66](../../src/scraping/crawler.py#L62-L66):

```python
url_lang = get_language_from_url(href)   # returns "es", "ayo", "en", or None
if lang is None and url_lang is not None:
    continue  # skip ES/AYO links when collecting EN pages
if lang is not None and url_lang != lang:
    continue  # skip links from other languages
```

### Output schema

```json
{
    "story_id": "first-person-narratives__cotade-i-gave-myself-to-him",
    "url_en":  "https://ayore.org/culture/first-person-narratives/cotade-i-gave-myself-to-him/",
    "url_ayo": "https://ayore.org/ayo/culture/first-person-narratives/cotate-e-ye%cc%83ra-yu-to-ome-dupade/",
    "url_es":  "https://ayore.org/es/cultura/relatos-personales/...",   // only when --scrape-es
    "section": "first-person-narratives",
    "type":    "personal_narrative",
    "title_en":  "...", "title_ayo": "...", "title_es": "...",
    "body_en":   "...", "body_ayo":  "...", "body_es":  "...",
    "body_decomposition": {
        "en":  [{"header": null, "text": "..."}],
        "ayo": [{"header": null, "text": "..."}]
    },
    "alignment_map": "[{\"en\": [0, 1], \"ayo\": [0]}]",
    "glossary": [{"ayoreo": "Dupade", "english": "God"}],
    "metadata": {
        "narrator": "Cotade",
        "location": "Campo Loro, Paraguay",
        "year": "1985",
        "transcriber": "Maxine Morarie"
    },
    "scraped_at": "2026-03-01T..."
}
```

### Storage

All stories from all sections in a single file: [data/raw/ayoreoorg/ayoreoorg.json](../../data/raw/ayoreoorg/ayoreoorg.json), keyed by `story_id`. Incrementally merged across runs — existing entries are updated or new ones added, **never** removed. Do not save per-story files.

`aligned_ayoreoorg.json` is the same shape with a populated `alignment_map` per story, produced by `scripts/align_mismatches_llm.py`.

### Entry points

```bash
python scripts/run_scraper.py                              # EN + AYO, all sections + PDFs
python scripts/run_scraper.py --scrape-es                  # also scrape Spanish pages
python scripts/run_scraper.py --section first-person-narratives
python scripts/run_scraper.py --dry-run                    # discover only, no scrape
python scripts/run_scraper.py --pdfs-only                  # only download PDFs
```

PDF downloads (dictionary + grammar) are configured in `pdf_resources` of [configs/scraping.yaml](../../configs/scraping.yaml).

### UTF-8 enforcement

Handled by `src/scraping/utils.fetch_page` — forces `response.encoding = "utf-8"` before parsing. Never call `requests.get()` directly; always go through `fetch_page()`.

---

## 2. bible.com

### Versions

| Language | Version | ID | URL suffix |
| :--- | :--- | :--- | :--- |
| Ayoré | Ayore Biblia | 2825 | `.AYORE` |
| Español | La Biblia: La Palabra de Dios para Todos | 3291 | `.VBL` |
| English | Free Bible Version | 1932 | `.FBV` |

URL pattern: `https://www.bible.com/es-ES/bible/{version_id}/{BOOK}.{chapter}.{suffix}`. The `es-ES/` segment is shared across all three versions; it controls UI locale only, not content language.

### Traversal strategy: linked-list anchored on Ayoré

Ayoré is the **limiting translation** — not every book is available. The script ([scripts/scrape_bible.py](../../scripts/scrape_bible.py)) walks the AYO chapter list via the site's "Siguiente capítulo" (next chapter) link and derives the ES and EN URLs by string substitution:

```python
es_url = current_ayo_url.replace("/2825/", "/3291/").replace(".AYORE", ".VBL")
en_url = current_ayo_url.replace("/2825/", "/1932/").replace(".AYORE", ".FBV")
```

Each iteration:
1. Fetch the AYO chapter, parse verses, find the "Siguiente capítulo" `<a>`.
2. If `story_id` already in `bible.json` → skip ES/EN fetches and advance.
3. Otherwise fetch ES and EN, validate verse counts, record the entry, save to disk, advance.

When no next link is found, the traversal terminates. This guarantees only chapters present in the Ayoré translation are scraped — no requests to non-existent URLs.

### Verse extraction

| Indicator | Selector / Attribute |
| :--- | :--- |
| Verse container | `<span data-usfm="GEN.1.1">` |
| Verse-number label | `<span>` with a class containing both `label` and `chaptercontent` — removed (`.decompose()`) before text extraction |
| Merged verses | `data-usfm="1SA.31.11+1SA.31.12"` — split on `+`, all numbers from the current chapter joined with `-` → header `"1 Samuel 31,11-12"` |
| Next chapter | `<a>` whose text contains `"Siguiente capítulo"` |
| Chapter title | `<h1>` (e.g. `"Génesis 1"`) |

### Validation layers

1. **Inline verse-count mismatch** — after fetching all three languages, compare verse counts. When they differ (often legitimate translator merges), record warnings in:
   - `warnings` field of the entry in `bible.json`
   - `mismatches` array in `data/raw/bible/bible_scraping_summary.json`
2. **Canon-completeness check** — [scripts/verify_bible_completeness.py](../../scripts/verify_bible_completeness.py) compares `bible.json` against the standard 66-book / 1189-chapter canon and reports missing chapters.

### Safe resumption

`bible.json` and `bible_scraping_summary.json` are written **after every chapter**. On restart, existing entries are loaded and any `story_id` already present is skipped. The full Bible takes several hours; `Ctrl+C` interrupts cleanly without data loss.

### Output schema

```json
{
    "story_id": "bible__gen-1",
    "url_es":  "https://www.bible.com/es-ES/bible/3291/GEN.1.VBL",
    "url_en":  "https://www.bible.com/es-ES/bible/1932/GEN.1.FBV",
    "url_ayo": "https://www.bible.com/es-ES/bible/2825/GEN.1.AYORE",
    "type":    "faith",
    "section": "Génesis",
    "chapter_usfm": "GEN.1",
    "title_es": "Génesis 1", "title_en": "Genesis 1", "title_ayo": "Génesis 1",
    "body_es":  "...", "body_en":  "...", "body_ayo":  "...",
    "body_decomposition": {
        "es":  [{"header": "Génesis 1,1", "text": "..."}],
        "en":  [{"header": "Genesis 1,1", "text": "..."}],
        "ayo": [{"header": "Génesis 1,1", "text": "..."}]
    },
    "warnings": []
}
```

### Storage

- [data/raw/bible/bible.json](../../data/raw/bible/bible.json) — one entry per chapter, keyed by `story_id`
- [data/raw/bible/bible_scraping_summary.json](../../data/raw/bible/bible_scraping_summary.json) — execution log + `mismatches` array
- `aligned_bible.json` — same shape as `bible.json` with a populated `alignment_map`, produced by `scripts/align_bible_llm.py`

### Entry points

```bash
python scripts/scrape_bible.py                  # full run (multi-hour, resumable)
python scripts/scrape_bible.py --test-run       # 2 chapters from current cursor
python scripts/verify_bible_completeness.py     # canon-coverage report
```

### UTF-8 enforcement

The Bible scraper does **not** route through `src/scraping/utils.fetch_page`; it calls `requests.get()` directly inside `extract_chapter_data`. Since the 2026-05-12 fix, that function explicitly sets `response.encoding = "utf-8"` before reading `response.text` to prevent mojibake in Ayoré text. Any future edits to that function must preserve the UTF-8 line.

---

## 3. Production run log

| Date | Source | Section | Items scraped | Notes |
| :--- | :--- | :--- | :--- | :--- |
| 2026-03-01 | ayore.org | `relatos-personales` (ES↔AYO test) | 14 | Earlier ES↔AYO positional-only pairing produced the wrong AYO URL for 13 of 14 stories. Motivated adoption of the WPML corrector that is now used on every page. |

---

## 4. Verification checklist (project-specific)

- [ ] EN+AYO scrape default; `--scrape-es` only when ES is explicitly needed
- [ ] All paired URLs sourced or verified via the WPML switcher on the EN page
- [ ] `story_id` follows `{section_en_slug}__{slug_en}` and is consistent across all language fields
- [ ] Output written to the single `data/raw/ayoreoorg/ayoreoorg.json` — no per-story files
- [ ] AYO URLs preserved with their percent-encoded characters
- [ ] Glossary entries use the `english` key (not `spanish`)
- [ ] All ayore.org HTTP calls go through `src/scraping/utils.fetch_page` (UTF-8 enforced)
- [ ] Bible scraper sets `response.encoding = "utf-8"` in `extract_chapter_data`
- [ ] Bible traversal anchors on AYO; ES/EN URLs derived by version-ID substitution
- [ ] Bible verse-count mismatches logged inline AND in `bible_scraping_summary.json`
- [ ] Bible scraper saves to disk after every chapter (safe resumption)
- [ ] `verify_bible_completeness.py` run after a full Bible scrape to confirm canon coverage
