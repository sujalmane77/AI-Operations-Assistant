# AI Operations Assistant — Build Plan
### (Spec file for autonomous execution via Claude Code)

---

## HOW TO USE THIS FILE (read this first, every session)

This file is written to be attached directly in the Claude Code extension in VS Code and executed with minimal back-and-forth, to conserve credits. If you are Claude Code reading this:

1. **Determine current state first.** Check the repo against the `## Progress Checklist` below and against what files actually exist on disk. The checklist is the source of truth for what's done — but verify against the actual repo, since the checklist could be stale if a previous session was interrupted mid-phase.
2. **Execute exactly one phase per work session unless told otherwise.** Find the first unchecked phase in the checklist. Read only that phase's section below — you do not need the rest of the file's phase details in context to work on it.
3. **Work autonomously within the phase.** Do not stop to ask for confirmation on implementation details, file layout, or minor decisions — this plan is detailed enough to just build. Only stop and ask the user directly when:
   - a phase's "Requires from user" field lists something only the user can provide (e.g. the company PDF, Google OAuth credentials), and it isn't present yet
   - you hit a genuine ambiguity that would materially change architecture (not style/naming)
4. **Test before marking done.** Every phase has a "Definition of Done" — actually run it (or tell the user the exact command to run it, then wait for their confirmation of the result) before checking it off.
5. **Update the checklist yourself** when a phase's Definition of Done is met — check the box and add a one-line note (e.g. date or commit-ish summary) so future sessions don't redo work.
6. **Be concise in your own output.** Don't re-explain the whole plan back to the user, don't regenerate files that didn't need to change, don't produce long prose summaries — a short "Phase N done: X, Y, Z. Tests pass. Ready for Phase N+1?" is sufficient.
7. **One phase = one context window.** Never pull in future-phase scope "while you're at it" — that's what burns credits on rework when direction needs to change later.

---

## Progress Checklist

- [x] Phase 0 — Project Scaffolding & Config
- [x] Phase 1 — SQLite Data Layer (Memory + Logs) — 2026-09-20: test_memory.py passes (2/2)
- [x] Phase 2 — RAG Pipeline (company_handbook.pdf ingestion + retrieval) — 2026-09-20: test_rag.py passes (2/2), 64 chunks / 28 sections ingested
- [x] Phase 3 — LLM Wrapper + No-Hallucination System Prompt — 2026-09-20: test_llm.py passes (2/2), Groq + Gemini fallback both verified live
- [x] Phase 4 — Tool Framework + Internal Tools — 2026-09-20: test_tools.py passes (4/4), dummy tool proves zero-edit extensibility
- [x] Phase 5 — LangGraph Orchestrator (the agent loop) — 2026-09-20: 3/3 manual queries via run_agent.py (RAG, search_database, database->create_summary chain), no infinite loops
- [x] Phase 6 — External Tools (Gmail + Calendar, OAuth) — 2026-09-20: DRY_RUN=true, both email and calendar queries correctly trigger their tool with sane dry-run log entries
- [x] Phase 7 — Logging & Error Handling Hardening — 2026-09-20: tool_node retries 2x w/ backoff, broken send_email test degrades gracefully, view_logs.py shows clear error trace
- [x] Phase 8 — FastAPI Endpoints — 2026-09-20: test_api.py passes (3/3); /chat, /sessions/{id}/history, /sessions/{id}/logs manually verified via curl + /docs
- [x] Phase 9 — Streamlit Frontend — 2026-09-20: verified via Streamlit AppTest (RAG query + tool query render correctly, trace expander works, sidebar log view works, no exceptions)
- [x] Phase 10 — End-to-End Polish & README — 2026-09-20: README rewritten with setup/demo script, requirements.txt pinned to tested versions, full suite (13/13) passes

---

## 0. Opinion / Reality Check

This is a genuinely good portfolio project — it demonstrates the four things that separate "I called an LLM API" from "I built an agent": retrieval, tool use, memory, and multi-step reasoning with observation. Scope is the real risk, not the tech: every individual piece (RAG, one tool, SQLite memory) is small on its own, but trying to build all of it in one pass is how projects stall. The phase breakdown below exists so the repo is always in a working state, and so this file — not a chat history — is what lets you resume after any interruption.

LangGraph is the right framework here specifically because "Think → Retrieve → Reason → Act → Observe → Repeat" maps directly onto its `StateGraph` model. Google OAuth (Gmail/Calendar) is the most fragile part of the whole build, so it's isolated into Phase 6, after everything else already works end-to-end without it.

---

## 1. Free-Only Tech Stack (final — do not relitigate mid-project)

| Layer | Choice | Why |
|---|---|---|
| Reasoning LLM | **Groq API** (`llama-3.3-70b-versatile`) | Free tier, generous rate limits, fast inference — good for multi-step agent loops |
| Fallback LLM | **Google Gemini API** (`gemini-2.0-flash`) | Free tier, used only if Groq errors/rate-limits |
| Embeddings | **sentence-transformers** (`all-MiniLM-L6-v2`), local | No API cost, no rate limits |
| Vector DB | **ChromaDB** (local, persistent) | Free, embedded, no server |
| Memory + logs | **SQLite** | Free, file-based, zero-config |
| Agent framework | **LangGraph** | Free/open-source; models the loop directly |
| Backend | **FastAPI** | Free, async |
| Frontend | **Streamlit** | Free, fastest usable UI |
| Email tool | **Gmail API** | Free with personal Google account (OAuth) |
| Calendar tool | **Google Calendar API** | Free with personal Google account (OAuth) |
| File parsing | **PyPDF** / **pdfplumber** | Free, local |

No paid key anywhere in this stack.

---

## 2. Architecture

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
         |   (single agent, one graph)      |
         +--------------------------------+
                          |
     +-----------+--------+---------+-----------+
     v           v        v         v           v
 System       Memory   Planner   Tool        Observer
 Prompt       Node     Node      Selector    Node
 (retrieval-  (SQLite) (LLM:     Node        (feeds tool
  first,                decides            output back
  no halluc-            next step)         into reasoning)
  ination)
                          |
                 +--------+--------+
                 v                 v
           RAG Retriever      Tool Registry
                 |             +----+----+----+----+
                 v             v    v    v    v    v
            ChromaDB      search_ send_ sched search_ create_
           (doc chunks)    docs   email ule_  db    summary
                                        meeting
                                         |      |
                                         v      v
                                    Gmail/Cal  SQLite
                                    APIs       (mock company DB)
                          |
                          v
                  Final response / draft
                          |
                          v
              Structured log (SQLite: every
              retrieval, tool call, decision)
```

**Loop semantics (LangGraph state machine):**
`Intent Classification -> [needs_retrieval?] -> RAG Search -> Reasoning -> [needs_tool_action?] -> Tool Selector -> Tool Execution -> Observe Result -> [task_complete?]` — loops back to Reasoning if not complete, otherwise -> Final Answer -> Memory Write -> Log Write.

---

## 3. Repository Structure (target, built incrementally)

```
ai-ops-assistant/
|-- app/
|   |-- main.py                 # FastAPI entrypoint
|   |-- config.py                # env/config loader
|   |-- agent/
|   |   |-- graph.py              # LangGraph StateGraph definition
|   |   |-- state.py              # AgentState schema
|   |   |-- system_prompt.py      # retrieval-first / no-hallucination prompt
|   |   |-- planner.py            # planner node logic
|   |-- rag/
|   |   |-- ingest.py             # PDF loading + chunking
|   |   |-- embeddings.py         # sentence-transformers wrapper
|   |   |-- retriever.py          # ChromaDB query interface
|   |-- tools/
|   |   |-- base.py               # Tool base class / registry
|   |   |-- search_documents.py
|   |   |-- search_database.py
|   |   |-- create_summary.py
|   |   |-- send_email.py
|   |   |-- schedule_meeting.py
|   |-- memory/
|   |   |-- db.py                 # SQLite schema + connection
|   |   |-- memory_store.py       # read/write conversation memory
|   |-- logging/
|       |-- logger.py             # structured step logging
|-- data/
|   |-- documents/                # company_handbook.pdf (single source doc)
|   |-- chroma/                   # ChromaDB persistence dir
|-- frontend/
|   |-- streamlit_app.py
|-- tests/
|   |-- ...                       # one test file per phase
|-- .env.example
|-- requirements.txt
|-- README.md
```

---

## 4. Phases

Each phase below is self-contained: goal, what the user must provide (if anything), what to build, and the Definition of Done. Build exactly and only what's listed — nothing from a later phase.

---

### Phase 0 — Project Scaffolding & Config

**Requires from user:** nothing.

**Build:**
- Full repo skeleton matching section 3.
- `requirements.txt` pinned for: fastapi, uvicorn, langgraph, langchain-core, chromadb, sentence-transformers, python-dotenv, groq, google-generativeai, streamlit, pypdf, pdfplumber, google-auth, google-auth-oauthlib, google-api-python-client.
- `app/config.py`: loads env vars via python-dotenv, sensible defaults, errors only for keys actually required at runtime.
- `.env.example`: every env var the whole project will eventually need (GROQ_API_KEY, GEMINI_API_KEY, GOOGLE_CLIENT_ID/SECRET, DRY_RUN, etc.), even ones unused yet.
- `app/main.py`: FastAPI app with `GET /health` -> `{"status": "ok"}`.
- Minimal `README.md`: venv setup + run instructions.

**Definition of Done:** `uvicorn app.main:app` runs; `GET /health` returns 200.

---

### Phase 1 — SQLite Data Layer (Memory + Logs)

**Requires from user:** nothing.

**Build:**
- `app/memory/db.py`: create-if-not-exists schema with two tables:
  1. `conversations`: id, session_id, role, content, timestamp
  2. `execution_logs`: id, session_id, step_type (retrieval/tool_call/decision/error), name, input, output, status, duration_ms, timestamp
- `app/memory/memory_store.py`: `save_message()`, `get_recent_messages(session_id, n)`, `save_log()`, `get_logs(session_id)`. Plain `sqlite3`, no ORM.
- `tests/test_memory.py`: inserts a fake message + log entry, reads back, asserts correctness.

**Definition of Done:** `test_memory.py` passes.

---

### Phase 2 — RAG Pipeline (company_handbook.pdf ingestion + retrieval)

Compatibility note (verified on Python 3.10.11): the working pair is `numpy==1.26.4` with `chromadb==0.5.23`. This combination resolves cleanly and remains compatible with the Python 3.10 runtime; newer `numpy`/`chromadb` versions backtrack to requiring Python >=3.11 or drift into incompatible persisted-schema formats.

**Requires from user:** `data/documents/company_handbook.pdf` — a single PDF the user writes themselves, covering multiple distinct sections (company overview, org structure, HR policies, onboarding, IT/security, project process, internal FAQ, etc.), each under a clear heading (e.g. `## Leave Policy`). This is the entire RAG showcase for the project, so distinct, clearly-headed sections matter more than length. **Do not proceed with this phase until the file exists** — ask the user for it if missing.

**Build:**
- `app/rag/embeddings.py`: sentence-transformers (`all-MiniLM-L6-v2`) wrapper, `embed_texts(list[str]) -> list[vector]`.
- `app/rag/ingest.py`: extracts text from `company_handbook.pdf` (pypdf or pdfplumber), chunks (~400-500 tokens, ~50 overlap) while trying not to split a heading from its following content, embeds, upserts into a persistent ChromaDB collection at `data/chroma/`, storing detected section heading as metadata per chunk where feasible.
- `app/rag/retriever.py`: `retrieve(query: str, k: int = 4) -> list of {text, source_section, score}`.
- `tests/test_rag.py`: ingest the PDF, run 3+ queries targeting 3 different sections (infer reasonable queries from whatever sections actually exist in the PDF), assert each query's top result comes from the expected section.

**Definition of Done:** ingestion populates ChromaDB; all 3+ section-targeted test queries return chunks from the correct section — proving retrieval discriminates between sections, not just returning generic top chunks.

---

### Phase 3 — LLM Wrapper + No-Hallucination System Prompt

**Requires from user:** GROQ_API_KEY and GEMINI_API_KEY in `.env` (free-tier signup at console.groq.com and Google AI Studio).

**Build:**
- `app/agent/system_prompt.py`: SYSTEM_PROMPT instructing the model to (1) act like an internal operations employee, not a chatbot, (2) prefer retrieved company context over its own knowledge, (3) explicitly say "I don't have that information in the company knowledge base" when retrieval is empty/irrelevant rather than guessing, (4) only call a tool when genuinely needed, (5) never fabricate tool results.
- `app/agent/llm.py`: `call_llm(messages, system_prompt)` — tries Groq (`llama-3.3-70b-versatile`) first, falls back to Gemini (`gemini-2.0-flash`) on error/rate-limit, retries transient errors up to 2x with backoff.
- `tests/test_llm.py`: sends a sample question through `call_llm` and prints the response; a second test simulates a Groq failure and confirms Gemini fallback triggers.

**Definition of Done:** both tests pass and produce real completions.

---

### Phase 4 — Tool Framework + Internal Tools

**Requires from user:** nothing (uses Phase 2's retriever + Phase 3's LLM).

**Build:**
- `app/tools/base.py`: `Tool` base class (name, description, input schema, `run()`), `TOOL_REGISTRY` dict, tools self-register via a `@register_tool` decorator — adding a future tool must require zero changes to existing files.
- `app/tools/search_documents.py`: wraps `app/rag/retriever.py`.
- `app/tools/search_database.py`: seed a small mock "company database" table in SQLite (pick something plausible — e.g. employees, tickets, or projects) with a few rows; Tool runs simple filtered queries against it.
- `app/tools/create_summary.py`: Tool that takes text/context and calls `app/agent/llm.py` to produce a structured summary.
- `tests/test_tools.py`: calls each tool directly with sample input, asserts output shape.

**Definition of Done:** all three tools work standalone and `test_tools.py` passes; a new dummy 4th tool can be registered by adding one file with no edits elsewhere (verify this claim).

---

### Phase 5 — LangGraph Orchestrator (the agent loop)

**Requires from user:** nothing (wires together everything from Phases 1-4).

**Build:**
- `app/agent/state.py`: typed `AgentState` (messages, retrieved_context, planned_action, tool_result, final_answer, session_id, step_count, max_steps guard).
- `app/agent/planner.py`: planner node — given state, decides `retrieve_more` / `call_tool(name, args)` / `respond_final`, via a JSON-constrained `call_llm` prompt.
- `app/agent/graph.py`: LangGraph `StateGraph` wiring: `intent_node -> retrieve_node (conditional) -> reason_node -> tool_node (conditional, dispatches via TOOL_REGISTRY) -> observe_node` -> loops back to `reason_node` until planner says `respond_final` or `max_steps` hit -> `final_node` (writes memory + logs via Phase 1 functions at every node transition).
- `scripts/run_agent.py`: CLI, takes a query arg, runs it through the compiled graph, prints final answer + step-by-step trace.

**Definition of Done:** three manual test queries work via `scripts/run_agent.py` — (1) pure RAG question grounded in the handbook, (2) a question that correctly triggers `search_database`, (3) a question that correctly triggers `create_summary` — each with a sane trace and no infinite loop.

---

### Phase 6 — External Tools (Gmail + Calendar, OAuth)

**Requires from user:** a Google Cloud project with Gmail API + Calendar API enabled, OAuth 2.0 Desktop credentials downloaded as `credentials.json`. If missing, produce `docs/google_oauth_setup.md` walking the user through creating these (free tier), then wait for the user to confirm it's done before testing.

**Build:**
- `app/tools/send_email.py`: Gmail API tool (google-auth + google-api-python-client). Respects a `DRY_RUN` env flag (default true) — when true, logs the composed email instead of sending.
- `app/tools/schedule_meeting.py`: same pattern via Google Calendar API, also respecting `DRY_RUN`.
- Register both in `TOOL_REGISTRY` the same way as Phase 4 — no planner/graph changes should be needed beyond the tools becoming available.
- `docs/google_oauth_setup.md` as above.

**Definition of Done:** with `DRY_RUN=true`, a query like "email a summary of the leave policy to test@example.com" and one like "schedule a 30-min meeting tomorrow at 3pm" both correctly trigger their tool and produce a sane dry-run log entry.

---

### Phase 7 — Logging & Error Handling Hardening

**Requires from user:** nothing.

**Build:**
- Wrap every tool execution in `tool_node` (try/except), log failures via `save_log()` with `status="error"`, retry transient failures up to 2x with backoff before surfacing a graceful (non-stack-trace) message to the user.
- Enforce the `max_steps` safety net from Phase 5's `AgentState`: clean termination message if hit, never an infinite loop.
- `scripts/view_logs.py`: CLI, takes a `session_id`, prints a clean chronological human-readable trace from `execution_logs`.

**Definition of Done:** deliberately breaking one tool (e.g. invalid Gmail token) does not crash the agent — it degrades gracefully and the log clearly shows the failure via `view_logs.py`.

---

### Phase 8 — FastAPI Endpoints

**Requires from user:** nothing.

**Build:**
- `POST /chat` — body `{session_id, message}` -> `{answer, steps}` (steps = node-transition trace), runs the message through the compiled agent graph.
- `GET /sessions/{session_id}/history` — returns conversation memory.
- `GET /sessions/{session_id}/logs` — returns structured execution log.
- Pydantic models, sane HTTP error codes on unhandled errors (should be rare given Phase 7).
- `tests/test_api.py`: FastAPI TestClient hits `/chat` with a sample RAG question, asserts 200 + non-empty answer.

**Definition of Done:** `test_api.py` passes; all three endpoints manually verified via `/docs` or curl.

---

### Phase 9 — Streamlit Frontend

**Requires from user:** nothing (talks to Phase 8's API).

**Build:**
- `frontend/streamlit_app.py`: persistent `session_id` via `st.session_state`; chat UI (`st.chat_message`/`st.chat_input`); per-turn expandable "agent trace" section (retrieved chunks + section, tool calls with input/output, decisions) from `/chat`'s `steps` field; sidebar button to view full session log via `GET /sessions/{id}/logs`.

**Definition of Done:** running FastAPI + `streamlit run frontend/streamlit_app.py` together gives a working chat UI where a RAG question and a tool-triggering question both display correctly, with trace expansion working.

---

### Phase 10 — End-to-End Polish & README

**Requires from user:** nothing — final review pass.

**Build:**
- Rewrite `README.md`: overview, architecture diagram, full setup (venv, `.env`, Google OAuth, ingesting `company_handbook.pdf`), how to run backend + frontend, a "demo script" of 4-5 example queries covering RAG, database tool, summary tool, email (dry run), calendar (dry run), in order.
- `docs/DESIGN_DECISIONS.md`: why LangGraph, why local embeddings, single-agent vs multi-agent, the no-hallucination system prompt approach — written for a portfolio/interview reviewer.
- Final pass: confirm every `requirements.txt` version is pinned; confirm a fresh venv clone-to-demo flow works end to end.

**Definition of Done:** a clean clone + README-only setup reaches a working demo in under 15 minutes.

---

## 5. Session-Resumption Protocol

- The `## Progress Checklist` above is the single source of truth across sessions — always check it (and verify against actual repo state) before doing anything.
- If interrupted mid-phase, the next session should first assess what partial work exists for that phase, decide whether to keep or discard it, then finish the phase's Definition of Done before moving on.
- Never start a phase whose "Requires from user" item is missing — stop and ask for it instead of guessing or stubbing it silently.
