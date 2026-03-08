# Hackathon Repository Analyzer — Implementation Plan

> **Status**: Approved | **Date**: 2026-03-07 | **Version**: 1.0

---

## Context

Building a Python CLI tool (`hackanalyze`) that accepts GitHub/GitLab repo URLs, clones them, performs multi-dimensional technical analysis, and generates Markdown reports. Designed for hackathon judges to objectively evaluate submissions at scale. The tool also produces a Vision Document and an Implementation Plan Proposal as standalone deliverables.

**Technology choices**: Python + Typer CLI, GitHub code search API + Claude AI for plagiarism detection.

---

## Project Root

All code lives in: `c:\git\ClaudeCodeSetup\hackathon-analyzer\`

---

## Project Structure

```
hackathon-analyzer/
├── pyproject.toml                        # Package, deps, entry point
├── .env.example                          # GITHUB_TOKEN, ANTHROPIC_API_KEY, etc.
├── .gitignore                            # Excludes repos/, reports/, cache/, .env
├── README.md                             # User-facing quickstart
├── PLAN.md                               # This document
├── VISION.md                             # Vision document (deliverable)
├── IMPLEMENTATION_PLAN_PROPOSAL.md       # Three approaches doc (deliverable)
├── CLAUDE.md                             # Build/test commands for AI-assisted dev
│
├── repos/                                # Cloned repos (gitignored)
├── reports/per-repo/                     # Per-repo Markdown reports (gitignored)
├── reports/summary/                      # Summary reports (gitignored)
├── cache/github_search/                  # GitHub API response cache (gitignored)
│
├── hackathon_analyzer/
│   ├── __init__.py
│   ├── cli.py                            # Typer app: analyze, batch, clean commands
│   ├── config.py                         # Pydantic Settings, env vars, constants
│   │
│   ├── core/
│   │   ├── models.py                     # ALL dataclasses/Pydantic models (lingua franca)
│   │   ├── pipeline.py                   # Orchestrates analysis steps with error recovery
│   │   └── repo_manager.py              # Clone, update, cleanup, URL parsing
│   │
│   ├── analyzers/
│   │   ├── structure.py                  # File tree, depth, layout patterns
│   │   ├── language.py                   # linguist-py + pygments + cloc/tokei
│   │   ├── documentation.py             # README quality, license, changelog
│   │   ├── build.py                      # Build system detection + safe build attempt
│   │   ├── code_quality.py              # flake8, radon, bandit (Python); heuristics (others)
│   │   ├── testing.py                    # Test file discovery, framework detection, ratio
│   │   ├── architecture.py              # Pattern detection + Claude narrative
│   │   └── originality.py               # GitHub search + Claude plagiarism assessment
│   │
│   ├── scoring/
│   │   ├── rubric.py                     # Dimension definitions and weights
│   │   └── scorer.py                     # Aggregates → 1.0-10.0 score
│   │
│   ├── reporting/
│   │   ├── per_repo_report.py           # SnakeMD per-repo Markdown report
│   │   ├── summary_report.py            # SnakeMD cross-repo summary report
│   │   └── terminal.py                  # Rich console output helpers
│   │
│   ├── integrations/
│   │   ├── github_api.py                # GitHubClient: rate-limited, disk-cached
│   │   └── claude_api.py               # ClaudeClient: thin Anthropic SDK wrapper
│   │
│   └── utils/
│       ├── subprocess_runner.py         # run_with_timeout(), tool_available()
│       ├── cache.py                      # DiskCache with TTL (SHA-256 keys)
│       └── file_utils.py               # Path helpers, safe reads, size checks
│
└── tests/
    ├── conftest.py
    ├── test_cli.py
    ├── test_repo_manager.py
    ├── test_scoring.py
    ├── test_analyzers/
    │   ├── test_structure.py
    │   ├── test_language.py
    │   ├── test_build.py
    │   ├── test_code_quality.py
    │   └── test_originality.py
    └── fixtures/sample_repos/
        ├── python-clean/                 # Minimal clean Python project (test fixture)
        └── js-no-tests/                  # Minimal JS project without tests (test fixture)
```

---

## Analysis Pipeline (per repo)

`pipeline.run_pipeline()` executes these steps in order. Each step is wrapped in `try/except` — failures are recorded in `result.errors` and do not abort subsequent steps.

| Step | Module | Output Model |
|------|--------|-------------|
| 0. Pre-flight | repo_manager | Validate URL, check size via GitHub API |
| 1. Clone / Update | repo_manager | `RepoMeta` |
| 2. Structure | analyzers/structure | `StructureResult` |
| 3. Language detection | analyzers/language | `LanguageResult` |
| 4. Documentation | analyzers/documentation | `DocumentationResult` |
| 5. Build detection + attempt | analyzers/build | `BuildResult` |
| 6. Code quality | analyzers/code_quality | `CodeQualityResult` |
| 7. Test analysis | analyzers/testing | `TestingResult` |
| 8. Architecture | analyzers/architecture | `ArchitectureResult` |
| 9. Originality check | analyzers/originality | `OriginalityResult` |
| 10. Scoring | scoring/scorer | `List[DimensionScore]` + total |
| 11. Per-repo report | reporting/per_repo_report | `.md` file written to disk |

After all repos are processed, the CLI calls `summary_report.generate()` → `summary-TIMESTAMP.md`

---

## Scoring Rubric (1.0 – 10.0)

| Dimension | Weight | Key Signals |
|-----------|--------|-------------|
| Code Quality | 20% | flake8 issues, cyclomatic complexity (radon CC), bandit security issues |
| Architecture | 20% | Pattern detected (MVC/layered), no god files (>500 LOC), CI config present |
| Testing | 15% | Test file count, test/code LOC ratio, test framework detected, CI test step |
| Build Success | 15% | Build system detected, dry-run build succeeded within timeout |
| Originality | 15% | GitHub code search matches + Claude verdict (inverted: lower match = higher score) |
| Documentation | 10% | README quality, license file, changelog, docs directory |
| Structure | 5% | Layout cleanliness, directory depth, naming consistency |

**Formula**: `final_score = round(1.0 + (weighted_sum_0_to_1 × 9.0), 1)`

### Per-Dimension Scoring (0.0 – 1.0)

**Documentation:**
- README exists: +0.30 | word count >200: +0.10
- Has Installation section: +0.10 | Has Usage section: +0.10
- Has license file: +0.15 | Has badges: +0.05
- Has docs/ dir: +0.10 | Has changelog: +0.05 | Has API docs: +0.05

**Code Quality (Python):** composite of:
- Flake8 issues: 0=1.0, 1-10=0.8, 11-50=0.5, 51-100=0.3, >100=0.1
- Cyclomatic complexity avg: ≤5=1.0, 5-10=0.7, 10-15=0.4, >15=0.2
- Maintainability index avg: ≥80=1.0, 60-79=0.7, 40-59=0.4, <40=0.2
- Bandit high severity: 0=1.0, 1-2=0.5, ≥3=0.1

**Testing:**
- Has test files: +0.30 | Count ≥10: +0.20
- Test/code ratio ≥0.20: +0.25 | Framework detected: +0.15 | CI test step: +0.10

**Build:**
- No build system: 0.3 (neutral) | System found, not attempted: 0.5
- Build failed: 0.3 | Build timed out: 0.2 | Build succeeded: 1.0

**Architecture:**
- Pattern detected: +0.30 | No god files: +0.20
- Separate src/tests: +0.15 | CI/CD config: +0.15 | Docker: +0.10 | ≥2 packages: +0.10

**Originality (inverted):**
- 0 matches: 1.0 | 1-2 weak matches: 0.8 | 3+ matches, low Claude risk: 0.6
- Medium Claude risk: 0.3 | High Claude risk: 0.1

---

## Plagiarism Detection (Two-Layer)

1. **GitHub `/search/code`**: Extract 5 signature snippets (≥10-line functions from largest non-test files, whitespace-normalized). Search GitHub for 6-8 unique tokens per snippet. Results disk-cached (TTL 24h), rate-limited via token bucket (30 req/min).

2. **Claude assessment**: Send snippets + matched URLs to Claude. Returns verdict: `low | medium | high` risk with rationale text.

---

## CLI Interface

```bash
# Analyze one repo
hackanalyze analyze https://github.com/owner/repo

# Analyze multiple repos (generates per-repo reports + summary)
hackanalyze analyze https://github.com/a/b https://github.com/c/d

# Batch from a newline-separated file of URLs
hackanalyze batch repos.txt

# Clean up cloned repos
hackanalyze clean

# Options
--output-dir PATH      # Default: ./reports
--timeout INT          # Build timeout seconds (default: 120)
--skip-build           # Skip build attempts
--skip-plagiarism      # Skip originality check
--github-token TEXT    # Override GITHUB_TOKEN env var
--claude-api-key TEXT  # Override ANTHROPIC_API_KEY env var
```

---

## Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| `shell=False` always in subprocess | Repos are untrusted input; list-form args prevent injection |
| Dry-run build commands only | Safe — `pip install --dry-run`, `npm install --dry-run` don't execute repo code |
| Claude is optional | Works without `ANTHROPIC_API_KEY`; graceful degradation to heuristics |
| Pydantic v2 models as data contracts | Type-safe, JSON-serializable, self-documenting between modules |
| SnakeMD for Markdown generation | Prevents malformed tables when repo names contain `\|` or `#` |
| Disk cache for GitHub search | 30 req/min limit — cache makes re-runs instant and preserves quota |
| Max repo size guard (500MB) | Checked via GitHub API before cloning — safety against huge repos |

---

## Dependencies

```toml
[project.dependencies]
typer[all]>=0.12          # CLI framework with Rich integration
gitpython>=3.1            # Git operations (clone, pull)
requests>=2.31            # GitHub REST API
anthropic>=0.28           # Claude API client
pygments>=2.17            # Language detection fallback
snakemd>=2.2              # Programmatic Markdown generation
rich>=13.7                # Terminal output, progress bars, tables
python-dotenv>=1.0        # .env file loading
pydantic>=2.6             # Data models
pydantic-settings>=2.2    # Settings from env vars

[project.optional-dependencies]
quality = [flake8, radon, bandit]   # Code quality analysis tools
dev = [pytest, pytest-cov, mypy, black, isort]
```

---

## Deliverable Documents

| File | Purpose |
|------|---------|
| `VISION.md` | Problem statement, goals, target users, SDLC fit, guiding principles, success metrics, future directions |
| `IMPLEMENTATION_PLAN_PROPOSAL.md` | Three architectural approaches with trade-offs (Approach A: monolith → B: modular CLI → C: full framework) |
| `README.md` | User-facing quickstart, install, examples |
| `CLAUDE.md` | AI-assisted development instructions (build/test commands, project notes) |

---

## Implementation Order

| Phase | Files | Notes |
|-------|-------|-------|
| 1. Scaffold | `pyproject.toml`, `.env.example`, `.gitignore`, `config.py`, `core/models.py` | Models first — all other modules import from here |
| 2. Utils | `utils/subprocess_runner.py`, `utils/cache.py`, `utils/file_utils.py` | Pure stdlib, no external deps |
| 3. Repo management | `core/repo_manager.py` | GitPython + subprocess fallback |
| 4. Integrations | `integrations/github_api.py`, `integrations/claude_api.py` | Rate limiting, caching, API clients |
| 5. Analyzers | All 8 analyzer modules + tests | structure → language → docs → build → quality → testing → architecture → originality |
| 6. Scoring | `scoring/rubric.py`, `scoring/scorer.py` | Pure functions, easy to unit test |
| 7. Reporting | `reporting/terminal.py`, `per_repo_report.py`, `summary_report.py` | SnakeMD + Rich |
| 8. Pipeline + CLI | `core/pipeline.py`, `cli.py` | Wire everything together |
| 9. Documents | `VISION.md`, `IMPLEMENTATION_PLAN_PROPOSAL.md`, `README.md`, `CLAUDE.md` | Final deliverables |
| 10. Tests + verify | Test fixtures, end-to-end verification | Confirm `pytest` passes, CLI runs |

---

## Verification Checklist

- [ ] `pip install -e ".[dev,quality]"` — installs cleanly
- [ ] `pytest tests/ -v` — all unit tests pass (no network calls, uses fixture repos)
- [ ] `hackanalyze analyze https://github.com/tiangolo/fastapi --skip-plagiarism` — end-to-end run
- [ ] `reports/per-repo/tiangolo-fastapi-report.md` generated with valid Markdown
- [ ] `hackanalyze batch` with 3 URLs → `reports/summary/summary-*.md` generated
- [ ] With `GITHUB_TOKEN`: plagiarism check runs, cache created in `cache/github_search/`
- [ ] With `ANTHROPIC_API_KEY`: architecture narrative and plagiarism verdict appear in report
- [ ] `hackanalyze analyze <url> --skip-build --skip-plagiarism` completes in <5 min on standard laptop

---

*Generated by Claude Sonnet 4.6 | Hackathon Analyzer v0.1.0*
