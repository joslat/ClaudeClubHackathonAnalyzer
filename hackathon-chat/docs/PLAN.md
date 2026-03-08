# Hackathon Chat Interface — Plan

> **Status**: Approved | **Date**: 2026-03-07 | **Version**: 1.0

---

## Context

The `hackathon-analyzer` project (being built in parallel) is a Python CLI tool (`hackanalyze`) that clones GitHub repos and produces multi-dimensional technical analysis reports. This application is a **chat agent** that wraps the analyzer behind a conversational interface. The user talks naturally to an agent that can run analyses, show results, and search the web.

**Design philosophy**: Keep it simple. Streamlit gives a polished chat UI with zero frontend code. Claude tool_use drives the agent. A thin adapter layer isolates the chat app from internal changes in the analyzer.

**Key constraint**: Since the analyzer is actively being developed by another instance, the integration is built against the stable **CLI interface** (defined in the analyzer's PLAN.md), not its internal Python modules. Only `analyzer_bridge.py` needs updating as the analyzer evolves.

---

## Project Structure

```
hackathon-chat/
├── pyproject.toml             # Package config + deps
├── .env.example               # ANTHROPIC_API_KEY, HACKANALYZE_PATH, etc.
├── PLAN.md                    # This document
├── IMPLEMENTATION_PLAN.md     # Step-by-step build plan
├── app.py                     # Streamlit entry point — run with: streamlit run app.py
│
└── agent/
    ├── __init__.py
    ├── chat_agent.py          # Multi-provider tool_use agentic loop (Azure, Ollama, Anthropic)
    ├── tools.py               # Tool JSON schemas + dispatcher
    ├── analyzer_bridge.py     # Calls hackathon-analyzer CLI, parses reports
    ├── web_search.py          # DuckDuckGo search (no API key required)
    └── formatters.py          # Streamlit visualizations for tool results
```

---

## Tech Stack

| Concern | Choice | Reason |
|---|---|---|
| Chat UI | Streamlit (`st.chat_input`, `st.chat_message`) | Built-in chat primitives, markdown rendering, metrics, tables — zero JS |
| Agent | Multi-provider: Azure OpenAI, Ollama, Anthropic Claude | Tool_use API, streaming, strong reasoning |
| Analyzer integration | CLI subprocess → parse generated reports | Decoupled from internal Python API; stable CLI spec per analyzer's PLAN.md |
| Web search | `duckduckgo-search` Python package | Free, no API key, lightweight |
| Visualizations | `st.metric`, `st.dataframe`, `st.progress` | Native Streamlit, no extra charting libs |

---

## Agent Tools (5 tools)

### 1. `analyze_repo`
Runs `hackanalyze analyze <url> [--skip-build] [--skip-plagiarism]` and returns parsed score + dimension breakdown.

### 2. `batch_analyze`
Runs `hackanalyze analyze <url1> <url2> ...` and returns a ranked list of results plus the summary report path.

### 3. `list_reports`
Scans the analyzer's `reports/` directory and returns a list of all per-repo and summary reports.

### 4. `read_report`
Reads a specific report by slug (e.g. `tiangolo-fastapi`) and returns the full markdown text for Claude to reason over.

### 5. `web_search`
DuckDuckGo search — returns `[{title, url, snippet}]` for any query.

---

## Chat Agent Loop

Multi-provider agentic loop (native tool_use for Anthropic, OpenAI-compatible function calling for Azure/Ollama):
1. Build messages list with system prompt + conversation history
2. Send to the selected LLM provider with all tool definitions
3. If response contains tool calls: execute tools, append results, repeat (max 5 rounds)
4. If response is final: yield text to Streamlit

Tool callbacks (`on_tool_start`, `on_tool_end`) drive `st.status()` spinners for live feedback.

---

## Streamlit UI

- **Sidebar**: LLM provider selector (Azure/Ollama/Anthropic) with per-provider credentials, toggles for skip-build / skip-plagiarism, hackanalyze path config, clear conversation button
- **Chat area**: Full history replay with inline tool visualizations
- **Tool visualizations** (rendered inline after each tool call):
  - `analyze_repo` → `st.metric` total score + `st.dataframe` dimension table + `st.progress` bars + expandable full report
  - `batch_analyze` → ranking table + expandable per-repo cards
  - `list_reports` → dataframe of available reports
  - `read_report` → expandable full markdown report
  - `web_search` → formatted list of results with links

---

## Analyzer Bridge Strategy

The bridge calls the stable CLI interface and reads generated `.md` files. It does **not** import `hackathon_analyzer.*` directly. This means:

- Internal Python API changes in the analyzer do not break the chat app
- The CLI flags (`--skip-build`, `--skip-plagiarism`) are stable per the analyzer's PLAN.md
- When the analyzer adds JSON output (a potential future enhancement), update only `analyzer_bridge.py`

---

## Dependencies

```toml
streamlit>=1.35
anthropic>=0.28
openai>=1.0
duckduckgo-search>=6.0
python-dotenv>=1.0
```

---

## Running the App

```bash
cd hackathon-chat
pip install -e .
cp .env.example .env
# Edit .env with your LLM provider credentials
streamlit run app.py
```

---

*Generated by Claude Sonnet 4.6 | Hackathon Chat v0.1.0*
