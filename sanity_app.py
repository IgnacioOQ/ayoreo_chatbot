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
JSON_PATH = PROJECT_ROOT / "data" / "raw" / "ayoreoorg.json"

# --- 1. State Management & Loading ---
@st.cache_data
def load_dataset() -> dict:
    if not JSON_PATH.exists():
        st.error(f"Dataset not found at {JSON_PATH}")
        return {}
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_dataset(data: dict):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    # Clear cache so next potential reload pulls the updated file natively
    load_dataset.clear()

if "dataset" not in st.session_state:
    st.session_state.dataset = load_dataset()

dataset = st.session_state.dataset

if not dataset:
    st.stop()

# Build filtering tuples dynamically
unique_types = sorted(list(set(v.get("type", "unknown") for v in dataset.values())))
unique_sections = sorted(list(set(v.get("section", "unknown") for v in dataset.values())))

# --- 2. Sidebar Navigation ---
with st.sidebar:
    st.title("🔎 Dataset Explorer")
    st.markdown("Filter and select stories from the scraped `ayoreoorg.json` dataset to sanity-check their contents and submit structural corrections.")
    
    st.markdown("---")
    st.header("Filters")
    
    selected_type = st.selectbox("Type", ["All"] + unique_types)
    selected_section = st.selectbox("Section", ["All"] + unique_sections)
    
    # Filter dataset
    filtered_keys = []
    for k, v in dataset.items():
        match_type = (selected_type == "All" or v.get("type") == selected_type)
        match_sec = (selected_section == "All" or v.get("section") == selected_section)
        if match_type and match_sec:
            filtered_keys.append(k)
            
    st.markdown("---")
    st.header(f"Stories ({len(filtered_keys)})")
    
    if not filtered_keys:
        st.warning("No stories match the current filters.")
        st.stop()
        
    selected_key = st.selectbox("Select a Story to View", filtered_keys)

# --- 3. Main Data Visualization Area ---
story = dataset[selected_key]

st.title(story.get("title_es", "Untitled Story"))

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
tcol1, tcol2, tcol3 = st.columns(3)
with tcol1:
    st.subheader("🇪🇸 Español")
    st.markdown(f"**URL:** [link]({story.get('url_es', '')})")
    st.text_area("Body", story.get("body_es", ""), height=300, disabled=True, key="raw_body_es")
with tcol2:
    st.subheader("🇬🇧 English")
    st.markdown(f"**URL:** [link]({story.get('url_en', '')})")
    st.text_area("Body", story.get("body_en", ""), height=300, disabled=True, key="raw_body_en")
with tcol3:
    st.subheader("🏹 Ayoré")
    st.markdown(f"**URL:** [link]({story.get('url_ayo', '')})")
    st.text_area("Body", story.get("body_ayo", ""), height=300, disabled=True, key="raw_body_ayo")

# Visualizing Decompositions
st.markdown("### 🧩 Body Decomposition")
decomp = story.get("body_decomposition", {})

tab_es, tab_en, tab_ayo = st.tabs(["Español", "English", "Ayoré"])
with tab_es:
    st.json(decomp.get("es", []))
with tab_en:
    st.json(decomp.get("en", []))
with tab_ayo:
    st.json(decomp.get("ayo", []))

st.markdown("---")

# --- 4. Annotation & Corrections Area ---
st.header("📝 Editor Corrections")
st.markdown("Use this form to add notes or correct the raw scraped bodies. Your inputs will be saved into the JSON under new `correction` keys so the raw text is never lost.")

with st.form("correction_form"):
    ccol1, ccol2, ccol3 = st.columns(3)
    
    # Pre-fill with existing corrections if they exist, otherwise default to the current raw body
    with ccol1:
        corr_es = st.text_area(
            "Corrected Español", 
            value=story.get("corrected_body_es", story.get("body_es", "")), 
            height=250
        )
    with ccol2:
        corr_en = st.text_area(
            "Corrected English", 
            value=story.get("corrected_body_en", story.get("body_en", "")), 
            height=250
        )
    with ccol3:
        corr_ayo = st.text_area(
            "Corrected Ayoré", 
            value=story.get("corrected_body_ayo", story.get("body_ayo", "")), 
            height=250
        )
        
    comment_text = st.text_area("Editor Comments / Notes", value=story.get("correction_notes", ""), height=100)
    
    submitted = st.form_submit_button("Save Corrections to Disk", type="primary")
    
    if submitted:
        # Update the active story in the session state
        st.session_state.dataset[selected_key]["corrected_body_es"] = corr_es
        st.session_state.dataset[selected_key]["corrected_body_en"] = corr_en
        st.session_state.dataset[selected_key]["corrected_body_ayo"] = corr_ayo
        st.session_state.dataset[selected_key]["correction_notes"] = comment_text
        
        # Hydrate disk map
        save_dataset(st.session_state.dataset)
        st.success("✅ Corrections saved successfully!")

st.markdown("---")
st.header("💾 Export Dataset")
st.markdown("If you are running this app on the web (Streamlit Cloud), your saves are temporary and isolated to the server. Click below to download your updated JSON file, and then send it to the repository owner to merge the updates!")

json_string = json.dumps(st.session_state.dataset, indent=2, ensure_ascii=False)
st.download_button(
    label="Download Updated ayoreoorg.json",
    data=json_string,
    file_name="ayoreoorg.json",
    mime="application/json",
    use_container_width=True
)
