import json
import re
from pathlib import Path

def extract_sections(text: str) -> list[dict]:
    """
    Parses a string of text into a list of dictionaries with 'header' and 'text'.
    Each \n\n-separated paragraph becomes its own chunk (one semantic unit / versicle).
    Headers (paragraphs starting with **...**) attach to the next content paragraph.
    """
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    sections = []
    pending_header = None

    for p in paragraphs:
        # Check if the paragraph starts with bold (**...) or bold-italic (***...) text.
        m = re.match(r'^(\*{2,3})([^\*]+)\1[\s:]*(?:\*\*[:\s]*\*\*[\s:]*)?(.*)', p, flags=re.DOTALL)

        if m:
            header = m.group(2).strip()
            rest = m.group(3).strip()
            if rest:
                # Header with inline content: emit as one chunk immediately
                sections.append({'header': header, 'text': rest})
                pending_header = None
            else:
                # Standalone header line: attach to the next paragraph
                if pending_header is not None:
                    # Consecutive headers: flush the previous one as an empty chunk
                    sections.append({'header': pending_header, 'text': ''})
                pending_header = header
        else:
            # Regular paragraph: one chunk, inheriting any pending header
            sections.append({'header': pending_header, 'text': p})
            pending_header = None

    # Flush any trailing header that had no following paragraph
    if pending_header is not None:
        sections.append({'header': pending_header, 'text': ''})

    return sections

def main():
    root_dir = Path(__file__).resolve().parent.parent
    ayoreo_json_path = root_dir / "data" / "raw" / "ayoreoorg" / "ayoreoorg.json"
    
    if not ayoreo_json_path.exists():
        print(f"File not found: {ayoreo_json_path}")
        return
        
    with open(ayoreo_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    updated_count = 0
    for story_id, item in data.items():
        body_es = item.get("body_es", "")
        body_en = item.get("body_en", "")
        body_ayo = item.get("body_ayo", "")
        
        # Parse each body independently
        item["body_decomposition"] = {
            "es": extract_sections(body_es),
            "en": extract_sections(body_en),
            "ayo": extract_sections(body_ayo)
        }
        updated_count += 1
        
    # Write the modified data back to the file
    with open(ayoreo_json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully added 'body_decomposition' to {updated_count} entries in ayoreoorg.json.")

if __name__ == "__main__":
    main()
