# Ayoreo-Spanish Translation Chatbot

Chatbot de traducción entre la lengua **Ayoreo** (familia Zamuco) y el **Español**, con múltiples backends de traducción: RAG + few-shot, red neuronal LoRA, o un híbrido de ambos.

## Arquitectura

1. **Data Collection**: Scraping de [ayore.org](https://ayore.org) para obtener textos paralelos Ayoreo-Español, diccionario y gramática.
2. **Processing**: Limpieza, alineación de oraciones y construcción de corpus paralelo.
3. **POS Tagging**: Etiquetado morfosintáctico del Ayoreo (híbrido: reglas + transferencia desde español).
4. **Traducción — 3 backends disponibles**:
   - **RAG**: Recupera ejemplos similares del corpus → few-shot prompt → Gemini API.
   - **Neural (LoRA)**: Red neuronal adapter entrenada sobre Mistral/LLaMA. El adapter (~1-5% de parámetros) se monta como overhead sobre el LLM congelado y le enseña Ayoreo.
   - **Hybrid**: El modelo LoRA genera una traducción inicial, luego RAG + Gemini la refinan.
5. **UI**: Aplicación Streamlit con modos de traducción, diccionario, POS tagger y chat.

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
├── app.py                        # Streamlit entry point
├── src/
│   ├── scraping/                 # Scraping de ayore.org
│   ├── processing/               # Limpieza, alineación, corpus
│   ├── pos_tagging/              # POS tagger para Ayoreo
│   ├── training/                 # LoRA trainer, fine-tuning, evaluación
│   ├── inference/                # Traducción (RAG, LoRA, hybrid), diccionario
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
