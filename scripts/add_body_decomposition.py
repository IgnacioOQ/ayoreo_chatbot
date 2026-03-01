import json
import re
from pathlib import Path

def extract_sections(text: str) -> list[dict]:
    """
    Parses a string of text into a list of dictionaries with 'header' and 'text'.
    Headers are recognized if a paragraph starts with **...**.
    """
    if not text:
        return []
    
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    sections = []
    current_header = None
    current_text = []
    
    for p in paragraphs:
        # Check if the paragraph starts with bold (**...) or bold-italic (***...) text.
        # We also consume trailing asterisks, spaces, or colons after the closing tag without eating subsequent text logic.
        m = re.match(r'^(\*{2,3})([^\*]+)\1[\s:]*(?:\*\*[:\s]*\*\*[\s:]*)?(.*)', p, flags=re.DOTALL)
        
        if m:
            header = m.group(2).strip()
            rest = m.group(3).strip()
            
            # If we already have accumulated text (or a header with text), flush it
            if current_header is not None or current_text:
                sections.append({
                    'header': current_header,
                    'text': '\n\n'.join(current_text).strip() if current_text else ""
                })
            
            # Start a new section
            current_header = header
            current_text = [rest] if rest else []
        else:
            # Continue accumulating text for the current section
            current_text.append(p)
            
    # Flush whatever remains at the end
    if current_header is not None or current_text:
        sections.append({
            'header': current_header,
            'text': '\n\n'.join(current_text).strip() if current_text else ""
        })
        
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
