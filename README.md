# AI Operations Assistant

An internal-operations AI agent that answers company-knowledge questions grounded
in a real handbook (RAG), looks up an internal ticket database, summarizes text,
and drafts emails / calendar events — all through a single LangGraph reasoning
loop with full step-by-step logging. Built entirely on free-tier services.

## Architecture

```
                         USER
                          |
                          v
                 Streamlit Chat UI
                          |
                          v
              FastAPI /chat endpoint
                          |
                          v
         +--------------------------------+
         |      LangGraph Orchestrator      |
         |   intent -> reason -> tool ->    |
         |   observe -> (loop) -> final     |
         +--------------------------------+
                          |
     +-----------+--------+---------+-----------+
     v           v        v         v           v
 System       Memory   Planner   Tool        Observer
 Prompt       (SQLite) (LLM      Registry    (feeds tool
 (retrieval-           decides   dispatch    output back
  first, no            next                 into reasoning)
  hallucination)       step)
                          |
                 +--------+--------+
                 v                 v
           ChromaDB           Tool Registry
       (handbook chunks,       search_documents, search_database,
        local embeddings)      create_summary, send_email (dry-run),
                                schedule_meeting (dry-run)
                          |
                          v
              Structured log (SQLite: every
              retrieval, tool call, decision)
```

Reasoning LLM: **Groq** (`openai/gpt-oss-120b`), falls back to **Gemini**
(`gemini-flash-latest`) on error/rate-limit. Embeddings run locally via
`sentence-transformers` — no embedding API calls, no rate limits.

## Setup

### 1. Clone and create a virtual environment

```bash
python -m venv .venv
```

Windows (PowerShell):
```powershell
.\.venv\Scripts\Activate.ps1
```
macOS/Linux:
```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your own keys — never commit `.env`:

```bash
cp .env.example .env
```

- `GROQ_API_KEY` — free at [console.groq.com](https://console.groq.com)
- `GEMINI_API_KEY` — free at [Google AI Studio](https://aistudio.google.com/)
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — only needed for real (non-dry-run)
  Gmail/Calendar sending; see step 5 below. Leave `DRY_RUN=true` to skip this
  entirely for the demo.

### 4. Add the company handbook and ingest it

Place your own `company_handbook.pdf` at `data/documents/company_handbook.pdf`
(a multi-section document — company overview, policies, FAQ, etc. — each under
a clear heading), then run:

```bash
python -m app.rag.ingest
```

This chunks the PDF, embeds it locally, and persists it to `data/chroma/`.

### 5. (Optional) Google OAuth for real email/calendar

Only needed if you want `send_email` / `schedule_meeting` to actually send/create
things instead of dry-run logging. Follow `docs/google_oauth_setup.md`, save the
downloaded file as `credentials.json` in the project root, and set `DRY_RUN=false`.
For the demo below, leave `DRY_RUN=true` — no Google Cloud project needed.

### 6. Initialize the database

```bash
python -c "from app.memory.db import init_db; init_db()"
```

(Also happens automatically on first FastAPI startup.)

## Running the app

Start the backend:
```bash
uvicorn app.main:app --reload
```

In a second terminal, start the frontend:
```bash
streamlit run frontend/streamlit_app.py
```

Open the Streamlit URL it prints (typically `http://localhost:8501`).

## Demo script

Try these in order in the chat UI — each demonstrates a different capability,
and each turn's "Agent trace" expander shows the retrieval/tool-call/reasoning
steps behind the answer:

1. **RAG (grounded in the handbook):**
   `What healthcare solutions does Wadhwani AI provide?`
2. **Internal database tool:**
   `Show me all open IT support tickets`
3. **Summary tool (chained with the database tool):**
   `Look up all the company tickets in the database, then create a summary report of them`
4. **Email tool (dry run):**
   `Email a summary of the healthcare section to test@example.com`
5. **Calendar tool (dry run):**
   `Schedule a 30-min meeting tomorrow at 3pm called Team Sync`

You can inspect the full raw execution log for any session via the sidebar
button, or directly:
```bash
python scripts/view_logs.py <session_id>
```

Or run any query headlessly without the UI:
```bash
python scripts/run_agent.py "your query here"
```

## Running tests

```bash
pytest tests/
```

## Project structure

See `docs/DESIGN_DECISIONS.md` for the reasoning behind the architecture and
tech choices (why LangGraph, why local embeddings, why single-agent, etc).
