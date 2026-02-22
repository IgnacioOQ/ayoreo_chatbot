"""Ayoreo-Spanish Translation Chatbot — Streamlit application."""

import streamlit as st

st.set_page_config(
    page_title="Ayoreo Translator",
    page_icon="🗣️",
    layout="wide",
)


def render_translation_ui():
    """Translation mode: bidirectional Ayoreo ↔ Spanish."""
    st.header("Traducción")

    direction = st.radio(
        "Dirección",
        ["Ayoreo → Español", "Español → Ayoreo"],
        horizontal=True,
    )
    dir_code = "ayo_to_es" if "Ayoreo →" in direction else "es_to_ayo"

    input_text = st.text_area(
        "Texto a traducir",
        height=150,
        placeholder="Escribí el texto acá...",
    )

    if st.button("Traducir", type="primary") and input_text.strip():
        with st.spinner("Traduciendo..."):
            try:
                engine = get_engine(st.session_state.get("backend", "rag"))
                result = engine.translate(input_text, direction=dir_code)
                st.success("Traducción:")
                st.write(result)
            except Exception as e:
                st.error(f"Error: {e}")


def render_dictionary_ui():
    """Dictionary mode: search Ayoreo words."""
    st.header("Diccionario")

    query = st.text_input("Buscar palabra", placeholder="Escribí una palabra en Ayoreo...")

    if query.strip():
        try:
            engine = get_engine()
            results = engine.search_dictionary(query)
            if results:
                for entry in results:
                    hw = entry.get("headword", entry.get("ayoreo", ""))
                    defn = entry.get("definition_es", entry.get("spanish", ""))
                    pos = entry.get("pos", "")
                    st.markdown(f"**{hw}** {f'({pos})' if pos else ''} — {defn}")
            else:
                st.info("No se encontraron resultados.")
        except Exception as e:
            st.error(f"Error: {e}")


def render_pos_ui():
    """POS Tagger mode: tag Ayoreo text."""
    st.header("POS Tagger")

    text = st.text_area(
        "Texto en Ayoreo",
        height=100,
        placeholder="Escribí texto en Ayoreo para analizar...",
    )

    if st.button("Analizar") and text.strip():
        try:
            engine = get_engine()
            tagged = engine.pos_tag(text)
            # Display as colored tokens
            html_parts = []
            colors = {
                "NOUN": "#4CAF50", "VERB": "#2196F3", "ADJ": "#FF9800",
                "ADV": "#9C27B0", "PRON": "#00BCD4", "PROPN": "#4CAF50",
                "X": "#9E9E9E",
            }
            for token, tag in tagged:
                color = colors.get(tag, "#9E9E9E")
                html_parts.append(
                    f'<span style="background-color:{color};color:white;'
                    f'padding:2px 6px;border-radius:4px;margin:2px;">'
                    f'{token}<sub>{tag}</sub></span>'
                )
            st.markdown(" ".join(html_parts), unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error: {e}")


def render_chat_ui():
    """Chat mode: conversational language learning."""
    st.header("Chat")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Preguntá sobre el idioma Ayoreo..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                # TODO: Implement chat with Gemini + tools
                response = "Chat mode coming soon. Usá el modo Traducción por ahora."
                st.write(response)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )


@st.cache_resource
def get_engine(backend: str = "rag"):
    """Initialize and cache the translation engine."""
    from src.inference.engine import TranslationEngine
    return TranslationEngine(backend=backend)


def main():
    st.title("Ayoreo ↔ Español")
    st.caption("Chatbot de traducción para la lengua Ayoreo")

    with st.sidebar:
        st.header("Modo")
        mode = st.radio(
            "Seleccionar modo",
            ["Traducción", "Diccionario", "POS Tagger", "Chat"],
            label_visibility="collapsed",
        )

        st.divider()
        st.header("Backend")
        backend = st.radio(
            "Motor de traducción",
            ["RAG + Gemini", "Neural (LoRA)", "Hybrid (Neural + RAG)"],
            help=(
                "**RAG**: Recupera ejemplos similares y usa Gemini API.\n\n"
                "**Neural**: Usa el modelo LoRA entrenado localmente.\n\n"
                "**Hybrid**: Neural traduce, Gemini refina con ejemplos RAG."
            ),
            label_visibility="collapsed",
        )
        backend_map = {
            "RAG + Gemini": "rag",
            "Neural (LoRA)": "neural",
            "Hybrid (Neural + RAG)": "hybrid",
        }
        st.session_state["backend"] = backend_map[backend]

    if mode == "Traducción":
        render_translation_ui()
    elif mode == "Diccionario":
        render_dictionary_ui()
    elif mode == "POS Tagger":
        render_pos_ui()
    elif mode == "Chat":
        render_chat_ui()


if __name__ == "__main__":
    main()
