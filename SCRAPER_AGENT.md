# Event Scraper Implementation Guide
- status: active
- type: guideline
<!-- content -->

This document defines the implementation patterns for the MCMP event scraper, including critical lessons learned from production usage.

---

## Event Scraper Implementation

### Primary Source: JSON API
- **Endpoint**: `https://www.philosophie.lmu.de/mcmp/site_tech/json-newsboard/json-events-newsboard-en.json`
- Discovered from the `jsonUrl` attribute of the `LmuNewsboard` Vue component on the events-overview page
- Returns **all events** reliably (54+) without Selenium or dynamic page loading

> [!NOTE]
> The events-overview page is JS-rendered via `LmuNewsboard.init()`. The JSON API bypasses this entirely, making Selenium optional.

### How It Works
1. **Fetch JSON index** from the API — returns all events with `id`, `date`, `dateEnd`, `link.href`, `link.text`
2. **Pre-populate metadata** from API data (`date`, `date_end` for multi-day events)
3. **Scrape individual pages** for full details (speaker, abstract, location, times)
4. **Fallback**: Selenium and static HTML scraping supplement the API for any events it might miss

### API Response Schema
```json
{
    "id": "9216",
    "categoryHeadline": "Event",
    "date": "2026-06-25T00:00:00.000Z",
    "dateEnd": "2026-06-26T00:00:00.000Z",
    "link": {
        "href": "https://...event/the-epistemology-of-medicine-92a34605.html",
        "text": "The Epistemology of Medicine"
    },
    "time": "",
    "topics": [],
    "description": ""
}
```

### Fallback Sources (supplement API)
1. **Selenium** (if available): Clicks "Load more" on events-overview for any events not in the API
2. **Static scraping**: Events page and homepage for events linked outside the newsboard

### Selenium (Legacy Fallback)
The events-overview page uses a "Load more" button for dynamic loading. Selenium clicks it repeatedly to reveal all events. This is now only used as a supplement to the JSON API.

**Dependencies** (optional): `selenium`, `webdriver-manager`

---

## Website Structure

### DOM Structure (Individual Event Pages)
- `<h1>` with speaker/event name
- `<h2>` labels for "Date:", "Location:", "Title:", "Abstract:"
- Location in `<address>` tag

---

## Critical: UTF-8 Encoding

> [!CAUTION]
> The MCMP website serves UTF-8 content (smart quotes like `'`, em dashes, etc.), but `requests` may guess the wrong encoding from HTTP headers, causing **mojibake** (e.g., `'` → `â€™`).

### Problem
- `requests` defaults to `ISO-8859-1` for `text/html` when the server doesn't declare `charset=utf-8`
- UTF-8 multi-byte characters (smart quotes, accented names) decode as garbage

### Solution: `_get()` helper
All HTTP requests go through `self._get(url)`, which forces `response.encoding = 'utf-8'` before `response.text` is accessed:
```python
def _get(self, url):
    """Wrapper around requests.get that forces UTF-8 encoding."""
    response = requests.get(url)
    response.raise_for_status()
    response.encoding = 'utf-8'
    return response
```

> [!IMPORTANT]
> **Never call `requests.get()` directly** in scraping methods. Always use `self._get()`.

---

## Incremental Scraping (Backward Compatibility)

The scraper preserves historical data across runs using `_merge_and_save()`:
- **Events and People**: Merged by URL key. Records from previous scrapes that no longer appear on the website are **retained**. Only matching URLs get updated.
- **Research and General**: **Overwritten** each run (structural merge is too complex for hierarchical category data).

This ensures a growing knowledge base where past events remain queryable even after they leave the website.

---

## Implementation Patterns

### 1. Deduplication (URL-based)
```python
seen_urls = set()
for link in event_links:
    url = self._normalize_url(link['href'])
    if url not in seen_urls:
        seen_urls.add(url)
```

### 2. Event Details Extraction
```python
# Labeled sections
for h2 in soup.find_all('h2'):
    label = h2.get_text(strip=True).rstrip(':').lower()
    if label == 'abstract':
        event['abstract'] = self._extract_section_content(h2)

# Location from address tag
address = soup.find('address')
if address:
    event['metadata']['location'] = address.get_text(' ', strip=True)
```

### 3. Date Parsing
```python
# "4 February 2026" → "2026-02-04"
match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', date_text)
```

---

## Output Schema (Events)
```json
{
    "title": "Talk: Simon Saunders (Oxford)",
    "url": "https://...",
    "talk_title": "Bell inequality violation is evidence for many worlds",
    "abstract": "Given two principles (a) no action-at-a-distance...",
    "metadata": {
        "date": "2026-02-04",
        "date_end": "2026-02-05",
        "time_start": "4:00 pm",
        "location": "Ludwigstr. 31 Ground floor, room 021",
        "speaker": "Simon Saunders (Oxford)"
    }
}
```

---

## People Scraper Implementation

### Sources
- **People Index**: `https://www.philosophie.lmu.de/mcmp/en/people/`
- **Profile Pages**: Individual pages linked from the index (e.g., `/people/contact-page/...`)

### DOM Structure (Profile Page)

| Field | Selector / Logic | Notes |
|-------|------------------|-------|
| **Name** | `h1.header-person__name` | Fallback to `h1` |
| **Position** | `p.header-person__job` | e.g., "Doctoral Fellow" |
| **Org Unit** | `p.header-person__department` | e.g., "Chair of Philosophy of Science" |
| **Email** | `a.header-person__contentlink.is-email` | Strip "Send an email", check `mailto:` |
| **Phone** | `a.header-person__contentlink.is-phone` | |
| **Room** | `div.header-person__detail_area p` | **CRITICAL**: Exclude text containing "Room finder" |
| **Image** | `img.picture__image` | Get `src` attribute |
| **Website** | `a` with text "Personal website" | |
| **Publications** | `h2` "Selected publications" | Parse sibling `ul` or `ol` lists |

### Output Schema
```json
{
    "name": "Dr. Conrad Friedrich",
    "url": "https://...",
    "description": "Personal information...",
    "metadata": {
        "position": "Postdoctoral fellow",
        "organizational_unit": "MCMP",
        "email": "Conrad.Friedrich@lmu.de",
        "office_address": "Ludwigstr. 31",
        "room": "Room 225",
        "website": "https://conradfriedrich.github.io/",
        "image_url": "https://...",
        "selected_publications": ["Pub 1", "Pub 2"]
    }
}
```

---

## News Scraper Implementation

### Source
- **JSON API**: `https://www.philosophie.lmu.de/mcmp/site_tech/json-newsboard/json-news-newsboard-en.json`
- Discovered from the `data-` attributes of the `LmuNewsboard` Vue component on the news-overview page

> [!NOTE]
> The news-overview page (`/latest-news/news-overview/`) is fully JS-rendered via `LmuNewsboard.init()`. Static scraping sees no content. The JSON API endpoint bypasses this entirely.

### How It Works
1. **Fetch JSON index** from the API — returns a list of news items with `id`, `date`, `link.href`, `link.text`
2. **Scrape individual pages** for full content (`div.rte__content` or fallback to `main`)
3. **Store in `data/news.json`** with incremental merge (URL-keyed, like events/people)

### API Response Schema
```json
{
    "id": "11072",
    "categoryHeadline": "News",
    "date": "2026-02-02T14:07:38.628Z",
    "link": {
        "href": "https://...news/call-for-application-phd-student-mfx-b7a800fd.html",
        "text": "Call for Application: PhD student (m/f/x)"
    },
    "topics": [],
    "description": ""
}
```

### Output Schema (`data/news.json`)
```json
{
    "title": "Call for Application: PhD student (m/f/x)",
    "url": "https://...",
    "metadata": {
        "date": "2026-02-02",
        "category": "News"
    },
    "description": "Full text scraped from the individual news page...",
    "type": "news",
    "scraped_at": "2026-02-14T..."
}
```

### Content Types
- Job postings (PhD, postdoc, faculty positions)
- Calls for papers/abstracts
- Award announcements (Karl-Heinz Hoffmann Prize, Kurt Gödel Award)
- Publication announcements
- Partnership announcements

### MCP Tool
Exposed as `search_news(query)` — searches titles and descriptions. Separate from `get_events` since news and events are semantically different.

---

## Verification
- [x] All 54+ events captured via JSON API (no Selenium required)
- [x] Abstracts extracted from individual pages
- [x] No duplicate URLs
- [x] Dates in ISO format
- [x] Multi-day events have `date_end` from API
- [x] UTF-8 encoding enforced (no mojibake in smart quotes/accented characters)
- [x] Past events/people preserved across scraper runs (incremental merge)
- [x] News items scraped from JSON API (bypasses JS-rendered newsboard)
- [x] News stored separately in `data/news.json` with incremental merge
