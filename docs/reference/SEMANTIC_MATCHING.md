# Semantic Matching Protocol for Low-Resource Languages
- status: active
- type: agent_skill
- label: [agent, core]
- last_checked: 2026-03-21
- id: semantic_matching_protocol
<!-- content -->

When aligning paragraph chunks across a high-resource language (English) and a structurally opaque, low-resource language (Ayoreo) without a bilingual dictionary, the LLM must rely on structural heuristics rather than direct translation understanding.

This document defines the strict, iterative protocol that any agent or alignment script must follow to assemble an `alignment_map`.

> **Note on Spanish (ES):** The pipeline is EN↔AYO by default. Spanish data may be present in the dataset for historical reasons or when re-scraped with `--scrape-es`, but it is **not required**. When ES data is available it can serve as a cross-check for EN anchoring (see Step 1 below), but the protocol is fully functional without it.

## Core Challenge
- status: active
- type: context
<!-- content -->
Because Ayoreo text parsing often yields a different number of paragraphs/chunks compared to its English counterpart, we must map them.

The scraper scripts currently pull from two distinct sources, both producing similar schema problems:
1. `ayore.org` (Relatos, cultural stories) -> `ayoreoorg.json`
2. `bible.com` (YouVersion Bible translation) -> `bible.json`

An `alignment_map` shows which indices in each language correspond to the exact same semantic chunk. For example:
```json
{
  "en": [0],
  "ayo": [0]
}
```
This means English chunk `0` contains the same information as Ayoreo chunk `0`.

When Spanish data is present, it may also appear in the map:
```json
{
  "en": [0],
  "ayo": [0],
  "es": [0, 1]
}
```

## Anchor Heuristic Protocol
- status: active
- type: protocol
<!-- content -->
Agents MUST follow these exact steps when attempting alignment:

1. **Step 1: English Anchor Alignment (EN → AYO)**
   - Use English as the primary anchor. Since the LLM fluently understands English, it has near-perfect accuracy in parsing the semantic narrative.
   - Example observation: *"EN chunk [0] corresponds to AYO chunk [0]. EN chunk [1] corresponds to AYO chunks [1] and [2]."*
   - If Spanish (ES) data is present in the entry, use it as a supplementary cross-check only — verify that the ES reading of a chunk agrees with EN before anchoring to AYO. Do not use ES as the primary driver.

2. **Step 2: Narrative Sequencing**
   - Summarize the narrative progression established in Step 1.
   - Example observation: *"The sequence is: (A) Introduction of narrator Cotade. (B) Journey to the forest. (C) Encounter with the jaguar."*

3. **Step 3: Low-Resource Anchoring (Named Entities & Structural Markers)**
   - Scan the opaque Ayoreo chunks for shared entities and structural traits that transcend translation.
   - Look for:
     - **Proper Nouns / Names:** *Cotade*, *Dupade*, *Campo Loro*.
     - **Numbers / Dates:** *1985*, *10*.
     - **Punctuation Patterns:** Quotation marks (`"..."`) usually map to dialogue in the exact same sequence in the other languages.
     - **Text Length:** Overall length of the text component. Short components typically translate to short components, and long components to long components. Use relative character blocks to establish a baseline.

4. **Step 4: Monotonic Structural Constraints**
   - The chunks ALWAYS appear chronologically.
   - If Ayoreo chunk `[1]` contains the name "Dupade" corresponding to Narrative Event B, then Ayoreo chunk `[0]` MUST correspond to Narrative Event A.
   - The LLM must not map AYO chunk `[2]` to EN chunk `[0]` if AYO chunk `[1]` maps to EN chunk `[1]`. Sequences cannot invert.

5. **Step 5: Emit the Map**
   - Build a flat JSON array of mapped groupings. Each grouping represents a single logical narrative unit.
   - *Requirement 1:* Every valid index from the original EN and AYO decomposition arrays must appear exactly once across the final groupings.
   - *Requirement 2:* If a language translation is entirely missing from the input (e.g., there is no Ayoreo text at all), you still must emit the `"ayo"` key for every grouping, but its value must be an empty array `[]`.
   - *Requirement 3:* The `"es"` key is **optional**. Include it only when Spanish data is present in the input. When included, every ES index must appear exactly once.
   - *Heuristic 1 (Missing Ayoreo Context):* When there is a mismatch where English components outnumber Ayoreo components, the missing pieces are almost always at the **beginning** of the text. This is because raw materials typically include English meta-comments or context framing the text, whereas the Ayoreo translation strictly contains only the narrative body.
   - *Heuristic 2 (Size Matching):* The LLM must not associate components of significantly different physical sizes. If an English component is a single sentence (e.g., a short meta-comment) and the Ayoreo component is an extremely long paragraph, they **DO NOT MATCH**. In this case, the short meta-comment is missing an Ayoreo translation and must be mapped to `[]`.

## Output Format
- status: active
- type: format
<!-- content -->
The semantic matching process must produce an output file that is structurally identical to the source JSON dataset (`ayoreoorg.json` or `bible.json`), but saved as a new file (e.g. `aligned_ayoreoorg.json` or `aligned_bible.json`).

The scripts (`align_mismatches_llm.py` and `align_bible_llm.py`) should serialize the complete dataset, where each original entry is preserved in its entirety, but any entry that underwent alignment now includes the new `"alignment_map"` key.

Example output shape for `aligned_ayoreoorg.json` (EN+AYO only, default):
```json
{
  "first-person-narratives__cotade-i-gave-myself-to-him": {
    "story_id": "first-person-narratives__cotade-i-gave-myself-to-him",
    "url_en": "...",
    "url_ayo": "...",
    "title_en": "...", "title_ayo": "...",
    "body_en": "...", "body_ayo": "...",
    "body_decomposition": {
      "en": [...],
      "ayo": [...]
    },
    "alignment_map": "[{\"en\": [0, 1], \"ayo\": [0]}]",
    "warnings": []
  }
}
```

Example with optional Spanish data present:
```json
{
  "alignment_map": "[{\"en\": [0, 1], \"ayo\": [0], \"es\": [0, 1]}]"
}
```

## LLM Prompts & Optimization
- status: active
- type: context
<!-- content -->
When invoking an LLM via API (e.g., Gemini Standard/Pro) to perform this matching, the System Instruction MUST include the rules described above in the **Anchor Heuristic Protocol**, accompanied by an explicit Structured Output schema.

### Token Efficiency Guardrails
Due to the sheer size of the raw translation text (e.g., 530 chapters of the Bible translate to ~3.69M tokens before output), agents or scripts running this protocol MUST abide by two cost-saving rules:
1. **Model Selection:** Use a lightweight, high-speed model (e.g., `gemini-2.5-flash`). The structural heuristics defined above do not require heavy reasoning models like `pro`, allowing for a ~95% cost reduction.
2. **Payload Minification:** Never send "pretty printed" data. When injecting the `body_decomposition` arrays into the prompt, you must serialize them without whitespaces (e.g. `json.dumps(data, separators=(',', ':'), ensure_ascii=False)`). Whitespace indenting across thousands of lines mathematically inflates token consumption by 20-30%.
3. **Skip absent languages:** Do not include the ES block in the prompt when Spanish data is not present. This avoids wasting tokens on empty arrays and keeps the prompt focused on EN↔AYO.
