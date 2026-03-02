# AI Agent Logs
- id: ai_agent_logs
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
This file tracks major actions, architectural changes, and features implemented by AI agents functioning on this codebase.

## [2026-03-02] Semantic Alignment Protocol & Token Optimization
- id: ai_agent_logs.2026_03_02_semantic_alignment_token_optimization
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
**Agent**: Antigravity
**Task**: Design a heuristic alignment protocol for low-resource translation datasets and optimize its API cost payload.

### Summary
- id: ai_agent_logs.2026_03_02_semantic_alignment_token_optimization.summary
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
Implemented a two-part semantic matching protocol using Gemini to map opaque Ayoreo text against high-resource English/Spanish anchors. Addressed high API token consumption during early runs by introducing payload minification and swapping the model from `gemini-2.5-pro` to `gemini-2.5-flash`, resulting in a ~95% cost reduction.

### Changes
- id: ai_agent_logs.2026_03_02_semantic_alignment_token_optimization.changes
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
-   **Semantic Alignment Tooling**: Created `scripts/align_mismatches_llm.py` and `scripts/align_bible_llm.py` to enforce structured JSON output grouping mapped sentence chunks.
-   **Heuristic Fallbacks**: Added size-matching and prefix-omission heuristics to the agent prompt to prevent LLMs from inaccurately mapping massive paragraphs to single-sentence meta-comments.
-   **Cost Optimization**: Edited generation scripts to use `json.dumps(..., separators=(',', ':'))` rather than `indent=2`, saving thousands of whitespace tokens per API call. Swapped to `gemini-2.5-flash` for structural reasoning.
-   **UI Integration**: Completely rewrote the "Parallel (Aligned)" tab in `sanity_app.py` to parse the dynamic alignment maps instead of relying on a naive max-length zip algorithm.

### Verification
- id: ai_agent_logs.2026_03_02_semantic_alignment_token_optimization.verification
- status: active
- type: context
- last_checked: 2026-03-02
<!-- content -->
-   Verified `sanity_app.py` correctly renders parsed map dictionaries for "Al pie del Totem" story without crashing.
-   Verified execution logs showing cost drops to ~$0.27 per 3.69M tokens.
