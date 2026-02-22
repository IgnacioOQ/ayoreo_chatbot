# Ayoreo-Spanish Translation Chatbot

Chatbot de traducción entre la lengua **Ayoreo** (familia Zamuco) y el **Español**, usando RAG + few-shot prompting sobre Google Gemini.

## Arquitectura

1. **Data Collection**: Scraping de [ayore.org](https://ayore.org) para obtener textos paralelos Ayoreo-Español, diccionario y gramática.
2. **Processing**: Limpieza, alineación de oraciones y construcción de corpus paralelo.
3. **POS Tagging**: Etiquetado morfosintáctico del Ayoreo (híbrido: reglas + transferencia desde español).
4. **Translation**: RAG + few-shot prompting — se recuperan ejemplos similares del corpus y se envían como contexto al LLM.
5. **Fine-tuning** (opcional): Ajuste fino sobre modelo open-source o vía API.
6. **UI**: Aplicación Streamlit con modos de traducción, diccionario, POS tagger y chat.

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
# Correr la app
streamlit run app.py

# Scraping
python scripts/run_scraper.py

# Procesar datos
python scripts/run_processing.py
```

## Estructura del proyecto

```
ayoreo_chatbot/
├── app.py                        # Streamlit entry point
├── src/
│   ├── scraping/                 # Scraping de ayore.org
│   ├── processing/               # Limpieza, alineación, corpus
│   ├── pos_tagging/              # POS tagger para Ayoreo
│   ├── training/                 # Fine-tuning y evaluación
│   ├── inference/                # Traducción, RAG, diccionario
│   └── utils/                    # Logging, config
├── data/
│   ├── raw/                      # Datos crudos (scrapeados)
│   ├── processed/                # Corpus procesado
│   └── splits/                   # Train/val/test
├── configs/                      # Configuraciones YAML
├── notebooks/                    # Experimentación
├── prompts/                      # System prompts y templates
├── scripts/                      # Entry points de pipelines
├── tests/                        # Tests
└── docs/reference/               # Markdown de referencia (proyecto anterior)
```

## Fuentes de datos

- [ayore.org](https://ayore.org) — Textos paralelos, diccionario, gramática
- Ver [fuentes.txt](fuentes.txt) para URLs específicas
