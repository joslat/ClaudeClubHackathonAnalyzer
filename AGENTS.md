# AGENTS.md — AI Agent Instructions for This Repository

This file instructs AI agents (Claude Code and others) on the structure, purpose, and conventions of this repository.

---

## Repository Overview

This monorepo contains two related Python projects that work together:

| Project | Folder | Role |
|---|---|---|
| **Hackathon Analyzer** | `hackathon-analyzer/` | CLI engine — clones repos and produces analysis reports |
| **Hackathon Chat** | `hackathon-chat/` | Chat agent UI — conversational interface over the analyzer |

They are developed independently and communicate only through the analyzer's stable CLI interface. Do not introduce a direct Python import dependency from `hackathon-chat` into `hackathon-analyzer` internals.

---

## Project 1: hackathon-analyzer

### Purpose

A Python CLI tool (`hackanalyze`) for hackathon judges. Given GitHub or GitLab repository URLs, it clones each repo and runs a multi-dimensional technical analysis, producing scored Markdown reports. Scores range from 1.0 to 10.0.

### Scoring Dimensions (12 total, weights sum to 100%)

| Dimension | Weight |
|---|---|
| Code Quality | 12% |
| Architecture | 12% |
| Promise vs Reality | 12% |
| Testing | 10% |
| Originality (plagiarism) | 10% |
| Vision & Ambition | 8% |
| Documentation | 8% |
| Build Success | 8% |
| Tech Stack Novelty | 6% |
| Hackathon Freshness | 6% |
| AI Integration | 5% |
| Structure | 3% |

### CLI Interface (stable — do not change signatures without updating AGENTS.md)

```bash
# Analyze one or more repos
hackanalyze analyze <url> [<url>...] [--skip-build] [--skip-plagiarism] [--output-dir PATH]

# Analyze from a file of URLs (one per line)
hackanalyze batch <file>

# Delete all cloned repos
hackanalyze clean
```

### Key Source Files

| File | Purpose |
|---|---|
| `hackathon_analyzer/cli.py` | Typer entry point |
| `hackathon_analyzer/core/pipeline.py` | Orchestrates all analysis steps |
| `hackathon_analyzer/core/models.py` | All dataclasses — the lingua franca between modules |
| `hackathon_analyzer/core/repo_manager.py` | Clone, update, cleanup repos |
| `hackathon_analyzer/analyzers/` | 13 independent analysis modules |
| `hackathon_analyzer/scoring/scorer.py` | Aggregates analyzer outputs → 1.0–10.0 score |
| `hackathon_analyzer/reporting/` | Markdown report generation |
| `hackathon_analyzer/integrations/` | GitHub API client, Claude API client |
| `hackathon_analyzer/config.py` | Pydantic Settings — all env vars |

### Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | No | — | Enables Claude architecture narratives and plagiarism verdicts |
| `GITHUB_TOKEN` | No | — | Enables GitHub code search for plagiarism detection |
| `REPOS_DIR` | No | `./repos` | Where repos are cloned |
| `REPORTS_DIR` | No | `./reports` | Where reports are written |
| `MAX_REPO_SIZE_MB` | No | `500` | Safety guard before cloning |

### Output

- Per-repo reports: `reports/per-repo/<owner>-<repo>-report.md`
- Summary report: `reports/summary/summary-<timestamp>.md`

### Development Commands

```bash
cd hackathon-analyzer
pip install -e ".[dev,quality]"
pytest tests/ -v
hackanalyze analyze https://github.com/tiangolo/fastapi --skip-plagiarism
```

See `hackathon-analyzer/docs/PLAN.md` for the full specification.

---

## Project 2: hackathon-chat

### Purpose

A Streamlit chat application with multi-provider LLM support (Azure OpenAI, Ollama, Anthropic Claude). The user converses with an AI agent that runs analyses, interprets results, and searches the web. It wraps the `hackanalyze` CLI via subprocess — it does **not** import `hackathon_analyzer` Python modules directly.

### Interface

```bash
cd hackathon-chat
pip install -e .
cp .env.example .env   # configure LLM provider credentials
streamlit run app.py
```

Opens a browser chat UI. The user can type naturally:
- *"Analyze https://github.com/owner/repo"*
- *"Compare these three repos: ..."*
- *"Search the web for best hackathon projects 2025"*
- *"Show me previous reports"*

### Agent Tools (Claude tool_use)

| Tool | What it does |
|---|---|
| `analyze_repo` | Calls `hackanalyze analyze <url>`, parses the report |
| `batch_analyze` | Calls `hackanalyze analyze <url1> <url2>...`, returns ranking |
| `list_reports` | Scans the reports directory, returns available slugs |
| `read_report` | Reads a specific `.md` report for Claude to reason over |
| `web_search` | DuckDuckGo search — no API key required |

### Key Source Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI — entry point |
| `agent/chat_agent.py` | Multi-provider tool_use agentic loop (Azure, Ollama, Anthropic) |
| `agent/tools.py` | Tool JSON schemas + dispatcher |
| `agent/analyzer_bridge.py` | Subprocess calls to `hackanalyze` + report parsing |
| `agent/web_search.py` | DuckDuckGo wrapper |
| `agent/formatters.py` | Streamlit score cards, tables, progress bars |

### Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | For Anthropic provider | — | Powers the Claude chat agent |
| `AZURE_OPENAI_ENDPOINT` | For Azure provider | — | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | For Azure provider | — | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | No | `gpt-4.1` | Azure deployment name |
| `AZURE_OPENAI_API_VERSION` | No | `2025-03-01-preview` | Azure API version |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-6` | Anthropic model name |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434/v1` | Ollama endpoint |
| `OLLAMA_MODEL` | No | `gpt-oss:20b` | Ollama model name |
| `CHAT_PROVIDER` | No | `azure` | Default LLM provider (`azure`, `ollama`, `anthropic`) |
| `HACKANALYZE_PATH` | No | `hackanalyze` | Path to the analyzer binary |
| `HACKANALYZE_REPORTS_DIR` | No | Auto-detected sibling | Where to find generated reports |

### Integration Rule

`analyzer_bridge.py` is the **only** file that may know about the analyzer's internals. All other files in `hackathon-chat` are completely independent. When the analyzer CLI changes, update only `analyzer_bridge.py`.

See `hackathon-chat/docs/PLAN.md` and `hackathon-chat/docs/IMPLEMENTATION_PLAN.md` for full details.

---

## README Maintenance Requirement

**Agents must keep `README.md` at the repository root up to date.**

The root `README.md` is the front door for any human or agent encountering this repo. It must always be accurate, concise, and easy to scan. Maintain it whenever any of the following change:

- A new project is added to the monorepo
- A project is renamed or removed
- The CLI interface of either project changes
- Installation steps change
- Environment variable requirements change

### What the root README must contain

1. **What this repo is** — one sentence
2. **Projects at a glance** — a table: name, folder, what it does
3. **Quickstart for each project** — install + run in under 5 lines each
4. **Environment variables** — the minimum required to run each project
5. **How the two projects relate** — which depends on which and how

### What the root README must NOT contain

- Implementation details (those belong in each project's own docs/PLAN.md)
- Scoring rubric details
- Full CLI flag references
- File-by-file breakdowns

Keep it short. A reader should understand the repo and be running something within 2 minutes.

---

## General Conventions

- **Python >= 3.11** for both projects
- **Pydantic v2** for data models in the analyzer
- **Never use `shell=True`** in subprocess calls — both projects deal with untrusted repo content
- **Graceful degradation**: both projects work without optional API keys (Claude, GitHub)
- Each project has its own `pyproject.toml` and is installed independently
- Secrets go in `.env` files — never committed (both `.gitignore` files exclude `.env`)
