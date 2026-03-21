import streamlit as st
import json
from pathlib import Path

st.set_page_config(
    page_title="Ayoreo Dataset Sanity Check",
    page_icon="🔎",
    layout="wide"
)

# Constants
PROJECT_ROOT = Path(__file__).resolve().parent
DATASETS = {
    "Ayoreo.org (Scraped)": {
        "json": PROJECT_ROOT / "data" / "raw" / "ayoreoorg" / "ayoreoorg.json",
        "aligned": PROJECT_ROOT / "data" / "raw" / "ayoreoorg" / "aligned_ayoreoorg.json"
    },
    "Bibles (YouVersion)": {
        "json": PROJECT_ROOT / "data" / "raw" / "bible" / "bible.json",
        "aligned": PROJECT_ROOT / "data" / "raw" / "bible" / "aligned_bible.json"
    }
}

# --- 1. State Management & Loading ---
@st.cache_data
def load_dataset(dataset_name: str) -> dict:
    paths = DATASETS[dataset_name]
    load_path = paths["aligned"] if paths["aligned"].exists() else paths["json"]
    if not load_path.exists():
        st.error(f"Dataset not found at {load_path}")
        return {}
    with open(load_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_dataset(dataset_name: str, data: dict):
    paths = DATASETS[dataset_name]
    with open(paths["aligned"], "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    # Clear cache so next potential reload pulls the updated file natively
    load_dataset.clear()

if "dataset" not in st.session_state:
    st.session_state.dataset = load_dataset(list(DATASETS.keys())[0])

# Wait for sidebar selection to render the rest
dataset = None

# Helper to check for mismatched decomposition lengths
def has_mismatch(entry) -> bool:
    deco = entry.get("body_decomposition", {})
    counts = [len(deco.get(lang, [])) for lang in ["en", "ayo"]]
    return len(set(counts)) > 1

# --- 2. Sidebar Navigation ---
with st.sidebar:
    st.title("🔎 Dataset Explorer")
    st.markdown("Filter and select stories from the scraped datasets to sanity-check their contents and submit structural corrections.")
    
    st.markdown("---")
    st.header("1. Select Dataset")
    selected_dataset = st.selectbox("Dataset Source", list(DATASETS.keys()))
    
    # Load dynamically based on sidebar
    st.session_state.dataset = load_dataset(selected_dataset)
    dataset = st.session_state.dataset

    if not dataset:
        st.stop()
        
    # Build filtering tuples dynamically
    unique_sections = sorted(list(set(v.get("section", "unknown") for v in dataset.values())))

    st.markdown("---")
    st.header("2. Filters")
    
    selected_section = st.selectbox("Section", ["All"] + unique_sections)
    
    # Filter dataset
    filtered_keys = []
    for k, v in dataset.items():
        match_sec = (selected_section == "All" or v.get("section") == selected_section)
        if match_sec:
            filtered_keys.append(k)
            
    st.markdown("---")
    st.header(f"Stories ({len(filtered_keys)})")
    
    if not filtered_keys:
        st.warning("No stories match the current filters.")
        st.stop()
        
    def format_story_label(key):
        return f"⚠️ {key}" if has_mismatch(dataset[key]) else key
        
    selected_key = st.selectbox("Select a Story to View", filtered_keys, format_func=format_story_label)

# --- 3. Main Data Visualization Area ---
story = dataset[selected_key]

st.title(story.get("title_en", "Untitled Story"))

# Metadata row
mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
meta = story.get("metadata", {})
with mcol1: st.metric("Type", story.get("type", "N/A"))
with mcol2: st.metric("Section", story.get("section", "N/A"))
with mcol3: st.metric("Narrator", meta.get("narrator", "Unknown"))
with mcol4: st.metric("Location", meta.get("location", "Unknown"))
with mcol5: st.metric("Year", meta.get("year", "Unknown"))

st.markdown("---")

# Visualizing Text Bodies natively
tcol1, tcol2 = st.columns(2)
with tcol1:
    st.subheader("🇬🇧 English")
    st.markdown(f"**URL:** [link]({story.get('url_en', '')})")
    st.text_area("Body", story.get("body_en", ""), height=300, disabled=True, key=f"raw_body_en_{selected_key}")
with tcol2:
    st.subheader("🏹 Ayoré")
    st.markdown(f"**URL:** [link]({story.get('url_ayo', '')})")
    st.text_area("Body", story.get("body_ayo", ""), height=300, disabled=True, key=f"raw_body_ayo_{selected_key}")

# Visualizing Decompositions
def format_decomp(decomp_list):
    """Add explicit index [i] to the header for easier reference in alignment."""
    if not isinstance(decomp_list, list): return []
    return [{"index": i, **item} for i, item in enumerate(decomp_list)]

st.markdown("### 🧩 Body Decomposition")
decomp = story.get("body_decomposition", {})

tab_en, tab_ayo, tab_parallel = st.tabs(["English", "Ayoré", "Parallel (Aligned)"])
with tab_en:
    st.json(format_decomp(decomp.get("en", [])), expanded=False)
with tab_ayo:
    st.json(format_decomp(decomp.get("ayo", [])), expanded=False)
with tab_parallel:
    dec_en = decomp.get("en", [])
    dec_ayo = decomp.get("ayo", [])

    alignment_str = story.get("alignment_map")

    if alignment_str:
        try:
            amap = json.loads(alignment_str) if isinstance(alignment_str, str) else alignment_str
            parallel_view = []
            for i, group in enumerate(amap):
                g_en = [dec_en[idx] for idx in group.get("en", []) if idx < len(dec_en)]
                g_ayo = [dec_ayo[idx] for idx in group.get("ayo", []) if idx < len(dec_ayo)]

                parallel_view.append({
                    "group": i,
                    "en": g_en if g_en else None,
                    "ayo": g_ayo if g_ayo else None
                })
            st.json(parallel_view, expanded=False)
        except Exception as e:
            st.error(f"Error parsing alignment map: {e}")
            st.code(alignment_str)
    else:
        # Fallback naive parallel array based on max length
        max_len = max(len(dec_en), len(dec_ayo))
        parallel_view = []
        for i in range(max_len):
            parallel_view.append({
                "index": i,
                "en": dec_en[i] if i < len(dec_en) else None,
                "ayo": dec_ayo[i] if i < len(dec_ayo) else None
            })
        st.json(parallel_view, expanded=False)

st.markdown("---")

# --- 4. Annotation & Corrections Area ---
st.header("📝 Editor Corrections")
st.markdown("Use this form to add notes or correct the raw scraped bodies. Your inputs will be saved into the JSON under new `correction` keys so the raw text is never lost.")

with st.form("correction_form"):
    alignment_str = st.text_area(
        "Alignment Map (JSON/Text)", 
        value=story.get("alignment_map", ""),
        height=100,
        help="e.g. {\"es\": [0,1], \"en\": [0], \"ayo\": [0]}",
        key=f"align_{selected_key}"
    )
    st.markdown("---")

    ccol1, ccol2 = st.columns(2)

    # Pre-fill with existing corrections if they exist, otherwise default to the current raw body
    with ccol1:
        corr_en = st.text_area(
            "Corrected English",
            value=story.get("corrected_body_en", story.get("body_en", "")),
            height=250,
            key=f"corr_en_{selected_key}"
        )
    with ccol2:
        corr_ayo = st.text_area(
            "Corrected Ayoré",
            value=story.get("corrected_body_ayo", story.get("body_ayo", "")),
            height=250,
            key=f"corr_ayo_{selected_key}"
        )
        
    comment_text = st.text_area("Editor Comments / Notes", value=story.get("correction_notes", ""), height=100, key=f"notes_{selected_key}")
    
    submitted = st.form_submit_button("Save Corrections to Disk", type="primary")
    
    if submitted:
        # Update the active story in the session state
        st.session_state.dataset[selected_key]["corrected_body_en"] = corr_en
        st.session_state.dataset[selected_key]["corrected_body_ayo"] = corr_ayo
        st.session_state.dataset[selected_key]["alignment_map"] = alignment_str
        st.session_state.dataset[selected_key]["correction_notes"] = comment_text
        
        # Hydrate disk map
        save_dataset(selected_dataset, st.session_state.dataset)
        st.success("✅ Corrections saved successfully!")

st.markdown("---")
st.header("💾 Export Dataset")
st.markdown("If you are running this app on the web (Streamlit Cloud), your saves are temporary and isolated to the server. Click below to download your updated JSON file, and then send it to the repository owner to merge the updates!")

json_string = json.dumps(st.session_state.dataset, indent=2, ensure_ascii=False)
st.download_button(
    label="Download commented_ayoreo.json",
    data=json_string,
    file_name="commented_ayoreo.json",
    mime="application/json",
    use_container_width=True
)
