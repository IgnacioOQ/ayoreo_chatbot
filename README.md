# Ayoreo-English Translation Chatbot

Chatbot de traducción entre la lengua **Ayoreo** (familia Zamuco) y el **Inglés**, con múltiples backends de traducción: RAG + few-shot, red neuronal LoRA, o un híbrido de ambos.

> **Nota sobre el idioma de trabajo:** El pipeline usa **Inglés (EN) como idioma ancla principal** en lugar de Español. Esto se debe a que la traducción inglesa disponible en ayore.org es de mayor calidad semántica, lo que facilita la alineación con el Ayoreo. El scraping de Español (`ES`) es opcional y está desactivado por defecto (`scrape_es: false` en `configs/scraping.yaml`).

## Arquitectura

1. **Data Collection**: Scraping de [ayore.org](https://ayore.org) usando BeautifulSoup y `requests`.
   - Se exploran iterativamente secciones culturales (ej. enseñanzas, relatos) en **EN y AYO** por defecto.
   - Se usa el **widget de idioma WPML** de la página EN para obtener las URLs exactas de la versión AYO, en lugar de emparejar por posición.
   - Se extrae texto principal, glosarios (término Ayoreo → definición en Inglés) y metadatos usando reglas y expresiones regulares (`page_scraper.py`).
   - Se descargan recursos en PDF como diccionarios y gramática pura (`pdf_scraper.py`).
2. **Processing**: Limpieza, alineación de oraciones y construcción de corpus paralelo EN↔AYO.
3. **Semantic Matching**: Alineación semántica a nivel de párrafo entre EN y AYO usando Gemini API (`align_mismatches_llm.py`).
4. **POS Tagging**: Etiquetado morfosintáctico del Ayoreo (híbrido: reglas + transferencia desde inglés).
5. **Traducción — 3 backends disponibles**:
   - **RAG**: Recupera ejemplos similares del corpus → few-shot prompt → Gemini API.
   - **Neural (LoRA)**: Red neuronal adapter entrenada sobre Mistral/LLaMA. El adapter (~1-5% de parámetros) se monta como overhead sobre el LLM congelado y le enseña Ayoreo.
   - **Hybrid**: El modelo LoRA genera una traducción inicial, luego RAG + Gemini la refinan.
6. **UI**: Aplicación Streamlit con modos de traducción, diccionario, POS tagger y chat.

---

## Fuente de datos: ayore.org

[ayore.org](https://ayore.org) es un sitio WordPress que publica textos culturales Ayoreo en **tres idiomas paralelos**: Español (`/es/`), Inglés (sin prefijo) y Ayoré (`/ayo/`). El sitio usa el plugin **WPML** para gestionar las traducciones.

### Estructura de URLs

| Idioma | Patrón de URL | Ejemplo |
| :----- | :------------ | :------ |
| Español | `ayore.org/es/cultura/{sección}/{slug}/` | `.../es/cultura/relatos-personales/cotade.../` |
| Inglés | `ayore.org/culture/{section}/{slug}/` | `.../culture/first-person-narratives/cotade.../` |
| Ayoré | `ayore.org/ayo/culture/{section}/{slug}/` | `.../ayo/culture/first-person-narratives/cotate.../` |

> El Inglés y el Ayoré usan los mismos slugs de sección en inglés, pero el Inglés **no tiene prefijo de idioma** en la URL.

### Secciones de contenido

Cada sección tiene un índice que lista los relatos disponibles. El scraper itera sobre estas secciones:

| Sección (ES) | Sección (EN/AYO) | Tipo |
| :----------- | :--------------- | :--- |
| `cultura/creencias` | `culture/beliefs` | belief |
| `cultura/relatos-personales` | `culture/first-person-narratives` | personal_narrative |
| `cultura/comidas` | `culture/foods` | food |
| `cultura/juegos` | `culture/games` | game |
| `cultura/medicina` | `culture/medicine` | medicine |
| `cultura/canciones-nativas` | `culture/native-songs` | song |
| `cultura/historia-oral` | `culture/oral-history` | oral_history |
| `cultura/tradiciones-orales` | `culture/oral-traditions` | oral_tradition |
| `cultura/ensenanzas` | `culture/teachings` | teaching |

### Estrategia de scraping: indicadores HTML

El scraper usa **indicadores HTML específicos** para navegar el sitio en lugar de heurísticas posicionales:

**1. Descubrimiento de relatos (índice de sección)**

Cada página de índice (ej. `/culture/first-person-narratives/`) contiene una lista `<ul>` con `<li><a href="...">` apuntando a cada relato individual. El crawler recoge todos los `<a href>` dentro del path de la sección y descarta:
- Fragmentos de ancla (`#masthead`, `#content`, etc.) — son enlaces de navegación, no relatos
- La URL del propio índice
- Duplicados

**2. Emparejamiento bilingüe: el widget WPML**

Cada página de relato individual contiene un **widget de cambio de idioma** insertado por WPML. El scraper visita la página EN y lee el widget para obtener la URL exacta de la versión AYO:

```html
<div class="wpml-ls-statics-shortcode_actions wpml-ls wpml-ls-legacy-list-horizontal">
  <ul>
    <li class="wpml-ls-item wpml-ls-item-ayo">
      <a href="https://ayore.org/ayo/culture/.../cotate-e-ye%cc%83ra-yu-to-ome-dupade/" class="wpml-ls-link">
        <span class="wpml-ls-native" lang="ayo">Ayoré</span>
      </a>
    </li>
  </ul>
</div>
```

El scraper lee el atributo `lang` de cada `<span class="wpml-ls-native">` para identificar el idioma y extrae el `href` del `<a class="wpml-ls-link">` correspondiente. Esto da la URL **exacta** de cada versión lingüística del relato.

> **Por qué no se usa emparejamiento posicional:** En producción, el 93% de los relatos (13/14) tenían el orden incorrecto al comparar los índices ES y AYO independientemente. El widget WPML corrigió todos los emparejamientos.

**3. Extracción de contenido**

Dentro de cada página de relato, el contenido principal se encuentra en:
- `div.entry-content` → div principal de WordPress (selector primario)
- `<h1>` → título del relato
- `<p>` y `<blockquote>` dentro del content div → cuerpo del texto
- `<strong>` / `<b>` seguidos de `–` → entradas del glosario (término Ayoreo → definición en Inglés)

### Output

Todos los relatos se guardan inicialmente en un archivo `data/raw/ayoreoorg/ayoreoorg.json`, indexado por `story_id` (ej. `first-person-narratives__cotade-i-gave-myself-to-him`). Posteriormente, el proceso de alineación genera `aligned_ayoreoorg.json` con idéntica estructura que incluye el mapa de alineación semántica.

**💰 Nota sobre Costos de API:** La generación de estos mapas utiliza Gemini. Para minimizar costos, los scripts transforman el payload mediante minificación JSON (`separators=(',', ':')`) y usan `gemini-2.5-flash` con thinking desactivado (`thinking_budget=0`), reduciendo los costos ~95% respecto a modelos Pro.

```json
{
  "first-person-narratives__cotade-i-gave-myself-to-him": {
    "story_id": "first-person-narratives__cotade-i-gave-myself-to-him",
    "url_en": "https://ayore.org/culture/first-person-narratives/cotade-i-gave-myself-to-him/",
    "url_ayo": "https://ayore.org/ayo/culture/first-person-narratives/cotate-e-ye%cc%83ra-yu-to-ome-dupade/",
    "type": "personal_narrative",
    "title_en": "...", "title_ayo": "...",
    "body_en":  "...", "body_ayo":  "...",
    "body_decomposition": {
      "en": [{"header": null, "text": "..."}],
      "ayo": [{"header": null, "text": "..."}]
    },
    "alignment_map": "[{\"en\": [0, 1], \"ayo\": [0]}]"
  }
}
```

> **Alineación Semántica LLM:** Debido a que la segmentación de párrafos puede diferir entre idiomas, el script `scripts/align_mismatches_llm.py` aplica el protocolo definido en `docs/reference/SEMANTIC_MATCHING.md`. Utiliza la API de Gemini para anclar semánticamente el Inglés y alinear heurísticamente los fragmentos opacos en Ayoré. Guarda el resultado con la clave `"alignment_map"` en `aligned_ayoreoorg.json`. Esto se visualiza interactivamente en `sanity_app.py`.

---

## Fuente de datos: Bible.com

Además del contenido cultural de [ayore.org](https://ayore.org), se extrae la **Biblia completa** (todos los libros disponibles traducidos al Ayoré) desde [Bible.com](https://www.bible.com) en tres traducciones paralelas:

| Idioma | Versión | ID | Ejemplo URL |
| :----- | :------ | :- | :---------- |
| Ayoré | Ayore Biblia | `2825` | `bible.com/es-ES/bible/2825/GEN.1.AYORE` |
| Español | La Biblia: La Palabra de Dios para Todos | `3291` | `bible.com/es-ES/bible/3291/GEN.1.VBL` |
| Inglés | Free Bible Version | `1932` | `bible.com/es-ES/bible/1932/GEN.1.FBV` |

### Estrategia de scraping: recorrido encadenado

En lugar de mantener un diccionario de los 66 libros canónicos y sus cantidades de capítulos, el script `scripts/scrape_bible.py` usa una **estrategia de lista enlazada**:

1. Comienza en Génesis 1 (versión Ayoré).
2. Descarga el HTML y extrae versículos usando el atributo `data-usfm` presente en cada `<span>`.
3. Busca el enlace `"Siguiente capítulo"` en la página, que apunta al siguiente capítulo o al primer capítulo del siguiente libro (ej. Génesis 50 → Éxodo 1).
4. Construye automáticamente las URLs equivalentes para Español y English reemplazando el ID de versión y el sufijo.
5. Repite hasta que no haya más enlace "Siguiente capítulo".

Esto garantiza que solo se scrapean capítulos que realmente existen en la traducción Ayoré, sin generar requests a páginas vacías.

### Extracción de versículos

Cada versículo está marcado en el HTML con:
- `data-usfm="GEN.1.1"` → identifica libro, capítulo y versículo
- `<span class="ChapterContent-module__cat7xG__label">1</span>` → número visible del versículo

El scraper elimina los `<span>` de etiqueta antes de extraer el texto, produciendo contenido limpio sin números residuales.

**Versículos fusionados:** La traducción Ayoré a veces combina dos versículos en uno por razones gramaticales o culturales. Bible.com marca estos con `data-usfm="1SA.31.11+1SA.31.12"`. El scraper detecta el `+`, separa las partes, y genera un header con rango (ej. `"1 Samuel 31,11-12"`). El texto completo se preserva.

### Validación y warnings

El script implementa dos capas de validación:

1. **Mismatch de versículos (inline):** Después de extraer cada capítulo en los tres idiomas, se comparan las cantidades de versículos. Si difieren (ej. Ayoré tiene 30 pero Español/Inglés tienen 31), se registra un warning:
   - En el campo `"warnings"` del entry en `bible.json` (para inspección granular)
   - En el array `"mismatches"` de `bible_scraping_summary.json` (para auditoría global)

   > Estos mismatches son informativos, no errores. Reflejan decisiones legítimas de los traductores al fusionar versículos.

2. **Completitud exógena:** El script `scripts/verify_bible_completeness.py` compara `bible.json` contra el canon bíblico estándar (66 libros, 1189 capítulos) y reporta qué capítulos faltan.

### Reanudación segura

El scraping de toda la Biblia toma varias horas. El script guarda `bible.json` a disco después de cada capítulo, y al reiniciarse detecta los capítulos ya almacenados y los salta automáticamente.

### Output

Cada capítulo se almacena como una entrada en `data/raw/bible/bible.json`:

```json
{
  "bible__gen-1": {
    "story_id": "bible__gen-1",
    "url_en": "https://www.bible.com/es-ES/bible/1932/GEN.1.FBV",
    "url_ayo": "https://www.bible.com/es-ES/bible/2825/GEN.1.AYORE",
    "type": "faith",
    "section": "Génesis",
    "chapter_usfm": "GEN.1",
    "title_en": "Genesis 1", "title_ayo": "Génesis 1",
    "body_en": "...", "body_ayo": "...",
    "body_decomposition": {
      "en": [{"header": "Genesis 1,1", "text": "In the beginning..."}],
      "ayo": [{"header": "Génesis 1,1", "text": "Iji taningai uje..."}]
    },
    "warnings": []
  }
}
```

---

## Setup

```bash
# Opción 1: Conda (recomendado)
conda env create -f environment.yml
conda activate ayoreo

# Opción 2: Pip
pip install -e ".[dev]"

# Configurar API key
cp .env.example .env
# Editar .env y reemplazar GOOGLE_API_KEY con tu clave de Gemini
```

---

## Uso

```bash
# Correr la app principal
streamlit run app.py

# Correr la app de sanity check (verificador y anotador del dataset raw)
streamlit run sanity_app.py
```

### Scraping

```bash
# Scraping completo EN+AYO (por defecto, sin Español)
python scripts/run_scraper.py

# Incluir también páginas en Español
python scripts/run_scraper.py --scrape-es

# Scraping de una sección específica
python scripts/run_scraper.py --section first-person-narratives

# Dry run: descubrir páginas sin scrapear
python scripts/run_scraper.py --dry-run

# Solo descargar PDFs
python scripts/run_scraper.py --pdfs-only

# Extracción de la Biblia completa desde Bible.com
python scripts/scrape_bible.py
```

### Alineación semántica

```bash
# Alinear todos los relatos (límite por defecto: 4M tokens por sesión)
python scripts/align_mismatches_llm.py

# Especificar un límite distinto de tokens
python scripts/align_mismatches_llm.py --max-tokens 1000000
```

El script es **reanudable**: al iniciarse crea un backup con timestamp (`aligned_ayoreoorg_backup_2026-03-21_15h30.json`) y salta automáticamente los relatos ya alineados. Muestra dos barras de progreso en tiempo real: una por relatos procesados y otra por tokens consumidos respecto al presupuesto de la sesión.

### Procesamiento

```bash
# Construir corpus paralelo EN↔AYO y splits de entrenamiento
python scripts/run_processing.py
```

### Entrenamiento

```bash
# Entrenar red neuronal (LoRA adapter)
pip install -e ".[training]"
python scripts/run_finetune.py

# Solo preparar datos para Gemini API (sin entrenamiento local)
python scripts/run_finetune.py --gemini-only

# Usar otro modelo base
python scripts/run_finetune.py --base-model meta-llama/Llama-3.1-8B
```

---

## Estructura del proyecto

```
ayoreo_chatbot/
├── app.py                        # Streamlit entry point principal
├── sanity_app.py                 # Streamlit app para verificar y corregir el dataset crudo
├── src/
│   ├── scraping/                 # Scraping de ayore.org
│   │   ├── crawler.py            # Descubrimiento de URLs por sección (EN+AYO por defecto)
│   │   ├── page_scraper.py       # Extracción de contenido + WPML pairing desde página EN
│   │   ├── pdf_scraper.py        # Descarga de PDFs (diccionario, gramática)
│   │   └── utils.py              # HTTP helpers, UTF-8, normalización de URLs
│   ├── processing/               # Limpieza, alineación EN↔AYO, corpus
│   ├── pos_tagging/              # POS tagger para Ayoreo
│   ├── training/                 # LoRA trainer, fine-tuning, evaluación
│   ├── inference/                # Traducción (RAG, LoRA, hybrid), diccionario
│   └── utils/                    # Logging, config
├── data/
│   ├── raw/
│   │   ├── ayoreoorg/            # Datos extraídos de ayore.org (ayoreoorg.json, aligned_ayoreoorg.json)
│   │   ├── bible/                # Biblia completa procedente de Bible.com
│   │   └── pdfs/                 # Diccionario y gramática en PDF
│   ├── processed/                # Corpus paralelo EN↔AYO procesado
│   └── splits/                   # Train/val/test
├── configs/
│   └── scraping.yaml             # Secciones, idiomas, delays, scrape_es flag
├── notebooks/                    # Experimentación
├── prompts/                      # System prompts y templates
├── scripts/
│   ├── run_scraper.py            # Entry point del pipeline de scraping de ayore.org
│   ├── scrape_bible.py           # Scraping de la Biblia desde Bible.com
│   ├── align_mismatches_llm.py   # Alineación semántica EN↔AYO con Gemini (reanudable, con progreso)
│   └── run_processing.py         # Construcción del corpus y splits
├── tests/                        # Tests
└── docs/reference/               # Guías para agentes (HTML_SCRAPING_SKILL.md, SEMANTIC_MATCHING.md, etc.)
```

## Fuentes de datos

- [ayore.org](https://ayore.org) — Textos paralelos EN/AYO, diccionario, gramática
- Ver [fuentes.txt](fuentes.txt) para URLs específicas
- Ver [docs/reference/HTML_SCRAPING_SKILL.md](docs/reference/HTML_SCRAPING_SKILL.md) para detalles técnicos del scraper
- Ver [docs/reference/SEMANTIC_MATCHING.md](docs/reference/SEMANTIC_MATCHING.md) para el protocolo de alineación semántica
