# Implementation Plan: New Analysis Dimensions

> **Status**: In Progress | **Date**: 2026-03-07 | **Version**: 1.0

---

## Overview

Adding 5 new scoring dimensions to the hackathon analyzer to capture innovation, ambition, trustworthiness, and real-world viability beyond structural code quality.

| # | Dimension | Score | Claude Required | Key Signal |
|---|-----------|:-----:|:---------------:|------------|
| 1 | Promise–Reality Gap | 9.5 | Yes | Does the implementation match the README claims? |
| 2 | Vision Ambition Score | 9.0 | Yes | Problem clarity, novelty, scope ambition |
| 3 | Tech Stack Novelty | 8.5 | No | Modern vs legacy dependencies |
| 4 | Hackathon Freshness | 8.5 | No | Repo age, commit history, pre-existing code flags |
| 5 | AI/LLM Integration Depth | 8.0 | No | Sophistication of AI usage patterns |

---

## Weight Rebalancing

Current weights (7 dimensions, sum = 1.0) → New weights (12 dimensions, sum = 1.0).

| Dimension | Old Weight | New Weight | Change |
|-----------|:---------:|:----------:|:------:|
| Code Quality | 20% | 12% | -8% |
| Architecture | 20% | 12% | -8% |
| Testing | 15% | 10% | -5% |
| Build Success | 15% | 8% | -7% |
| Originality | 15% | 10% | -5% |
| Documentation | 10% | 8% | -2% |
| Structure | 5% | 3% | -2% |
| **Promise–Reality Gap** | — | **12%** | new |
| **Vision Ambition** | — | **8%** | new |
| **Tech Stack Novelty** | — | **6%** | new |
| **Hackathon Freshness** | — | **6%** | new |
| **AI/LLM Integration** | — | **5%** | new |
| **TOTAL** | **100%** | **100%** | |

**Rationale**: Promise–Reality Gap (12%) gets the highest new weight because it's the #1 thing judges manually check. Original core dimensions retain majority weight (63%) to preserve existing scoring stability.

---

## New Data Models (`core/models.py`)

### PromiseRealityResult
```python
@dataclass
class PromiseRealityResult:
    readme_summary: str = ""           # Extracted README claims
    codebase_summary: str = ""         # Actual implementation summary
    alignment_score: float = 0.0       # 0.0–1.0 (1.0 = perfect match)
    claude_assessment: str = ""        # Claude's detailed assessment
    key_claims: list = field(...)      # Claims found in README
    claims_supported: int = 0          # How many claims have code evidence
    claims_unsupported: int = 0        # How many claims lack code evidence
```

### VisionAmbitionResult
```python
@dataclass
class VisionAmbitionResult:
    problem_clarity: float = 0.0       # 0.0–1.0
    solution_novelty: float = 0.0      # 0.0–1.0
    scope_ambition: float = 0.0        # 0.0–1.0
    audience_specificity: float = 0.0  # 0.0–1.0
    vision_score: float = 0.0          # Weighted composite
    vision_rationale: str = ""         # Claude's rationale
```

### TechStackNoveltyResult
```python
@dataclass
class TechStackNoveltyResult:
    dependencies_found: dict = field(...)  # package → category
    novelty_score: float = 0.0             # 0.0–1.0
    bleeding_edge_count: int = 0
    modern_count: int = 0
    established_count: int = 0
    legacy_count: int = 0
    cross_domain_bonus: bool = False
    notable_deps: list = field(...)        # Interesting dependencies
```

### HackathonFreshnessResult
```python
@dataclass
class HackathonFreshnessResult:
    repo_created_at: str = ""              # ISO date from GitHub API
    first_commit_date: str = ""            # From git log
    last_commit_date: str = ""             # From git log
    total_commits: int = 0
    commit_span_days: int = 0
    freshness_score: float = 0.0           # 0.0–1.0
    freshness_flag: str = "unknown"        # "fresh" | "old" | "unknown"
    flag_reason: str = ""
```

### AIIntegrationResult
```python
@dataclass
class AIIntegrationResult:
    ai_libraries_detected: list = field(...)         # e.g. ["openai", "langchain"]
    ai_patterns_detected: list = field(...)          # e.g. ["RAG", "tool_calling"]
    integration_depth: str = "none"                  # none/basic/intermediate/advanced/expert
    depth_score: float = 0.0                         # 0.0–1.0
    evidence: list = field(...)                      # File:line evidence
```

---

## New Analyzer Modules

### 1. `analyzers/promise_reality.py`

**Dependencies**: Claude API (required for meaningful results), README text, codebase structure

**Algorithm**:
1. Extract README text (first 3000 words) — parse claims/goals
2. Build codebase summary: top-level modules, key function signatures, file structure
3. Send both to Claude with structured prompt asking for alignment assessment
4. Parse Claude's response for `alignment_score` (0–1) and per-claim verdicts
5. Fallback without Claude: compare README keywords against filenames/function names (heuristic)

**Claude Prompt**: "Given this README and codebase summary, assess whether the implementation matches the stated goals. For each claim in the README, state whether code evidence supports it. Return alignment_score (0.0–1.0) and rationale."

### 2. `analyzers/vision_ambition.py`

**Dependencies**: Claude API (required), README text only

**Algorithm**:
1. Extract README text (first 2000 words)
2. Send to Claude with structured sub-dimension rubric
3. Parse scores for: problem_clarity, solution_novelty, scope_ambition, audience_specificity
4. Compute weighted composite: clarity(30%) + novelty(30%) + ambition(25%) + audience(15%)
5. Fallback without Claude: keyword-based heuristic (mentions of "problem", "solve", "user", "novel")

### 3. `analyzers/tech_stack_novelty.py`

**Dependencies**: None (pure file analysis)

**Algorithm**:
1. Parse dependency files: `requirements.txt`, `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `*.csproj`/`Directory.Packages.props`
2. Map each dependency to a novelty tier using a curated dictionary:
   - **Bleeding edge** (1.0): `crewai`, `autogen`, `ollama`, latest LLM SDKs, `bun`, `deno`
   - **Modern** (0.7): `fastapi`, `next`, `svelte`, `axum`, `anthropic`, `openai`
   - **Established** (0.4): `flask`, `express`, `spring`, `django`, `react`
   - **Legacy** (0.1): `jquery`, old PHP libs, python2-era packages
3. Score = weighted average of tier scores, with bonus for cross-domain
4. Unknown deps default to "established" (0.4) — conservative

### 4. `analyzers/hackathon_freshness.py`

**Dependencies**: Git history (local), optionally GitHub API

**Algorithm**:
1. Run `git log --format="%H %aI" --reverse` to get first and last commit dates
2. Count total commits via `git rev-list --count HEAD`
3. Calculate commit span in days
4. Score:
   - Created within 3 days: 1.0 (clearly hackathon-fresh)
   - Created within 7 days: 0.8
   - Created within 30 days: 0.5
   - Older than 30 days: 0.2 (flag as potentially pre-existing)
   - Unknown: 0.5 (neutral)
5. Optional: if `hackathon_start_date` configured, check if first commit is after that date

### 5. `analyzers/ai_integration.py`

**Dependencies**: None (pure file/import analysis)

**Algorithm**:
1. Scan all source files for AI/ML library imports and patterns
2. Categorize detected patterns by sophistication tier:
   - **Basic** (0.3): Raw API call (`openai.ChatCompletion`, `anthropic.messages`)
   - **Intermediate** (0.5): Structured prompting, system messages, function calling
   - **Advanced** (0.7): RAG (vector DB + retrieval), embeddings, tool use
   - **Expert** (0.9): Multi-agent orchestration, fine-tuning, custom training
3. Score = highest tier detected
4. Boost if multiple AI libraries used together (+0.1)

**Detection patterns** (imports and code patterns):
- Libraries: `openai`, `anthropic`, `langchain`, `llamaindex`, `chromadb`, `pinecone`, `weaviate`, `crewai`, `autogen`, `semantic_kernel`, `ollama`, `transformers`, `huggingface_hub`
- Patterns: `tool_choice`, `function_call`, `system.*message`, `embed`, `vector`, `retriev`, `agent`, `chain`, `prompt_template`

---

## Scoring Functions (`scoring/scorer.py`)

### `_score_promise_reality(r)`
- No result: 0.5 (neutral)
- Use `alignment_score` directly (already 0–1)
- Without Claude: heuristic based on keyword overlap

### `_score_vision_ambition(r)`
- No result: 0.5
- Use `vision_score` directly

### `_score_tech_stack_novelty(r)`
- No result: 0.4 (neutral)
- Use `novelty_score` directly

### `_score_hackathon_freshness(r)`
- No result: 0.5 (neutral)
- Use `freshness_score` directly

### `_score_ai_integration(r)`
- No result: 0.3 (neutral — no AI doesn't mean bad)
- Use `depth_score` directly

---

## Pipeline Integration (`core/pipeline.py`)

New steps added after existing Step 9 (Originality):

| Step | Module | Runs After | Needs Claude |
|------|--------|-----------|:------------:|
| 10. Promise–Reality | analyzers/promise_reality | Documentation + Structure | Yes |
| 11. Vision Ambition | analyzers/vision_ambition | Documentation | Yes |
| 12. Tech Stack Novelty | analyzers/tech_stack_novelty | Language detection | No |
| 13. Hackathon Freshness | analyzers/hackathon_freshness | Clone | No |
| 14. AI Integration | analyzers/ai_integration | Language detection | No |
| 15. Scoring | scoring/scorer | All analyzers | No |

---

## Report Updates

### Per-Repo Report (`reporting/per_repo_report.py`)
New sections added between Architecture and Scorecard:
- **Promise vs Reality** — alignment score, per-claim breakdown, Claude assessment
- **Vision & Ambition** — sub-dimension scores, rationale
- **Tech Stack** — dependency novelty breakdown, notable deps
- **Hackathon Freshness** — repo age, freshness flag, commit timeline
- **AI Integration** — detected libraries, patterns, depth tier

### Summary Report (`reporting/summary_report.py`)
- New dimension columns automatically appear in leaderboard (via existing dimension loop)
- New dimension rows in dimension comparison table

---

## Config Changes (`config.py`)

```python
hackathon_start_date: str = ""  # ISO date e.g. "2026-03-01" — optional
```

---

## Files Modified

| File | Change |
|------|--------|
| `core/models.py` | +5 new dataclasses, update `RepoAnalysisResult` |
| `config.py` | +1 config field (`hackathon_start_date`) |
| `integrations/claude_api.py` | +2 methods (`assess_promise_reality`, `assess_vision`) |
| `analyzers/promise_reality.py` | **NEW** |
| `analyzers/vision_ambition.py` | **NEW** |
| `analyzers/tech_stack_novelty.py` | **NEW** |
| `analyzers/hackathon_freshness.py` | **NEW** |
| `analyzers/ai_integration.py` | **NEW** |
| `scoring/rubric.py` | +5 dimensions, rebalanced weights |
| `scoring/scorer.py` | +5 scorer functions |
| `core/pipeline.py` | +5 pipeline steps |
| `reporting/per_repo_report.py` | +5 report sections |
| `reporting/summary_report.py` | Auto-handles new dimensions (no change needed) |

---

## Graceful Degradation

| Scenario | Behavior |
|----------|----------|
| No `ANTHROPIC_API_KEY` | Promise–Reality → keyword heuristic; Vision → keyword heuristic; all others unaffected |
| No `GITHUB_TOKEN` | Freshness relies on git log only (no GitHub API created_at) |
| No git history (shallow clone) | Freshness → "unknown" flag, score 0.5 |
| No dependency files found | Tech Stack → score 0.4 (neutral) |
| No AI detected | AI Integration → score 0.0, flagged "none" (not penalized via low weight) |

---

*Plan authored 2026-03-07 | hackathon-analyzer v0.2.0*
