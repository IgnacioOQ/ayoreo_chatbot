# Web Scraper Implementation Guide
- status: active
- type: agent_skill
- label: [agent]
- last_checked: 2026-03-01
<!-- content -->

This document defines general implementation patterns for web scraping, with specific lessons learned from scraping `ayore.org` (a trilingual WordPress/WPML site).

---

## Core Principle: Find the HTML Indicators
- status: active
<!-- content -->

The key insight of web scraping is that **every piece of target content has an HTML indicator** — a CSS class, attribute, tag structure, or pattern that uniquely identifies it. The scraper's job is to locate that indicator and extract the data around it.

**How to find indicators:**
1. Open DevTools → Inspect the element you want to extract
2. Look for a **unique class or attribute** on the element or its container
3. Check whether the class/attribute is stable (not randomly generated, e.g. not Tailwind hashes or React IDs)
4. Verify it doesn't appear in unrelated parts of the page

**Examples of good indicators:**
- `class="entry-content"` → WordPress main content div
- `class="wpml-ls-item-en"` → WPML language switcher, English link
- `<address>` tag → physical location text
- `<h2>` with text "Abstract:" → labeled section header

**Examples of bad indicators:**
- Generic tags like `<div>`, `<p>` without class attributes
- Positional selectors like `nth-child(3)` — fragile if the page layout changes
- Inline styles or dynamically generated class names

---

## Multi-Language Scraping: The WPML Pattern
- status: active
<!-- content -->

`ayore.org` (and many WordPress sites) use **WPML** (WordPress Multilingual Plugin) to serve the same content in multiple languages. WPML inserts a language switcher widget into each page that links to the exact equivalent URL in every other language.

### Why This Matters

**Do NOT rely on positional pairing** (matching story #1 in ES with story #1 in AYO by crawling index pages independently). This breaks silently if:
- A story exists in one language but not another
- Stories are listed in different orders per language
- New stories are added asynchronously

**Instead: use the WPML switcher on each scraped page** to get the exact URL mapping between language versions.

### WPML Language Switcher HTML

```html
<div class="wpml-ls-statics-shortcode_actions wpml-ls wpml-ls-legacy-list-horizontal">
  <ul>
    <li class="wpml-ls-slot-shortcode_actions wpml-ls-item wpml-ls-item-en wpml-ls-first-item wpml-ls-item-legacy-list-horizontal">
      <a href="https://ayore.org/culture/first-person-narratives/cotade-i-gave-myself-to-him/" class="wpml-ls-link">
        <img class="wpml-ls-flag" src=".../flags/en.png" alt="" width=18 height=12 />
        <span class="wpml-ls-native" lang="en">English</span>
      </a>
    </li>
    <li class="wpml-ls-slot-shortcode_actions wpml-ls-item wpml-ls-item-ayo wpml-ls-last-item wpml-ls-item-legacy-list-horizontal">
      <a href="https://ayore.org/ayo/culture/first-person-narratives/cotate-e-ye%cc%83ra-yu-to-ome-dupade/" class="wpml-ls-link">
        <img class="wpml-ls-flag" src=".../flags/ayo.jpg" alt="" width=18 height=12 />
        <span class="wpml-ls-native" lang="ayo">Ayoré</span>
      </a>
    </li>
  </ul>
</div>
```

### Key Observations

| Indicator | Meaning |
| :--- | :--- |
| `div.wpml-ls` | Container for the entire language switcher |
| `li.wpml-ls-item-{lang}` | One language option (e.g. `wpml-ls-item-en`, `wpml-ls-item-ayo`) |
| `a.wpml-ls-link` | The link to that language version — contains the target URL |
| `span.wpml-ls-native[lang="en"]` | The `lang` attribute identifies which language |

> [!IMPORTANT]
> The switcher shows only the **other** languages, not the current page's language. If you are on the ES page, the switcher lists EN and AYO — not ES.

### Python: Extract Language URLs from WPML Switcher

```python
def extract_language_urls(soup) -> dict[str, str]:
    """Extract URLs for all language versions from the WPML switcher.

    Call this on any already-scraped page to get the exact sibling URLs.
    The returned dict keys are language codes ('en', 'ayo', 'es', etc.).
    The current page's language is NOT included (WPML only shows others).
    """
    urls = {}
    switcher = soup.find("div", class_="wpml-ls")
    if not switcher:
        return urls
    for li in switcher.find_all("li", class_="wpml-ls-item"):
        span = li.find("span", class_="wpml-ls-native")
        a = li.find("a", class_="wpml-ls-link")
        if span and a:
            lang = span.get("lang")   # e.g. "en", "ayo"
            href = a.get("href")
            if lang and href:
                urls[lang] = href
    return urls
```

### Recommended Crawl Strategy

1. **Crawl the ES index** to get all Spanish story URLs (ES is always the most complete)
2. **For each ES story page**, fetch the page and call `extract_language_urls()` to get the exact EN and AYO URLs
3. **Store all three** under a shared `story_id` (use the ES slug as canonical key)

This is more reliable than crawling three index pages and pairing by position.

---

## ayore.org: Site Structure
- status: active
<!-- content -->

`ayore.org` is a WordPress site serving trilingual content (Spanish, English, Ayoré).

### URL Structure

| Language | URL pattern | Notes |
| :--- | :--- | :--- |
| Spanish | `https://ayore.org/es/cultura/{section}/{slug}/` | Always present |
| English | `https://ayore.org/culture/{section}/{slug}/` | **No lang prefix** |
| Ayoré | `https://ayore.org/ayo/culture/{section}/{slug}/` | `ayo/` prefix |

> [!NOTE]
> English and Ayoré share the same section-path slugs (e.g. `culture/first-person-narratives`), but English has no language prefix in the URL. Spanish uses different, Spanish-language slugs (e.g. `cultura/relatos-personales`).

### Content Sections

| ES path | EN/AYO path | Type |
| :--- | :--- | :--- |
| `cultura/relatos-personales` | `culture/first-person-narratives` | narrative |
| `cultura/ensenanzas` | `culture/teachings` | narrative |
| `cultura/historia-oral` | `culture/oral-history` | narrative |
| `cultura/tradiciones-orales` | `culture/oral-traditions` | narrative |
| `cultura/creencias` | `culture/beliefs` | narrative |
| `cultura/canciones-nativas` | `culture/native-songs` | song |
| `cultura/juegos` | `culture/games` | narrative |
| `cultura/comidas` | `culture/foods` | narrative |
| `cultura/medicina` | `culture/medicine` | narrative |

### WordPress Content DOM

| Element | Selector | Notes |
| :--- | :--- | :--- |
| Main content | `div.entry-content` | Primary WordPress content div |
| Fallback | `article`, `div.post-content`, `main` | Try in order |
| Page title | `h1` | First `<h1>` on page |
| Body text | `p`, `blockquote` within content div | Skip fragments < 10 chars |
| Glossary terms | `strong`/`b` + sibling text with `–` or `-` | Ayoreo term → Spanish definition |

### Metadata Patterns (regex)

```python
# Narrator
r"(?:Narr?ador|Narrator|Narrated by)[:\s]+(.+?)(?:\n|$)"

# Location + year
r"(?:Campo Loro|Tobité|Zapocó|Santa Cruz|Poza Verde|Rincón del Tigre)[,\s]+(?:Bolivia|Paraguay)[,\s]*(\d{4})?"

# Transcriber / translator
r"(?:Transcri(?:bed|to) (?:by|por))[:\s]+(.+?)(?:\n|$)"
r"(?:Translat(?:ed|ado) (?:to Spanish )?(?:by|por))[:\s]+(.+?)(?:\n|$)"
```

### Output Schema per Story

```json
{
    "story_id": "relatos-personales__cotade-me-he-entregado-dupade",
    "url_es":  "https://ayore.org/es/cultura/relatos-personales/cotade-me-he-entregado-dupade/",
    "url_en":  "https://ayore.org/culture/first-person-narratives/cotade-i-gave-myself-to-him/",
    "url_ayo": "https://ayore.org/ayo/culture/first-person-narratives/cotate-e-ye%cc%83ra-yu-to-ome-dupade/",
    "section": "relatos-personales",
    "type": "narrative",
    "title_es": "...", "title_en": "...", "title_ayo": "...",
    "body_es":  "...", "body_en":  "...", "body_ayo":  "...",
    "glossary": [{"ayoreo": "Dupade", "spanish": "Dios"}],
    "metadata": {
        "narrator": "Cotade",
        "location": "Campo Loro, Paraguay",
        "year": "1985",
        "transcriber": "Maxine Morarie"
    },
    "scraped_at": "2026-03-01T..."
}
```

---

## Critical: UTF-8 Encoding
- status: active
<!-- content -->

> [!CAUTION]
> `requests` may guess the wrong encoding from HTTP headers, causing **mojibake** (e.g. `'` → `â€™`). This is especially damaging for Ayoreo text, which contains non-ASCII characters.

Always force UTF-8 before accessing `response.text`:

```python
def fetch_page(url: str) -> BeautifulSoup | None:
    response = requests.get(url, headers={"User-Agent": "..."})
    response.raise_for_status()
    response.encoding = "utf-8"   # Force before .text is accessed
    return BeautifulSoup(response.text, "lxml")
```

> [!IMPORTANT]
> **Never call `requests.get()` directly** in scraping methods. Always use the `fetch_page()` wrapper that enforces UTF-8.

---

## Implementation Patterns
- status: active
<!-- content -->

### 1. URL Deduplication

```python
seen_urls = set()
for a_tag in soup.find_all("a", href=True):
    url = normalize_url(a_tag["href"], base_url)
    if url in seen_urls:
        continue
    seen_urls.add(url)
```

### 2. Language Guard (for no-prefix English URLs)

When crawling the English index (no `/en/` prefix), AYO and ES sibling links will also contain the section path. Filter them out by checking the URL's language prefix:

```python
from src.scraping.utils import get_language_from_url

url_lang = get_language_from_url(href)  # returns "es", "ayo", "en", or None
if lang is None and url_lang is not None:
    continue  # skip ES/AYO links when collecting English pages
if lang is not None and url_lang != lang:
    continue  # skip links from other languages
```

### 3. Incremental Scraping

Merge new scrape results with existing data by URL key, so historical records are retained:

```python
existing = json.loads(path.read_text()) if path.exists() else {}
for item in new_items:
    existing[item["url_es"]] = item   # update or add
path.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
```

---

## Verification Checklist
- status: active
<!-- content -->

- [ ] All three language versions discovered for each story
- [ ] Language URLs sourced from WPML switcher (not positional pairing)
- [ ] UTF-8 encoding enforced — no mojibake in Ayoreo/Spanish text
- [ ] `story_id` present and consistent across all three language versions
- [ ] Glossary extracted from ES pages
- [ ] Metadata (narrator, location, year) extracted where present
- [ ] No duplicate URLs within a section
- [ ] Empty/boilerplate pages flagged with a warning log
