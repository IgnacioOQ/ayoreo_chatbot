"""Ayoreo-English Translation Chatbot — Streamlit application."""

import streamlit as st

st.set_page_config(
    page_title="Ayoreo Translator",
    page_icon="🗣️",
    layout="wide",
)


def render_translation_ui():
    """Translation mode: bidirectional Ayoreo ↔ English."""
    st.header("Translation")

    direction = st.radio(
        "Direction",
        ["Ayoreo → English", "English → Ayoreo"],
        horizontal=True,
    )
    dir_code = "ayo_to_en" if "Ayoreo →" in direction else "en_to_ayo"

    input_text = st.text_area(
        "Text to translate",
        height=150,
        placeholder="Enter text here...",
    )

    if st.button("Translate", type="primary") and input_text.strip():
        with st.spinner("Translating..."):
            try:
                engine = get_engine(st.session_state.get("backend", "rag"))
                result = engine.translate(input_text, direction=dir_code)
                st.success("Translation:")
                st.write(result)
            except Exception as e:
                st.error(f"Error: {e}")


def render_dictionary_ui():
    """Dictionary mode: search Ayoreo words."""
    st.header("Dictionary")

    query = st.text_input("Search word", placeholder="Enter an Ayoreo word...")

    if query.strip():
        try:
            engine = get_engine()
            results = engine.search_dictionary(query)
            if results:
                for entry in results:
                    hw = entry.get("headword", entry.get("ayoreo", ""))
                    defn = entry.get("definition_en", entry.get("english", ""))
                    pos = entry.get("pos", "")
                    st.markdown(f"**{hw}** {f'({pos})' if pos else ''} — {defn}")
            else:
                st.info("No results found.")
        except Exception as e:
            st.error(f"Error: {e}")


def render_pos_ui():
    """POS Tagger mode: tag Ayoreo text."""
    st.header("POS Tagger")

    text = st.text_area(
        "Ayoreo text",
        height=100,
        placeholder="Enter Ayoreo text to analyze...",
    )

    if st.button("Analyze") and text.strip():
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

    if prompt := st.chat_input("Ask about the Ayoreo language..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # TODO: Implement chat with Gemini + tools
                response = "Chat mode coming soon. Use Translation mode for now."
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
    st.title("Ayoreo ↔ English")
    st.caption("Translation chatbot for the Ayoreo language")

    with st.sidebar:
        st.header("Mode")
        mode = st.radio(
            "Select mode",
            ["Translation", "Dictionary", "POS Tagger", "Chat"],
            label_visibility="collapsed",
        )

        st.divider()
        st.header("Backend")
        backend = st.radio(
            "Translation engine",
            ["RAG + Gemini", "Neural (LoRA)", "Hybrid (Neural + RAG)"],
            help=(
                "**RAG**: Retrieves similar examples and uses Gemini API.\n\n"
                "**Neural**: Uses the locally trained LoRA adapter.\n\n"
                "**Hybrid**: Neural translates, Gemini refines with RAG examples."
            ),
            label_visibility="collapsed",
        )
        backend_map = {
            "RAG + Gemini": "rag",
            "Neural (LoRA)": "neural",
            "Hybrid (Neural + RAG)": "hybrid",
        }
        st.session_state["backend"] = backend_map[backend]

    if mode == "Translation":
        render_translation_ui()
    elif mode == "Dictionary":
        render_dictionary_ui()
    elif mode == "POS Tagger":
        render_pos_ui()
    elif mode == "Chat":
        render_chat_ui()


if __name__ == "__main__":
    main()
