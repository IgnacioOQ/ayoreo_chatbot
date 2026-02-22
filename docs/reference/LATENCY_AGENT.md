# Latency Monitoring & Optimization Skill
- status: active
- type: agent_skill
- context_dependencies: {"conventions": "MD_CONVENTIONS.md", "engine": "src/core/engine.py", "server": "src/mcp/server.py", "logger": "src/utils/logger.py", "tools": "src/mcp/tools.py"}
<!-- content -->
This document defines the latency instrumentation in the MCMP Chatbot pipeline, documents known bottlenecks, and provides guidelines for diagnosing and optimizing response times.

---

## 1. Instrumentation Overview
- status: active
<!-- content -->
The pipeline uses a `log_latency` context manager (`src/utils/logger.py`) that wraps each stage with `time.perf_counter()` and logs elapsed milliseconds as `[LATENCY] stage_name: X.Xms`.

### Instrumented Stages

| Stage | File | What It Measures |
|:---|:---|:---|
| `total_generate_response` | `engine.py` | End-to-end time for a single request |
| `load_personality` | `engine.py` | Reading `prompts/personality.md` from disk |
| `build_tools` | `engine.py` | Building tool definitions + description strings |
| `gemini_import` | `engine.py` | Lazy `from google import genai` (first request only) |
| `gemini_client_init` | `engine.py` | `genai.Client()` instantiation |
| `format_history` | `engine.py` | Converting chat history to provider format |
| `gemini_chat_create` | `engine.py` | `client.chats.create()` with config |
| `llm_api_call` | `engine.py` | LLM network call — `chat.send_message()` / API call |
| `llm_api_call_2` | `engine.py` | Second LLM call after tool results (OpenAI only) |
| `tool:{name}` | `server.py` | Individual MCP tool execution (e.g., `tool:get_events`) |

### How to Read the Logs

```bash
grep "\[LATENCY\]" mcmp_chatbot.log
```

Example output for a single Gemini request:
```
[LATENCY] load_personality: 0.7ms
[LATENCY] build_tools: 0.0ms
[LATENCY] gemini_import: 1939.4ms       ← first request only
[LATENCY] gemini_client_init: 208.3ms
[LATENCY] format_history: 0.0ms
[LATENCY] gemini_chat_create: 0.3ms
[LATENCY] llm_api_call: 2706.7ms
[LATENCY] total_generate_response: 4856.7ms
```

### The `log_latency` Context Manager

Defined in `src/utils/logger.py`:
```python
@contextmanager
def log_latency(stage: str):
    start = time.perf_counter()
    yield
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(f"[LATENCY] {stage}: {elapsed_ms:.1f}ms")
```

Use `time.perf_counter()` (not `time.time()`) for monotonic, high-resolution timing unaffected by system clock adjustments.

---

## 2. Pipeline Anatomy
- status: active
<!-- content -->
A single request flows through these stages in order:

```
User Query (app.py)
  |
  v
generate_response() [total_generate_response]
  |
  +-- load_personality()        [load_personality]     ~1ms      (file I/O)
  +-- build tool definitions    [build_tools]          ~0ms      (in-memory)
  +-- import google.genai       [gemini_import]        ~1900ms   (first request only!)
  +-- create API client         [gemini_client_init]   ~200ms    (per request)
  +-- format chat history       [format_history]       ~0ms      (in-memory)
  +-- create chat session       [gemini_chat_create]   ~0ms      (in-memory)
  +-- LLM API call              [llm_api_call]         ~2-3s     (network + inference)
  |     |
  |     +-- (Gemini auto-function-calling may trigger tool calls internally)
  |     +-- (OpenAI: explicit tool loop below)
  |
  +-- Tool execution            [tool:{name}]          ~5-100ms  (file I/O)
  +-- LLM API call #2           [llm_api_call_2]       ~0.5-1.5s (network, OpenAI only)
```

### Provider Differences

| Provider | Tool Calling Model | Instrumentation Notes |
|:---|:---|:---|
| **Gemini** | `automatic_function_calling` (up to 5 round-trips) | `llm_api_call` includes tool execution time since Gemini handles it internally. `tool:{name}` still logs individually. |
| **OpenAI** | Explicit two-call loop | `llm_api_call` = first call, `tool:{name}` = each tool, `llm_api_call_2` = second call with results. |
| **Anthropic** | No tool calling implemented yet | Only `llm_api_call` is logged. |

---

## 3. Measured Baseline (2026-02-14)
- status: active
- last_checked: 2026-02-14
<!-- content -->
Measured with `gemini-2.0-flash`, no chat history, single query ("What is the next upcoming talk?"):

| Stage | Time | % of Total | Notes |
|:---|---:|---:|:---|
| `gemini_import` | 1939ms | 39.9% | First request only (Python import of `google.genai`) |
| `llm_api_call` | 2707ms | 55.7% | Network + LLM inference + auto tool calls |
| `gemini_client_init` | 208ms | 4.3% | Creates `genai.Client()` per request |
| `load_personality` | 0.7ms | <0.1% | Reads `personality.md` from disk |
| `build_tools` | 0.0ms | <0.1% | In-memory tool definition building |
| `format_history` | 0.0ms | <0.1% | No history on first message |
| `gemini_chat_create` | 0.3ms | <0.1% | In-memory chat session creation |
| **total_generate_response** | **4857ms** | **100%** | |

> [!IMPORTANT]
> On subsequent requests within the same process, `gemini_import` drops to ~0ms (Python caches imports). This means steady-state latency is ~3000ms, dominated by `llm_api_call`.

> [!NOTE]
> Gemini's `automatic_function_calling` executes tools internally. The `tool:{name}` entries from `server.py` will appear in the log, but their time is included within `llm_api_call`.

---

## 4. Known Bottlenecks
- status: active
<!-- content -->

### A. LLM API Latency (2000-3000ms per call)

The dominant cost. Typically 55-70% of total request time on steady-state requests.

**Factors:**
- Model size (`gemini-2.0-flash` vs `gemini-2.0-flash-lite`)
- Prompt length (system instruction + chat history + tool descriptions)
- Number of tool round-trips (Gemini auto-calling can trigger up to 5)

**Diagnosis:** Compare `llm_api_call` across requests. If it grows with conversation length, chat history size is the likely cause.

### B. Tool File I/O (5-115ms per tool call)

Every MCP tool call loads its JSON file from disk via `load_data()`:

| Tool | File | Size | Typical Latency |
|:---|:---|:---|:---|
| `get_events` | `raw_events.json` | ~150 KB | 50-115ms |
| `search_people` | `people.json` | ~230 KB | 25-65ms |
| `search_research` | `research.json` | ~12 KB | 5-20ms |
| `search_news` | `news.json` | ~18 KB | 5-20ms |
| `search_graph` | `mcmp_graph.md` | ~11 KB | 12-30ms |

> [!NOTE]
> `search_graph` is especially costly because it instantiates a new `GraphUtils()` on every call, re-loading and re-parsing the graph file each time.

### C. Personality Loading (2-5ms per request)

`load_personality()` reads `prompts/personality.md` from disk on every request. The file is static and rarely changes.

### D. Gemini SDK Import (~1900ms, first request only)

The lazy `from google import genai` inside `generate_response()` takes ~2 seconds on the first call. Python caches the import for subsequent calls, so this only affects cold-start latency.

### E. Gemini Client Init (~200ms per request)

`genai.Client(api_key=...)` is created on every request. This involves internal SDK setup.

### F. Logging Overhead

Each `log_info()` call writes synchronously to both `mcmp_chatbot.log` (file) and stdout. Multiple log calls per request add up to ~20-60ms.

---

## 5. Optimization Playbook
- status: active
<!-- content -->
Ranked by impact (highest first). These are documented strategies for when latency becomes a problem.

### Priority 1: Reduce LLM Round-Trips

- **Symptom:** `llm_api_call` > 3000ms, or `total_generate_response` > 5000ms with Gemini auto-calling.
- **Action:** Reduce `maximum_remote_calls` from 5 to 2-3, or switch to explicit tool calling.
- **Trade-off:** Fewer tool calls may reduce answer quality for complex queries.

### Priority 2: Cache Data Files in Memory

- **Symptom:** `tool:get_events` or `tool:search_people` consistently > 50ms.
- **Action:** Add `@functools.lru_cache` to `load_data()` in `src/mcp/tools.py`, or use a singleton `DataManager` that loads files once at startup.
- **Trade-off:** Stale data until process restart or explicit cache invalidation.

### Priority 3: Cache GraphUtils Instance

- **Symptom:** `tool:search_graph` > 15ms.
- **Action:** Reuse the `GraphUtils` instance from `ChatEngine.graph_utils` instead of creating a new one per `search_graph()` call.
- **Implementation:** Pass the shared instance to the tool, or use a module-level singleton.

### Priority 4: Cache Personality

- **Symptom:** `load_personality` > 3ms consistently.
- **Action:** Read personality once at `ChatEngine.__init__` and store as `self.personality`.
- **Trade-off:** Requires restart to pick up personality changes.

### Priority 5: Move Gemini Import to Module Level

- **Symptom:** `gemini_import` ~1900ms on first request.
- **Action:** Move `from google import genai` and `from google.genai import types` to the top of `engine.py` (guarded with a try/except for environments without the SDK).
- **Trade-off:** Slower module import time, but eliminates first-request penalty.

### Priority 6: Cache Gemini Client

- **Symptom:** `gemini_client_init` ~200ms on every request.
- **Action:** Create `genai.Client()` once in `ChatEngine.__init__` and store as `self.gemini_client`.
- **Trade-off:** Client may need recreation if API key changes (unlikely in production).

### Priority 7: Limit Chat History Length

- **Symptom:** `llm_api_call` grows linearly with conversation length.
- **Action:** Cap `chat_history` to the last N messages (e.g., 10-20) before passing to the LLM.
- **Trade-off:** Very long conversations may lose early context.

---

## 6. Adding New Instrumentation
- status: active
<!-- content -->
When adding new pipeline stages or optimizing existing ones:

1. **Import** `log_latency` from `src/utils/logger.py`.
2. **Wrap** the code block with `with log_latency("descriptive_name"):`.
3. **Naming convention:** Use lowercase with underscores for stages (`llm_api_call`), and `tool:{name}` prefix for MCP tools.
4. **Keep it lightweight:** The context manager adds ~1 microsecond overhead. Do not nest excessively.

```python
from src.utils.logger import log_latency

with log_latency("my_new_stage"):
    result = expensive_operation()
```

---

## 7. Verification
- status: active
<!-- content -->
- [x] `log_latency` context manager implemented in `src/utils/logger.py`
- [x] `generate_response` instrumented with 8 stages in `src/core/engine.py`
- [x] `call_tool` instrumented per-tool in `src/mcp/server.py`
- [x] All latency entries use `[LATENCY]` prefix for easy grep filtering
- [x] No new dependencies (uses stdlib `time` and `contextlib`)
- [x] Baseline measured: ~4.9s total (first request), ~3s steady-state (2026-02-14)

---

## 8. Optimization Record
- status: active
<!-- content -->

### Optimization 1: Initialization & Caching (2026-02-14)
**Problem:**
- `gemini_import` took ~2s on first request.
- `gemini_client_init` took ~200ms per request.
- `load_personality` took ~1-3ms per request.
- `tool` loading relied on repeatedly reading JSONs from disk.

**Solution:**
1.  **Moved Imports:** `google.genai` is now imported at module level in `engine.py`.
2.  **Cached Client:** `genai.Client` is instantiated once in `ChatEngine.__init__`.
3.  **Cached Personality:** Loaded once in `__init__`.
4.  **Cached Data:** Added `@lru_cache` to `load_data` in `src/mcp/tools.py`.

**Results:**
- `total_generate_response`: Reduced from **~4.9s** to **~2.6s** (First Request).
- `gemini_import` / `client_init` overhead removed from response path.
- `llm_api_call` remains the dominant factor (~2.6s).
