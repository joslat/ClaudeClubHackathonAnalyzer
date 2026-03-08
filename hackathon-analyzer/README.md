# Hackathon Repository Analyzer

Analyze hackathon submissions for technical quality and originality. Generates Markdown reports with 1-10 scores across 12 dimensions including code quality, architecture, promise vs reality, testing, originality, documentation, and more.

## Quick Start

```bash
# Install
pip install -e ".[dev,quality]"

# Analyze one repo (no API keys needed)
hackanalyze analyze https://github.com/owner/repo --skip-plagiarism

# Analyze multiple repos (generates per-repo reports + summary)
hackanalyze analyze https://github.com/a/b https://github.com/c/d

# Batch from a file (one URL per line)
hackanalyze batch repos.txt

# With full analysis (GitHub + Claude)
GITHUB_TOKEN=ghp_... ANTHROPIC_API_KEY=sk-ant-... hackanalyze analyze https://github.com/owner/repo
```

## Setup

```bash
cp .env.example .env
# Edit .env: add GITHUB_TOKEN and ANTHROPIC_API_KEY (both optional)
pip install -e ".[dev,quality]"
```

### Optional tools (enhance analysis)

```bash
pip install flake8 radon bandit   # Python code quality (auto-detected if installed)
# cloc or tokei for accurate LOC counts (auto-detected if on PATH)
```

## CLI Reference

```
hackanalyze analyze <REPO_URLS>...
  --output-dir PATH      Report output directory (default: ./reports)
  --timeout INT          Build timeout in seconds (default: 120)
  --skip-build           Skip build attempts
  --skip-plagiarism      Skip GitHub code search + AI originality check
  --github-token TEXT    GitHub PAT (or set GITHUB_TOKEN env var)
  --claude-api-key TEXT  Anthropic API key (or set ANTHROPIC_API_KEY env var)
  --repos-dir PATH       Where repos are cloned (default: ./repos)

hackanalyze batch <FILE>
  Same options as analyze; reads URLs from file (one per line, # = comment)

hackanalyze clean [--repos-dir PATH] [--yes]
  Delete all cloned repos
```

## Output

```
reports/
  per-repo/
    owner-reponame-report.md     # Full analysis with score breakdown
  summary/
    summary-20260307-142315.md  # Leaderboard + cross-repo statistics
```

## Scoring Rubric

| Dimension | Weight | What's measured |
|-----------|-------:|-----------------|
| Code Quality | 12% | Flake8, cyclomatic complexity (radon), bandit security |
| Architecture | 12% | Pattern detected, god files, CI/CD, Docker |
| Promise vs Reality | 12% | Does the implementation match what the README claims? |
| Testing | 10% | Test files, ratio, frameworks, CI test step |
| Originality | 10% | GitHub code search + Claude AI verdict |
| Vision & Ambition | 8% | Problem clarity, solution novelty, scope ambition |
| Documentation | 8% | README quality, license, changelog, docs |
| Build Success | 8% | Build system detected + dry-run succeeded |
| Tech Stack Novelty | 6% | Modern vs legacy dependency choices |
| Hackathon Freshness | 6% | Was the repo created during the hackathon window? |
| AI Integration | 5% | Depth and sophistication of AI/LLM usage |
| Structure | 3% | Layout, depth, file naming |

**Final score**: `1.0 + (weighted_sum × 9.0)` → range 1.0-10.0

## Project Documents

- [PLAN.md](docs/PLAN.md) — Implementation plan
- [VISION.md](docs/VISION.md) — Project vision and SDLC context
- [IMPLEMENTATION_PLAN_PROPOSAL.md](docs/IMPLEMENTATION_PLAN_PROPOSAL.md) — Three architectural approaches

## Development

```bash
pytest tests/ -v          # Run tests
pip install -e ".[dev]"   # Install dev tools
```

## Security Notes

- All subprocess calls use `shell=False` — repo content cannot inject commands
- Build attempts use dry-run commands (`pip install --dry-run`, `npm install --dry-run`)
- Repos above `MAX_REPO_SIZE_MB` (default 500MB) are skipped before cloning
- No repo code is sent to external services (only 6-8 token search queries to GitHub)
