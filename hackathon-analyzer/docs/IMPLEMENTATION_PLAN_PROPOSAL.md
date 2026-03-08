# Implementation Plan Proposal: Hackathon Repository Analyzer

**Version**: 1.0
**Date**: 2026-03-07
**Author**: Claude Sonnet 4.6

> *This document thinks out loud about three different ways to build the Hackathon Repository Analyzer — from the simplest possible approach to a full production-grade framework. It is intentionally exploratory.*

---

## The Problem We're Solving (Quick Recap)

We need a tool that:
1. Accepts a GitHub/GitLab repo URL
2. Clones the repo locally
3. Analyzes it across multiple dimensions (code quality, testing, architecture, originality, etc.)
4. Produces a Markdown report with a 1-10 score
5. Produces a summary across all analyzed repos
6. Detects plagiarism using GitHub code search + AI

Three approaches, three very different engineering tradeoffs.

---

## Approach A: The Simple Script

*"Get something working today. Figure out structure tomorrow."*

### Philosophy

One file. Maybe two. No abstractions, no packages, no tests. Just Python talking directly to APIs and writing text files. The fastest path from zero to a working demo.

### What it looks like

```
hackathon-analyzer/
  analyze.py          # ~600 lines, does everything
  report_template.md  # Jinja2 template for output
  requirements.txt    # Just requests, gitpython, jinja2
```

`analyze.py` would look roughly like:

```python
# Single entry point: python analyze.py https://github.com/owner/repo
import subprocess, os, json, sys, requests
from pathlib import Path

REPO_URL = sys.argv[1]
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

def clone_repo(url):
    slug = url.split("github.com/")[1].replace("/", "-")
    subprocess.run(["git", "clone", "--depth", "1", url, f"repos/{slug}"])
    return Path(f"repos/{slug}"), slug

def detect_language(repo_path):
    # Count file extensions, return most common
    ...

def check_readme(repo_path):
    readme = repo_path / "README.md"
    return {"exists": readme.exists(), "words": len(readme.read_text().split()) if readme.exists() else 0}

def run_flake8(repo_path):
    result = subprocess.run(["flake8", ".", "--count", "--exit-zero"], cwd=repo_path, capture_output=True, text=True)
    return int(result.stdout.strip().split("\n")[-1] or 0)

def search_github(snippet, token):
    # ... requests call, no caching, will hit rate limits
    ...

def score_everything(checks):
    # big dict → weighted average → 1-10
    ...

def write_report(slug, checks, score):
    with open(f"reports/{slug}.md", "w") as f:
        f.write(f"# {slug}\nScore: {score}/10\n...")

repo_path, slug = clone_repo(REPO_URL)
readme = check_readme(repo_path)
lang = detect_language(repo_path)
linter = run_flake8(repo_path)
# ... etc
score = score_everything({...})
write_report(slug, ..., score)
```

### Pros

- **Working in 4 hours** — literally the next afternoon after reading the requirements
- **Zero architectural decisions** — no packages, no interfaces, just code
- **Easy to demo** — `python analyze.py https://github.com/anything` and it works
- **Low cognitive load** — one file to read, one file to debug

### Cons

- **Rate limits will break it** — no caching on GitHub search calls; 30 req/min limit means 6+ repos in a batch will fail silently
- **No error isolation** — if flake8 isn't installed, the whole script crashes; there's no graceful degradation
- **Untestable** — everything is in one function chain; mocking git or APIs requires monkey-patching
- **Not extensible** — adding a new language analyzer means editing the monolith; adding batch processing means copy-pasting the main flow
- **Security risk** — easy to accidentally use `shell=True` when building subprocess calls inline
- **Report formatting is fragile** — f-strings with `|` in repo names will break Markdown tables

### When to choose Approach A

Use this when:
- You need to validate the concept *today* before committing to architecture
- You're the only person who will ever run this
- The hackathon has < 20 submissions and you can manually check edge cases
- You plan to throw this away once requirements are clearer

**Approach A is the spike before Approach B.**

---

## Approach B: The Modular CLI (Recommended — Currently Implemented)

*"Separate concerns from day one. Each piece is testable and replaceable."*

### Philosophy

The core insight of Approach B is that analysis, scoring, and reporting are fundamentally different concerns. A `structure.py` module should know nothing about how its output ends up in a Markdown file. A `scorer.py` should know nothing about GitHub. The pipeline just wires them together.

This is what we've built. The full implementation is in this repository.

### What makes it work

**Typed data models as contracts** (`core/models.py`):
Every analyzer returns a specific dataclass (`StructureResult`, `LanguageResult`, etc.). If you add a field to `TestingResult`, your IDE immediately shows you everywhere that field needs to be handled. No silent dict key errors at report generation time.

**Independent analyzers** (`analyzers/`):
Each analyzer is a pure function: `analyze_X(repo_path: Path, ...) -> XResult`. They can be developed, tested, and replaced independently. Adding a new analyzer (say, `security_scan.py`) means creating one file and adding one step to `pipeline.py`.

**Error isolation** (`core/pipeline.py`):
```python
for step in analysis_steps:
    try:
        step(result)
    except Exception as e:
        result.errors.append(str(e))
        # continue — other steps still run
```
If `bandit` crashes on a weird Go project, the other 7 analyzers still complete. The report notes the error but isn't aborted.

**Disk-based caching** (`utils/cache.py`):
GitHub search API calls are cached with SHA-256 keys and a 24-hour TTL. Re-running analysis on the same repo doesn't burn rate limit quota. Cache entries are stored as plain JSON files — easy to inspect, easy to clear.

**Rate-limited API clients** (`integrations/github_api.py`):
A token bucket implementation ensures we never exceed 30 req/min. The client checks `X-RateLimit-Remaining` headers and sleeps until reset if approaching the limit. This is invisible to callers.

### Structure overview

```
hackathon_analyzer/
  cli.py              # Typer app — thin, just wires options to pipeline
  config.py           # Pydantic Settings — validated env vars
  core/
    models.py         # All data contracts (the lingua franca)
    pipeline.py       # Orchestrator with error recovery
    repo_manager.py   # Clone, parse URL, update, cleanup
  analyzers/          # 8 independent analysis functions
  scoring/            # Rubric weights + aggregation formula
  reporting/          # Markdown generation + Rich terminal output
  integrations/       # GitHub API client, Claude API client
  utils/              # subprocess, cache, file helpers
```

### Why the scoring formula is 1 + (sum × 9)

The weighted sum of dimension scores lands in 0.0-1.0. Mapping this linearly to 1-10 means:
- A repo that scores 0 on *everything* still gets a 1.0 (it exists — it cloned)
- A repo that scores 1.0 on *everything* gets a 10.0
- The 9-point spread between floor and ceiling creates meaningful differentiation

Alternative formulas considered:
- `score × 10`: Would give 0 for a completely empty repo — too harsh for repos that at least built
- `(score + 0.1) × 9.09`: More complex, same result as the current formula
- `1 + score × 9` (current): Clean, explainable, mirrors academic grading floors

### Pros

- **Each module independently testable** — unit tests for `scorer.py` use fake `RepoAnalysisResult` objects, no git involved
- **Safe subprocess handling** — `run_with_timeout()` centralizes all subprocess calls, guaranteeing `shell=False` and consistent timeout handling
- **Language-agnostic by design** — the pipeline doesn't know what language it's analyzing; analyzers gracefully skip steps that don't apply
- **Graceful degradation** — Claude key missing? Architecture narrative uses heuristics. GitHub token missing? Plagiarism check is skipped with a warning, not a crash.
- **Clean entry point** — `hackanalyze analyze <url>` works from the terminal; `hackanalyze batch repos.txt` handles bulk

### Cons

- **~30 files before first working demo** — more upfront investment than Approach A
- **Requires discipline** — easy to let business logic creep into `cli.py` or put API calls in analyzers directly
- **Sequential analysis** — each analyzer runs one at a time; a batch of 50 repos takes proportionally longer (Approach C solves this with async)

### When to choose Approach B

This is the right approach for:
- A team of 1-3 people building for real use
- A tool that will be maintained past the hackathon weekend
- Cases where correctness, testability, and extensibility matter
- Any situation where the set of analyzers will grow over time

**Approach B is what we built. Start here.**

---

## Approach C: The Full Framework

*"Build for scale, extensibility, and a future product."*

### Philosophy

What if this tool needed to analyze 500 repos simultaneously? What if you wanted to add a web UI where judges could browse reports? What if you wanted a plugin marketplace where community members could contribute language-specific analyzers?

Approach C answers these questions — at the cost of significant upfront complexity.

### What's different from Approach B

**Async pipeline with `asyncio`:**

```python
import asyncio

async def run_pipeline_async(meta: RepoMeta, config: Config) -> RepoAnalysisResult:
    structure_task = asyncio.create_task(analyze_structure_async(meta.local_path))
    language_task = asyncio.create_task(detect_languages_async(meta.local_path))
    doc_task = asyncio.create_task(analyze_documentation_async(meta.local_path))

    # All three run concurrently — structure, language, and docs don't depend on each other
    structure, language, docs = await asyncio.gather(structure_task, language_task, doc_task)

    # Build depends on language detection result
    build = await analyze_build_async(meta.local_path, language)
    ...

async def analyze_batch_async(urls: list[str]) -> list[RepoAnalysisResult]:
    tasks = [run_pipeline_async(parse_repo_url(url)) for url in urls]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

This is a genuine speedup for large batches: language detection, documentation analysis, and structure analysis are all I/O-bound and can run concurrently within a single repo's pipeline.

**Plugin system via Python entry points:**

```toml
# plugin-rust-analyzer/pyproject.toml
[project.entry-points."hackanalyzer.analyzers"]
rust_clippy = "plugin_rust.clippy:analyze_clippy"
```

```python
# hackathon_analyzer/core/plugin_loader.py
import importlib.metadata

def load_analyzers() -> dict[str, Callable]:
    analyzers = {}
    for ep in importlib.metadata.entry_points(group="hackanalyzer.analyzers"):
        analyzers[ep.name] = ep.load()
    return analyzers
```

Third-party contributors can publish `pip install hackanalyzer-rust` and have their Rust-specific analysis (Clippy scores, unsafe blocks counted) automatically incorporated.

**SQLite persistence via SQLAlchemy:**

```python
class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    id = Column(Integer, primary_key=True)
    repo_url = Column(String)
    score = Column(Float)
    analyzed_at = Column(DateTime)
    result_json = Column(JSON)  # Full RepoAnalysisResult serialized
```

This enables:
- Re-running analysis and comparing score changes over time
- Cross-hackathon comparison ("how does this year's cohort compare to last year's?")
- REST API queries like "show all repos with score > 7 and plagiarism_risk = 'low'"

**FastAPI REST layer:**

```python
from fastapi import FastAPI
app = FastAPI()

@app.post("/analyze")
async def analyze_endpoint(request: AnalyzeRequest) -> AnalysisRunResponse:
    result = await run_pipeline_async(parse_repo_url(request.url))
    save_to_db(result)
    return AnalysisRunResponse(score=result.total_score, report_url=f"/reports/{result.meta.slug}")

@app.get("/reports/{slug}")
async def get_report(slug: str) -> ReportResponse:
    ...
```

This makes the analyzer accessible as a web service. A simple React frontend can submit repo URLs and display formatted reports.

**Docker sandboxing for builds:**

Instead of `timeout`-only protection on build attempts, Approach C runs builds inside ephemeral Docker containers:

```python
async def attempt_build_sandboxed(repo_path: Path, build_system: str) -> BuildResult:
    cmd = ["docker", "run", "--rm", "--network=none",
           "--memory=512m", "--cpus=1",
           "-v", f"{repo_path}:/repo:ro",
           f"hackanalyzer-sandbox-{build_system}",
           "build.sh"]
    # Docker's isolation is stronger than subprocess timeout alone
    ...
```

This provides network isolation (malicious repos can't phone home during build), memory limits, and read-only repo mounting.

### Full Approach C Structure

```
hackathon-analyzer/
  src/
    hackathon_analyzer/
      api/                    # FastAPI routes
        routes/
          analyze.py
          reports.py
          health.py
        middleware.py
      core/                   # Same as Approach B
      analyzers/              # Same as Approach B
      plugins/                # Plugin loader
        loader.py
        registry.py
      db/                     # SQLAlchemy models + migrations
        models.py
        migrations/           # Alembic
      worker/                 # Async task queue (optional: Celery/Redis)
        tasks.py
      ...
  docker/
    sandbox-python/           # Build sandbox images
    sandbox-node/
    sandbox-rust/
  tests/
    ...
  alembic.ini
  docker-compose.yml          # Redis + SQLite + app
```

### Pros

- **Handles 100+ concurrent repos** — async pipeline + worker queue
- **Full audit trail** — every analysis run stored, queryable, comparable
- **Web UI ready** — FastAPI wraps existing core; no rewrite needed
- **Plugin ecosystem** — community can extend without forking
- **Stronger sandboxing** — Docker isolation for build attempts

### Cons

- **3-5x more code** before first working demo
- **Async debugging is hard** — `asyncio` stack traces are cryptic; race conditions are subtle
- **Heavy dependency stack** — FastAPI, SQLAlchemy, Alembic, Redis, Docker... each is a failure point
- **Premature for a CLI tool** — if the use case is "10-50 repos per hackathon, run by one person", this is overkill
- **Docker requirement** — not all judges will have Docker installed

### When to choose Approach C

Choose Approach C when:
- This is being built as a SaaS product with multiple simultaneous users
- Hackathons consistently have > 200 submissions
- A web dashboard for judges is a hard requirement
- You have budget for a 2-3 person engineering team to build it properly

**Don't start with Approach C.** Start with B, which is already structured to migrate toward C incrementally:
- `asyncio` can be layered onto the existing pipeline functions
- FastAPI can wrap the existing `Config` + `pipeline.run_pipeline()` without changes
- SQLAlchemy can persist `RepoAnalysisResult` via its `model_dump()` JSON method

---

## Comparison Matrix

| Criterion | A: Script | B: Modular CLI | C: Full Framework |
|-----------|:---------:|:--------------:|:-----------------:|
| Time to first working demo | 4 hours | 3-5 days | 2-3 weeks |
| Testability | Very low | High | Very high |
| Extensibility | None | Moderate | Very high |
| Error resilience | None | Good | Excellent |
| Rate limit safety | None | Good | Excellent |
| Multi-user support | No | No (single user) | Yes |
| Web UI | No | No | Yes |
| Plugin ecosystem | No | No | Yes |
| Async/concurrent | No | No | Yes |
| Appropriate for 10-50 repos | Yes | Yes | Over-engineered |
| Appropriate for 200+ repos | No | Maybe | Yes |
| Appropriate for SaaS | No | No | Yes |

---

## Recommended Migration Path

```
Approach A (prototype, 1 day)
    ↓ validate GitHub search actually returns useful results
    ↓ validate Claude verdict text is useful for judges

Approach B (modular CLI, current — 3-5 days)
    ↓ validate with real hackathon judges
    ↓ collect feedback on report format and scoring weights

Approach B.5 (async pipeline added to B, 2-3 days)
    ↓ enables concurrent analysis within one repo
    ↓ needed when batch size > 20 repos

Approach C (full framework, 2-3 weeks)
    ↓ only if web UI or SaaS is a confirmed requirement
```

The critical insight: **Approach B is designed to survive Approach C.** The modular structure, typed models, and clean interfaces mean that async, persistence, and a web layer can all be added incrementally — without rewriting the analysis or scoring logic.

---

## Technical Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| GitHub rate limits block plagiarism check | High | Medium | Disk cache (24h TTL), token bucket rate limiter, `--skip-plagiarism` flag |
| Malicious repo hangs build step | Medium | High | `BUILD_TIMEOUT_SECONDS`, dry-run commands, `shell=False` |
| Repo too large to clone (500MB+) | Low | High | GitHub API size check before clone, `MAX_REPO_SIZE_MB` guard |
| Claude API unavailable | Low | Low | All Claude calls are optional; heuristic fallbacks always exist |
| Language detection wrong | Medium | Low | Affects one score dimension; other 6 dimensions still scored correctly |
| cloc/radon/bandit not installed | High | Low | `tool_available()` check before every call; graceful skip |

---

*Implementation Plan Proposal v1.0 — Hackathon Repository Analyzer*
