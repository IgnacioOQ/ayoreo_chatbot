# Token Optimization Skill
- id: tokenopt_skill
- status: active
- type: agent_skill
- last_checked: 2026-03-02
- label: [agent, guide, core]
<!-- content -->
This document outlines critical guardrails and techniques that all AI Agents operating on this repository must enforce when designing prompts, building API payloads, or writing automation scripts. Due to the high volume of text data processed in this project (e.g., hundreds of parsed semantic chapters), inefficient token usage can result in catastrophic API cost overruns.

## Core Optimization Principles
- id: tokenopt_skill.core_optimization_principles
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
When writing Python scripts that invoke `google.genai` or when formulating prompts, agents must adhere to the following rules:

### 1. Payload Minification (JSON Serialization)
- id: tokenopt_skill.core_optimization_principles.payload_minification
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: Never inject "pretty-printed" JSON or heavily formatted dictionaries into an LLM prompt.
**Why**: Formatting parameters like `indent=2` or `indent=4` inject thousands of meaningless space characters, tabs, and newlines into the prompt. LLMs tokenize these whitespace characters, artificially inflating the context window and the resulting cost by 20% to 30%.
**Implementation**: Always serialize datasets using `separators=(',', ':')` before injection.

*Bad Example (High Token Cost):*
```python
prompt = f"Align this data:\n{json.dumps(data, indent=2)}"
```

*Good Example (Token Optimized):*
```python
prompt = f"Align this data:\n{json.dumps(data, separators=(',', ':'))}"
```

### 2. Model Selection (Cost-to-Reasoning Ratio)
- id: tokenopt_skill.core_optimization_principles.model_selection
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: Default to lightweight, fast models (e.g., `gemini-2.5-flash`) for structural parsing, metadata extraction, semantic mapping, and data formatting.
**Why**: Reasoning models like `gemini-2.5-pro` cost significantly more (often 10x to 15x higher per million tokens). Structural alignment tasks (like zipping arrays or mapping known entities) do not require deep logical reasoning or world knowledge.
**Implementation**: Reserve `pro` models *only* for deep creative tasks, complex philosophical translation inference, or abstract architectural planning. For batch processing over the `bible.json` or `ayoreoorg.json` datasets, `flash` is mandatory.

### 3. Prompt Verbosity
- id: tokenopt_skill.core_optimization_principles.prompt_verbosity
- status: active
- type: guideline
- last_checked: 2026-03-02
<!-- content -->
**Rule**: Eliminate conversational filler from `SYSTEM_PROMPT` strings inside scripts.
**Why**: Instructing the model with "Please take a look at the following data and tell me what you think..." adds redundant tokens. 
**Implementation**: Be highly directive. Use protocols (e.g., "Extract X. Output Y.").

## Known Incidents
- id: tokenopt_skill.known_incidents
- status: active
- type: log
- last_checked: 2026-03-02
<!-- content -->
- **March 2026 Semantic Alignment Bloat**: The initial semantic matching scripts processed 530 biblical chapters using `json.dumps(..., indent=2)` and `gemini-2.5-pro`. This consumed 3.69 million tokens at a cost of ~$26. Swapping to `gemini-2.5-flash` and stripping JSON whitespace reduced the footprint to a few cents per run.
