# MCMP Chatbot

- status: active
- context_dependencies: {"agents": "AGENTS.md", "conventions": "docs/MD_CONVENTIONS.md"}

<!-- content -->

A chatbot for the **Munich Center for Mathematical Philosophy (MCMP)**. This application scrapes the MCMP website for the latest events, people, and research, and uses an LLM (Google Gemini, OpenAI, or Anthropic) with structured data tools (MCP) to answer user queries about the center's activities.

The application is built with **Streamlit** for the frontend, uses **MCP tools** over JSON databases for data access, and integrates with **Google Sheets** for cloud-based feedback collection.

## Features

- **Activity QA**: Ask about upcoming talks, reading groups, and events.
- **Automated Scraping**: Keeps data fresh by scraping the MCMP website.
- **Incremental Scraping**: Preserves historical data (e.g., past events) by merging new scrapes with existing records logic, ensuring a growing knowledge base.
- **Rich Metadata Extraction**: Automatically extracts detailed profile information including emails, office locations, hierarchical roles, and publication lists.
- **MCP Architecture**: Uses structured data tools (Model Context Protocol) over JSON databases for precise, low-latency data access — no embedding pipeline needed.
- **Institutional Graph**: Uses a graph-based layer (`data/graph`) to understand organizational structure (Chairs, Leadership) while linking people to hierarchical **Research Topics**.
- **Cloud Database (Feedback)**: User feedback is automatically saved to a Google Sheet for persistent, cloud-based storage (with a local JSON fallback).
- **Multi-LLM Support**: Configured to work seamlessly with **Google Gemini**, but also supports OpenAI and Anthropic.
- **Structured Data Tools (MCP)**: Implements an in-process Model Context Protocol (MCP) server that exposes `people.json`, `research.json`, `raw_events.json`, and the institutional graph as structured tools. This allows the LLM to perform precise queries (e.g., "List all events next week", "Who researches Logic?", "Who leads the Chair of Logic?").
- **Configurable Personality (Leopold)**: The chatbot's personality is defined in `prompts/personality.md`, separating tone and identity from code. Edit the file to adjust behavior without touching the engine.
- **Agentic Workflow**: Follows the `AGENTS.md` and `docs/MD_CONVENTIONS.md` protocols for AI-assisted development.



## Architecture

The system uses an **MCP-only architecture**: the LLM has direct access to structured data tools that query the JSON databases. No embedding pipeline or vector database is needed.

1.  **Data Collection**: The system uses `src/scrapers` to fetch data from the MCMP website and stores it as JSON files.
2.  **Tool-Augmented Generation**: When a user asks a question, the LLM receives the query along with available MCP tools. It decides which tools to call to fetch relevant data.
3.  **Response**: The LLM generates a response grounded in the tool results.



## Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd mcmp_chatbot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Secrets**:
   Create a `.streamlit/secrets.toml` file with your API keys.

   **For Google Gemini (Recommended):**
   - Get your API key from [Google AI Studio](https://aistudio.google.com/).
   ```toml
   GEMINI_API_KEY = "your-google-gemini-key"
   ```
   > [!NOTE]
   > The `GEMINI_API_KEY` determines where the LLM usage is billed. This is often a different Google Cloud project (e.g., `gen-lang-client...`) than the Service Account used for Sheets. To consolidate billing, link your API key to the `mcmp-chatbot` project in Google AI Studio.

   **For Cloud Feedback (Google Sheets):**
   - Create a project in [Google Cloud Console](https://console.cloud.google.com/).
   - Enable the [Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com) and [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com).
   - Create a Service Account and download the JSON key.
   ```toml
   [gcp_service_account]
   type = "service_account"
   project_id = "..."
   private_key = "..."
   client_email = "..."
   # ... (other standard GCP credentials)
   sheet_name = "MCMP Feedback"
   ```

4. **Run the Application**:
   ```bash
   streamlit run app.py
   ```

## Data Maintenance
To keep the chatbot up to date with the latest MCMP events and personnel, run the update protocol:

```bash
python scripts/update_dataset.py
```
This script will:
1.  Scrape the MCMP website (Events, People, Research).
2.  Update JSON datasets (`data/*.json`).
3.  **Enrich Metadata**: Run internal utilities to extract structured metadata (dates, roles) from text descriptions.
4.  Rebuild the Institutional Graph (`data/graph/mcmp_graph.md` and `mcmp_jgraph.json`).

## Technical Architecture

### 1. Frontend: Streamlit
The user interface is built entirely in **Streamlit**, providing a clean, responsive chat interface. It handles user sessions, admin access (password protected), and feedback forms directly in the browser.

### 2. AI Engine: Google Gemini
The core logic (`src/core/engine.py`) connects to the **Gemini API** (or others) to generate responses. It prompts the model with retrieved context from the vector store to ensure accuracy and minimize hallucinations.

### 3. Data Storage
- **Vector Database**: Scraped content is chunked and embedded into a local **ChromaDB** instance (`data/vectordb`) for fast semantic retrieval.
- **Markdown Graph**: Institutional relationships are stored in `data/graph/mcmp_graph.md` and parsed by `src/core/graph_utils.py` for context injection.
- **Cloud Feedback**: User feedback is pushed to **Google Sheets** via the Google Drive API, acting as a cloud database for ongoing user data collection.

### 5. MCP Integration (Structured Data)
To handle specific queries that require structured data access (e.g., "Which events are happening between date X and Y?"), the system implements a lightweight **MCP Server** (`src/mcp/`).
- **Tools**: Exposes Python functions (`search_people`, `search_research`, `get_events`) as tools to the LLM.
- **Hybrid Execution**: The RAG engine first retrieves semantic context, then offers these tools to the LLM. If the LLM determines it needs precise data, it calls the tool, and the result is fed back for the final answer.
- **Toggle**: This feature is optional and can be enabled/disabled via the Streamlit sidebar to manage latency and costs.

### 6. Advanced Logic (Prompt Engineering)
To ensure reliable tool usage, the system implements:
- **Dynamic Injection**: Tools are explicitly listed in the system prompt.
- **Force Usage**: Imperative commands ("Just check") prevent the LLM from asking for permission.
- **Data Enrichment**: If RAG context is partial (e.g., missing abstracts), the LLM is mandated to use tools to fetch full details.
*(See `docs/MCP_AGENT.md` for full implementation details)*

### 4. Data Model & Relationships
The system connects four key data types to answer complex questions:
1.  **People** (`data/people.json`): Comprehensive profiles including bios, contact details (email, phone, office), organizational roles, and selected publications.
2.  **Research** (`data/research.json`): Hierarchical structure of research areas (e.g., Logic, Philosophy of Science) and their subtopics, with automated linking to people.
3.  **Events** (`data/raw_events.json`): Upcoming talks and workshops.
4.  **Institutional Graph** (`data/graph/mcmp_graph.md`): A knowledge graph that links **People** to **Organizational Units** (Chairs) and defines hierarchy (e.g., who leads a chair, who supervises whom). 


**How they interact:**
- When a user asks "Who works at the Chair of Philosophy of Science?", the **Graph** identifies the Chair entity and its `affiliated_with` edges.
- The system then retrieves detailed profiles from **People** data.
- If the user asks "What does Ignacio Ojea research?", the system checks his **People** profile, which is now automatically linked to relevant **Research Topics** (e.g., "Philosophy of Science") and specific projects.

## Query Processing Pipeline

This diagram illustrates how the system uses **MCP (Structured Data)** tools and the **Graph (Relationships)** to answer a user query.

```mermaid
graph TD
    UserQuery[User Query] --> LLM[LLM with MCP Tools]
    
    subgraph "MCP Tools"
        LLM -->|"search_people(query)"| PeopleDB[(people.json)]
        LLM -->|"get_events(query)"| EventsDB[(raw_events.json)]
        LLM -->|"search_research(topic)"| ResearchDB[(research.json)]
        LLM -->|"search_graph(query)"| GraphDB[(Institutional Graph)]
    end
    
    PeopleDB --> |Results| LLM
    EventsDB --> |Results| LLM
    ResearchDB --> |Results| LLM
    GraphDB --> |Results| LLM
    
    LLM --> FinalResponse[Final Response]

    style PeopleDB fill:#e8f5e9,stroke:#1b5e20
    style EventsDB fill:#e8f5e9,stroke:#1b5e20
    style ResearchDB fill:#e8f5e9,stroke:#1b5e20
    style GraphDB fill:#f3e5f5,stroke:#4a148c
    style LLM fill:#fff3e0,stroke:#e65100
```

### How It Works
1.  **User Query**: The user asks a question (e.g., *"What is Hannes Leitgeb working on?"*).
2.  **LLM with Tools**: The LLM receives the query along with personality instructions and available MCP tools.
3.  **Tool Calls**: The LLM decides which tools to call based on the question:
    - `search_people` for profile information
    - `get_events` for upcoming talks and workshops
    - `search_research` for research topics and areas
    - `search_graph` for institutional relationships (who leads which chair, etc.)
4.  **Final Response**: The LLM synthesizes all tool results into a coherent answer.

### Example Walkthrough

**Query:** *"What is Hannes Leitgeb working on and what are his upcoming events?"*

1.  **Tool Calls**:
    - `search_people("Hannes Leitgeb")` → Returns profile, research interests
    - `search_graph("Hannes Leitgeb")` → Returns: "Hannes Leitgeb LEADS Chair of Logic..."
    - `get_events(query="Hannes Leitgeb")` → Returns: `[{"title": "Talk at LMU", "date": "2024-10-15", ...}]`

2.  **Final Synthesis**:
    > "Hannes Leitgeb is currently working on Logic and Probability... He leads the Chair of Logic and Philosophy of Language. Regarding his schedule, he has an upcoming talk at LMU on October 15th."

## Project Structure

```
mcmp_chatbot/
├── app.py                # Main Streamlit application entry point
├── src/
│   ├── core/             # Chat engine (Gemini), Graph Utils, Personality loader
│   ├── mcp/              # MCP Tools and Server implementation
│   ├── scrapers/         # Scrapers for MCMP website
│   ├── ui/               # Streamlit UI components
│   └── utils/            # Helper functions (logging, etc.)
├── prompts/              # Chatbot personality configuration
│   └── personality.md    # Leopold's identity, tone, and guidelines
├── data/                 # Local data storage (JSONs)
├── docs/                 # Project documentation and proposals
│   ├── rag_improvements.md
│   ├── HOUSEKEEPING.md   # Maintenance protocols
│   ├── PERSONALITY_AGENT.md # Agent skill for personality design
│   └── MD_CONVENTIONS.md # Markdown conventions
├── scripts/              # Maintenance and update scripts
│   └── update_dataset.py # Main data update script
├── tests/                # Unit and integration tests
├── AGENTS.md             # Guidelines for AI Agents
└── requirements.txt      # Python dependencies
```

## Agentic Workflow

This project uses a structured workflow for AI agents.
- **AGENTS.md**: Read this first if you are an AI assistant.
- **docs/MD_CONVENTIONS.md**: Defines the schema for Markdown files and task management.
