# Semantic Matching Protocol for Low-Resource Languages
- status: active
- type: agent_skill
- label: [agent, core]
- last_checked: 2026-03-02
- id: semantic_matching_protocol
<!-- content -->

When aligning paragraph chunks across highly resourced languages (e.g., Spanish, English) and structurally opaque, low-resource languages (e.g., Ayoreo) without a bilingual dictionary, the LLM must rely on structural heuristics rather than direct translation understanding.

This document defines the strict, iterative protocol that any agent or alignment script must follow to assemble an `alignment_map`.

## Core Challenge
- status: active
- type: context
<!-- content -->
Because Ayoreo text parsing often yields a different number of paragraphs/chunks compared to its Spanish/English counterparts, we must map them.

An `alignment_map` shows which indices in each language correspond to the exact same semantic chunk. For example:
```json
{
  "es": [0, 1],
  "en": [0],
  "ayo": [0]
}
```
This means Spanish chunks `0` and `1` together contain the same information as English chunk `0` and Ayoreo chunk `0`.

## Anchor Heuristic Protocol
- status: active
- type: protocol
<!-- content -->
Agents MUST follow these exact steps when attempting alignment:

1. **Step 1: High-Resource Anchor Alignment (ES ↔ EN)**
   - Start by aligning the Spanish and English chunks. Since the LLM fluently understands both, it has near-perfect accuracy in matching the semantic narrative between them.
   - Example observation: *"ES chunk [0] and [1] correspond to EN chunk [0]. ES chunk [2] corresponds to EN chunk [1]."*

2. **Step 2: Narrative Sequencing**
   - Summarize the narrative progression established in Step 1.
   - Example observation: *"The sequence is: (A) Introduction of narrator Cotade. (B) Journey to the forest. (C) Encounter with the jaguar."*

3. **Step 3: Low-Resource Anchoring (Named Entities & Structural Markers)**
   - Scan the opaque Ayoreo chunks for shared entities that transcend translation.
   - Look for:
     - **Proper Nouns / Names:** *Cotade*, *Dupade*, *Campo Loro*.
     - **Numbers / Dates:** *1985*, *10*.
     - **Punctuation Patterns:** Quotation marks (`"..."`) usually map to dialogue in the exact same sequence in the other languages.
     - **Formatting:** Paragraph length relative to the overall text.

4. **Step 4: Monotonic Structural Constraints**
   - The chunks ALWAYS appear chronologically.
   - If Ayoreo chunk `[1]` contains the name "Dupade" corresponding to Narrative Event B, then Ayoreo chunk `[0]` MUST correspond to Narrative Event A.
   - The LLM must not map AYO chunk `[2]` to ES chunk `[0]` if AYO chunk `[1]` maps to ES chunk `[1]`. Sequences cannot invert.

5. **Step 5: Emit the Map**
   - Build a flat JSON array of mapped groupings. Each grouping represents a single logical narrative unit.
   - *Requirement:* Every valid index from the original decomposition arrays must appear exactly once across the final groupings.

## LLM Prompts
- status: active
- type: context
<!-- content -->
When invoking an LLM via API (e.g., Gemini Standard/Pro) to perform this matching, the System Instruction MUST include the rules described above in the **Anchor Heuristic Protocol**, accompanied by an explicit Structured Output schema.
