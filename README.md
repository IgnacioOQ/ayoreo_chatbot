# Ayoreo-Spanish Translation Chatbot

Chatbot de traducción entre la lengua **Ayoreo** (familia Zamuco) y el **Español**, con múltiples backends de traducción: RAG + few-shot, red neuronal LoRA, o un híbrido de ambos.

## Arquitectura

1. **Data Collection**: Scraping de [ayore.org](https://ayore.org) usando BeautifulSoup y `requests`.
   - Se exploran iterativamente secciones culturales (ej. enseñanzas, relatos) en los tres idiomas.
   - Se usa el **widget de idioma WPML** de cada página para obtener las URLs exactas de las versiones EN y AYO, en lugar de emparejar por posición.
   - Se extrae texto principal, glosarios y metadatos (narrador, año, ubicación) usando reglas y expresiones regulares (`page_scraper.py`).
   - Se descargan recursos en PDF como diccionarios y gramática pura (`pdf_scraper.py`).
2. **Processing**: Limpieza, alineación de oraciones y construcción de corpus paralelo.
3. **POS Tagging**: Etiquetado morfosintáctico del Ayoreo (híbrido: reglas + transferencia desde español).
4. **Traducción — 3 backends disponibles**:
   - **RAG**: Recupera ejemplos similares del corpus → few-shot prompt → Gemini API.
   - **Neural (LoRA)**: Red neuronal adapter entrenada sobre Mistral/LLaMA. El adapter (~1-5% de parámetros) se monta como overhead sobre el LLM congelado y le enseña Ayoreo.
   - **Hybrid**: El modelo LoRA genera una traducción inicial, luego RAG + Gemini la refinan.
5. **UI**: Aplicación Streamlit con modos de traducción, diccionario, POS tagger y chat.

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

Cada página de índice (ej. `/es/cultura/relatos-personales/`) contiene una lista `<ul>` con `<li><a href="...">` apuntando a cada relato individual. El crawler recoge todos los `<a href>` dentro del path de la sección y descarta:
- Fragmentos de ancla (`#masthead`, `#content`, etc.) — son enlaces de navegación, no relatos
- La URL del propio índice
- Duplicados

**2. Emparejamiento trilingüe: el widget WPML**

Cada página de relato individual contiene un **widget de cambio de idioma** insertado por WPML:

```html
<div class="wpml-ls-statics-shortcode_actions wpml-ls wpml-ls-legacy-list-horizontal">
  <ul>
    <li class="wpml-ls-item wpml-ls-item-en">
      <a href="https://ayore.org/culture/.../cotade-i-gave-myself-to-him/" class="wpml-ls-link">
        <span class="wpml-ls-native" lang="en">English</span>
      </a>
    </li>
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
- `<strong>` / `<b>` seguidos de `–` → entradas del glosario (término Ayoreo → definición)

### Output

Todos los relatos se guardan en un único archivo `data/raw/ayoreoorg.json`, indexado por `story_id` (ej. `relatos-personales__cotade-me-he-entregado-dupade`). Cada entrada contiene el texto en los tres idiomas, junto con el contenido particionado estructuralmente:

```json
{
  "relatos-personales__cotade-me-he-entregado-dupade": {
    "story_id": "relatos-personales__cotade-me-he-entregado-dupade",
    "url_es": "https://ayore.org/es/cultura/relatos-personales/cotade-me-he-entregado-dupade/",
    "url_en": "https://ayore.org/culture/first-person-narratives/cotade-i-gave-myself-to-him/",
    "url_ayo": "https://ayore.org/ayo/culture/first-person-narratives/cotate-e-ye%cc%83ra-yu-to-ome-dupade/",
    "type": "personal_narrative",
    "title_es": "...", "title_en": "...", "title_ayo": "...",
    "body_es":  "...", "body_en":  "...", "body_ayo":  "...",
    "body_decomposition": {
      "es": [{"header": null, "text": "..."}],
      "en": [{"header": null, "text": "..."}],
      "ayo": [{"header": null, "text": "..."}]
    },
    ...
  }
}
```

---

## Setup

```bash
# Opción 1: Conda
conda env create -f environment.yml
conda activate ayoreo

# Opción 2: Pip
pip install -e ".[dev]"

# Configurar API key
cp .env.example .env
# Editar .env con tu GOOGLE_API_KEY
```

## Uso

```bash
# Correr la app principal
streamlit run app.py

# Correr la app de sanity check (verificador y anotador del dataset raw)
streamlit run sanity_app.py

# Scraping completo (todas las secciones)
python scripts/run_scraper.py

# Scraping de una sección específica
python scripts/run_scraper.py --section relatos-personales

# Dry run: descubrir páginas sin scrapear
python scripts/run_scraper.py --dry-run

# Procesar datos
python scripts/run_processing.py

# Entrenar red neuronal (LoRA adapter)
pip install -e ".[training]"
python scripts/run_finetune.py

# Solo preparar datos para Gemini API (sin entrenamiento local)
python scripts/run_finetune.py --gemini-only

# Usar otro modelo base
python scripts/run_finetune.py --base-model meta-llama/Llama-3.1-8B
```

## Estructura del proyecto

```
ayoreo_chatbot/
├── app.py                        # Streamlit entry point principal
├── sanity_app.py                 # Streamlit app para verificar y corregir el dataset crudo
├── src/
│   ├── scraping/                 # Scraping de ayore.org
│   │   ├── crawler.py            # Descubrimiento de URLs por sección
│   │   ├── page_scraper.py       # Extracción de contenido + WPML pairing
│   │   ├── pdf_scraper.py        # Descarga de PDFs (diccionario, gramática)
│   │   └── utils.py              # HTTP helpers, UTF-8, normalización de URLs
│   ├── processing/               # Limpieza, alineación, corpus
│   ├── pos_tagging/              # POS tagger para Ayoreo
│   ├── training/                 # LoRA trainer, fine-tuning, evaluación
│   ├── inference/                # Traducción (RAG, LoRA, hybrid), diccionario
│   └── utils/                    # Logging, config
├── data/
│   ├── raw/
│   │   ├── stories.json          # Todos los relatos (3 idiomas, indexados por story_id)
│   │   └── pdfs/                 # Diccionario y gramática en PDF
│   ├── processed/                # Corpus procesado
│   └── splits/                   # Train/val/test
├── configs/
│   └── scraping.yaml             # Secciones, idiomas, delays
├── notebooks/                    # Experimentación
├── prompts/                      # System prompts y templates
├── scripts/
│   └── run_scraper.py            # Entry point del pipeline de scraping
├── tests/                        # Tests
└── docs/reference/               # Guías para agentes (HTML_SCRAPING_SKILL.md, etc.)
```

## Fuentes de datos

- [ayore.org](https://ayore.org) — Textos paralelos ES/EN/AYO, diccionario, gramática
- Ver [fuentes.txt](fuentes.txt) para URLs específicas
- Ver [docs/reference/HTML_SCRAPING_SKILL.md](docs/reference/HTML_SCRAPING_SKILL.md) para detalles técnicos del scraper
