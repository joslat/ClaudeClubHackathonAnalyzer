# CLAUDE.md — Hackathon Repository Analyzer

## Build & Run

```bash
# Install in development mode with all tools
pip install -e ".[dev,quality]"

# Run CLI
hackanalyze analyze https://github.com/owner/repo --skip-plagiarism

# Run with full analysis
GITHUB_TOKEN=... ANTHROPIC_API_KEY=... hackanalyze analyze https://github.com/owner/repo
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_scoring.py -v

# With coverage
pytest tests/ --cov=hackathon_analyzer --cov-report=term-missing
```

## Project Structure

```
hackathon_analyzer/
  cli.py              # Entry point — Typer app (keep thin)
  config.py           # Pydantic Settings from env vars
  core/
    models.py         # ALL data contracts — edit carefully (everything imports this)
    pipeline.py       # Orchestrator — error recovery per step
    repo_manager.py   # Git clone/update/cleanup
  analyzers/          # 13 independent analysis functions (pure functions)
  scoring/            # Rubric weights + score aggregation
  reporting/          # Markdown + Rich terminal output
  integrations/       # GitHub API, Claude API clients
  utils/              # subprocess, cache, file helpers
```

## Key Conventions

- **No shell=True ever** — all subprocess calls go through `utils/subprocess_runner.run_with_timeout()`
- **Analyzers are pure functions**: `analyze_X(path, ...) -> XResult` — no side effects, no API calls
- **Claude and GitHub are optional** — all features degrade gracefully without API keys
- **Error recovery**: pipeline wraps each step in try/except; failures go to `result.errors`, analysis continues
- **Models first**: if you add a field to a model, update the relevant scorer and report section

## Environment Variables

```
GITHUB_TOKEN          # Required for plagiarism detection (GitHub code search)
ANTHROPIC_API_KEY     # Required for AI architecture summaries and plagiarism verdicts
REPOS_DIR             # Where cloned repos go (default: ./repos)
REPORTS_DIR           # Where reports go (default: ./reports)
CACHE_DIR             # Where API response cache goes (default: ./cache)
BUILD_TIMEOUT_SECONDS # Default: 120
CLONE_TIMEOUT_SECONDS # Default: 300
MAX_REPO_SIZE_MB      # Default: 500
CACHE_TTL_SECONDS     # GitHub search cache TTL (default: 86400 = 24h)
CLAUDE_MODEL          # Claude model to use (default: claude-opus-4-5)
HACKATHON_START_DATE  # ISO date when hackathon started (for freshness scoring)
```

## Adding a New Analyzer

1. Create `hackathon_analyzer/analyzers/new_thing.py` with function `analyze_new_thing(path, ...) -> NewThingResult`
2. Add `NewThingResult` dataclass to `core/models.py` and `new_thing: Optional[NewThingResult] = None` to `RepoAnalysisResult`
3. Add `_run_new_thing()` step to `core/pipeline.py`
4. Add `_score_new_thing()` to `scoring/scorer.py` and update `DIMENSIONS` in `scoring/rubric.py`
5. Add a report section to `reporting/per_repo_report.py`
