# Hackathon Analyzer Suite

A monorepo of tools for analyzing and judging hackathon submissions using AI.

## Projects

| Project | Folder | What it does |
|---|---|---|
| **Hackathon Analyzer** | `hackathon-analyzer/` | CLI that clones GitHub repos and scores them across 12 dimensions (1.0–10.0) |
| **Hackathon Chat** | `hackathon-chat/` | Streamlit chat app — talk to an AI agent that runs the analyzer and searches the web |

The chat app drives the analyzer. The analyzer works standalone too.

---

## Quickstart

### Hackathon Analyzer

```bash
cd hackathon-analyzer
pip install -e ".[dev,quality]"
cp .env.example .env          # add ANTHROPIC_API_KEY and GITHUB_TOKEN (both optional)
hackanalyze analyze https://github.com/owner/repo --skip-plagiarism
```

Reports are written to `hackathon-analyzer/reports/`.

### Hackathon Chat

```bash
cd hackathon-chat
pip install -e .
cp .env.example .env          # configure your LLM provider credentials
streamlit run app.py
```

Opens a browser chat UI. Type a GitHub URL and the agent handles the rest. Supports three LLM providers: **Azure OpenAI**, **Ollama** (local), and **Anthropic Claude** — selectable in the sidebar.

---

## Environment Variables

Each project has its own `.env.example` with full documentation. Below is a summary.

### Hackathon Chat

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `CHAT_PROVIDER` | No | `azure` | LLM provider: `azure`, `ollama`, or `anthropic` |
| `AZURE_OPENAI_ENDPOINT` | For Azure | — | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | For Azure | — | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | No | `gpt-4.1` | Azure deployment name |
| `AZURE_OPENAI_API_VERSION` | No | `2025-03-01-preview` | Azure API version |
| `ANTHROPIC_API_KEY` | For Anthropic | — | Anthropic API key (also used by analyzer) |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-6` | Anthropic model name |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434/v1` | Ollama endpoint |
| `OLLAMA_MODEL` | No | `gpt-oss:20b` | Ollama model name |
| `HACKANALYZE_PATH` | No | auto-detected | Path to `hackanalyze` binary |

### Hackathon Analyzer

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GITHUB_TOKEN` | No | — | GitHub code search for plagiarism detection |
| `ANTHROPIC_API_KEY` | No | — | AI architecture summaries and plagiarism verdicts |
| `CLAUDE_MODEL` | No | `claude-opus-4-5` | Claude model for AI analysis |

---

## How They Relate

```
hackathon-chat  →  subprocess  →  hackanalyze CLI  →  reports/*.md
```

The chat app calls the analyzer as a CLI subprocess and reads the generated Markdown reports. There is no direct Python import between them — you can develop and run each project independently.
