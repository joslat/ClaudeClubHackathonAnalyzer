# Hackathon Chat Interface — Implementation Plan

> **Status**: Complete | **Date**: 2026-03-07 | **Version**: 1.0

---

## Overview

This document describes the step-by-step implementation of the `hackathon-chat` application — a Streamlit chat interface that wraps the `hackathon-analyzer` CLI behind an AI agent.

---

## Phase 1: Project Scaffold

**Files created:**
- `pyproject.toml` — package metadata, dependencies, build system
- `.env.example` — template for environment variables
- `agent/__init__.py` — empty package marker

**Key decisions:**
- Use `hatchling` as build backend (lightweight, modern)
- Minimal dependencies: `streamlit`, `anthropic`, `duckduckgo-search`, `python-dotenv`
- No direct dependency on `hackathon-analyzer` — integration is via subprocess

---

## Phase 2: Web Search Module (`agent/web_search.py`)

**What it does:** Thin wrapper around the `duckduckgo-search` package.

**Interface:**
```python
search(query: str, max_results: int = 5) -> list[dict[str, str]]
# Returns: [{title, url, snippet}, ...]
```

**Design notes:**
- Lazy import of `duckduckgo_search` — returns a user-friendly error if not installed
- All exceptions caught and returned as error dicts (never raises to the agent)
- Stateless — safe to call from any context

---

## Phase 3: Analyzer Bridge (`agent/analyzer_bridge.py`)

**What it does:** Calls the `hackanalyze` CLI via subprocess and parses the generated `.md` report files.

**Why subprocess, not Python import:**
- The analyzer is being developed in parallel; its internal Python API may change
- The CLI interface (`analyze`, `batch`, `clean`, flags) is stable per the analyzer's PLAN.md
- Only this file needs updating when the analyzer evolves

**Key functions:**

| Function | What it does |
|---|---|
| `analyze_repo(url, skip_build, skip_plagiarism)` | Runs `hackanalyze analyze <url>`, reads report |
| `batch_analyze(urls, skip_build, skip_plagiarism)` | Runs `hackanalyze analyze <url1> <url2>...` |
| `list_reports()` | Scans `reports/per-repo/` and `reports/summary/` |
| `read_report(slug)` | Reads a specific `.md` report file |
| `clean_repos()` | Runs `hackanalyze clean` |

**Report parsing:**
- `_parse_score_from_report(text)` — regex extracts the 1.0–10.0 total score
- `_parse_dimensions_from_report(text)` — regex extracts the markdown table rows for all 7 dimensions
- `_find_report(slug)` — looks up the report file with fuzzy matching on slug

**Configuration via env vars:**
- `HACKANALYZE_PATH` — override the binary path (default: `hackanalyze`)
- `HACKANALYZE_REPORTS_DIR` — override reports directory (default: auto-detected sibling folder)

---

## Phase 4: Tool Definitions (`agent/tools.py`)

**What it does:** Defines the 5 tools as JSON schemas (for Claude) and dispatches tool calls to the bridge and web search.

**Tools defined:**

| Tool | Input | Description |
|---|---|---|
| `analyze_repo` | `url`, `skip_build`, `skip_plagiarism` | Analyze a single repo |
| `batch_analyze` | `urls[]`, `skip_build`, `skip_plagiarism` | Analyze multiple repos |
| `list_reports` | (none) | List existing reports |
| `read_report` | `slug` | Read a specific report |
| `web_search` | `query`, `max_results` | DuckDuckGo search |

**Dispatcher:**
```python
dispatch(tool_name: str, tool_input: dict) -> Any
```
Routes each tool call to the correct function. Returns JSON-serializable values. All errors are returned as `{"error": "..."}` dicts rather than raising.

---

## Phase 5: Chat Agent (`agent/chat_agent.py`)

**What it does:** Implements the Claude tool_use agentic loop.

**Loop logic:**
1. Build `messages` list (system prompt + conversation history)
2. Call `client.messages.create(model, tools, messages)`
3. Parse response content blocks:
   - `text` blocks → yield text chunks for streaming
   - `tool_use` blocks → collect tool calls
4. If tool calls present: execute each via `dispatch()`, append results to messages, repeat
5. If `stop_reason == "end_turn"`: loop ends

**Callbacks for UI feedback:**
```python
on_tool_start(tool_name, tool_input)  # Called before executing a tool
on_tool_end(tool_name, result)         # Called after tool completes
```
These drive `st.status()` spinners in the Streamlit UI.

**System prompt instructs Claude to:**
- Act as a hackathon judge assistant
- Use tools proactively (don't ask "should I analyze this?")
- Present results concisely (the UI renders the score cards, Claude adds interpretation)
- Be direct with recommendations

**Model:** `claude-sonnet-4-6`

---

## Phase 6: Result Formatters (`agent/formatters.py`)

**What it does:** Renders tool results as Streamlit visualizations inline with the chat.

**Per-tool renderers:**

| Tool | Visualization |
|---|---|
| `analyze_repo` | `st.metric` score, `st.progress` bar, `st.dataframe` dimension table, expandable full report |
| `batch_analyze` | Ranking table sorted by score, expandable per-repo cards |
| `list_reports` | Dataframe of slugs, paths, modified dates |
| `read_report` | Score metric + expandable full markdown |
| `web_search` | Formatted list with clickable titles and snippets |

**Score color indicators:**
- 🟢 8.0+ (excellent)
- 🟡 6.0–7.9 (good)
- 🟠 4.0–5.9 (fair)
- 🔴 below 4.0 (poor)

**Dimension score bar:**
ASCII progress bar (`█░`) scaled to the 0.0–1.0 score, shown in the dataframe.

---

## Phase 7: Streamlit App (`app.py`)

**What it does:** Wires everything into a Streamlit chat application.

**Layout:**
- **Left sidebar**: API key, analysis toggles (skip-build, skip-plagiarism), binary path, reports dir, clear conversation button
- **Main area**: Chat history + input

**Session state:**
- `messages` — full Claude API message history (persisted across Streamlit reruns)
- `tool_results` — list of `{message_index, tool, result}` for replaying visualizations on page reruns

**Message rendering:**
- Iterates `session_state.messages` and renders each with `st.chat_message`
- After each assistant message, renders any tool visualizations stored at that message index
- Handles both raw string content and Claude API content block lists

**Input handling:**
1. User submits a message via `st.chat_input`
2. Guard check: require API key
3. Inject sidebar toggle state (skip-build / skip-plagiarism) into the message as a note
4. Call `chat_agent.run()` with `on_tool_start` / `on_tool_end` callbacks
5. Stream text with cursor (`▌`) until complete
6. Render tool visualizations immediately after the response
7. Persist everything to session state for history replay

---

## Verification Checklist

- [ ] `pip install -e .` — installs cleanly
- [ ] `streamlit run app.py` — opens in browser, welcome message shown
- [ ] Enter Anthropic API key in sidebar
- [ ] Type: `"analyze https://github.com/tiangolo/fastapi --skip-plagiarism"` → agent calls tool, shows spinner, renders score card
- [ ] Type: `"search for best hackathon projects 2025"` → web results appear in chat
- [ ] Type: `"list my previous reports"` → report inventory shown as dataframe
- [ ] Type: `"compare the last two repos I analyzed"` → Claude reasons over session context
- [ ] Clear conversation → history resets, welcome message re-appears
- [ ] Missing API key → clear error message shown, chat blocked

---

## Future Enhancements

- **Streaming tool feedback**: Stream CLI output in real-time (requires analyzer to support streaming output)
- **JSON sidecar files**: Once the analyzer exports structured JSON alongside `.md` reports, update `analyzer_bridge.py` to read JSON instead of regex-parsing markdown
- **Report export**: Add a "Download report" button per analysis
- **Hackathon session management**: Save/load named sessions (e.g., "Spring 2026 Hackathon")
- **Score history chart**: `st.line_chart` showing score trends across multiple analyses
- **Direct Python import mode**: Optional fast-path using `hackathon_analyzer` Python API when the package is stable

---

*Generated by Claude Sonnet 4.6 | Hackathon Chat v0.1.0*
