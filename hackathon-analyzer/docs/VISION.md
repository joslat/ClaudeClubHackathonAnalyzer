# Vision Document: Hackathon Repository Analyzer

**Version**: 1.0
**Date**: 2026-03-07
**Status**: Draft
**Author**: Claude Sonnet 4.6 (AI-assisted design)

---

## 1. Purpose and Problem Statement

Every hackathon ends the same way: judges face a stack of repositories to evaluate, a short window of time, and no consistent methodology. The result is reviews that are inevitably biased — toward familiar tech stacks, toward projects with impressive demos, toward teams whose README is long enough to read. Technical quality, code originality, and architectural thinking are chronically under-rewarded because they take time to assess.

**The core problem has three dimensions:**

1. **Scale** — A 200-team hackathon with 5 judges means each judge reviews 40 projects. At 30 minutes each, that's 20 hours. Human attention degrades. Consistency suffers.

2. **Inconsistency** — Without a rubric, two judges scoring the same repo often diverge by 2-3 points. Subjective impressions dominate over evidence.

3. **Originality risk** — Hackathon fraud is real. Copied code from previous competitions or open-source repos is hard to detect without tooling. Judges rarely have time to cross-check.

**This tool's mission**: Provide automated, evidence-based technical analysis of any repository in minutes — generating judge-ready reports that surface objective metrics, flag plagiarism risks, and free human judges to focus on what they do best: evaluating innovation and impact.

---

## 2. Goals and Non-Goals

### Goals

- **Objective first-pass scoring** across 7 technical dimensions (code quality, architecture, testing, build success, originality, documentation, structure)
- **Multi-language support** — Python, JavaScript/TypeScript, Java, Go, Rust, Ruby, and more — without favoring any particular stack
- **Plagiarism detection** combining GitHub code search and AI-powered conceptual similarity assessment
- **Judge-ready Markdown reports** — per-repository and cross-repository summary — generated automatically
- **Safe execution** — build attempts use dry-run commands and strict timeouts; no arbitrary code is executed from submitted repos
- **Graceful degradation** — the tool works without API keys; each optional component (GitHub token, Anthropic key) enhances results but is not required

### Non-Goals

- **Replacing human judgment** — the final decision is always a human's. This tool provides evidence, not verdicts.
- **Full CI/CD pipeline execution** — the tool does not run test suites, compile binaries, or start services. It identifies whether these capabilities exist, not whether they pass.
- **Real-time scoring** — this is a batch analysis tool, not a live competition platform.
- **Private repository access** — designed for public repos or repos accessible with a PAT.

---

## 3. Target Users

| User | Need | Value |
|------|------|-------|
| **Hackathon organizers** | Consistent evaluation across many submissions | Leaderboard + summary report in minutes |
| **Technical judges** | Evidence-based scoring guidance | Per-repo report with score rationale |
| **Educators** | Assess student project quality | Code quality + testing metrics |
| **Event sponsors** | Identify technically strong projects | Score rankings by dimension |
| **Open-source maintainers** | Evaluate contribution quality | Same rubric applied consistently |

---

## 4. System in the Software Development Lifecycle

This tool sits at the intersection of **code review** and **quality assurance** — two pillars of professional software engineering that hackathon projects routinely skip under time pressure.

```
[ Hackathon Submission ]
        ↓
[ hackanalyze analyze <url> ]
        ↓
[ Clone → Structure → Language → Docs → Build → Quality → Tests → Architecture → Originality ]
        ↓
[ Score (1-10) + Per-Repo Report ]
        ↓
[ Summary Report + Leaderboard ]
        ↓
[ Human Judge Review ]
        ↓
[ Award Decision ]
```

**Integration points in the SDLC:**

- **Pre-review gate**: Run before judges begin reading to produce a ranked shortlist
- **CI automation**: Can run in GitHub Actions as a scheduled job if submissions come via PR
- **Post-competition feedback**: Reports can be shared with participants as learning material
- **Template detection**: Future version can compare submissions against known starter templates to detect low-effort entries

**How it fits professional software practices:**

Every dimension the tool scores corresponds to a real engineering discipline:
- Code quality → code review, static analysis
- Testing → TDD, QA processes
- Build success → CI/CD, DevOps
- Architecture → system design
- Documentation → technical writing, DX
- Originality → IP compliance, open-source licensing

By scoring these, the tool teaches participants what professional software looks like — and rewards those who practiced it.

---

## 5. Key Capabilities

### Analysis Engine
- **8 independent analyzers** running sequentially per repo, each isolated so failures don't cascade
- **Language-agnostic core** with language-specific plugins for code quality tools
- **Configurable scoring rubric** — weights can be adjusted to reflect hackathon theme (e.g., weight originality higher for an innovation-focused event)

### Safety
- All subprocess calls use list-form arguments (`shell=False`) — untrusted repo paths cannot inject commands
- Build attempts use dry-run commands (`pip install --dry-run`, `npm install --dry-run`)
- Configurable timeout for all external commands (default: 120s for builds, 300s for clones)
- Max repo size guard (default: 500MB) — checked via GitHub API before cloning

### Plagiarism Detection
- **Layer 1 — GitHub code search**: Extracts characteristic code snippets, searches GitHub for matching tokens. Results cached for 24 hours to respect rate limits.
- **Layer 2 — Claude AI assessment**: Reviews snippet + matched URLs, returns `LOW | MEDIUM | HIGH` risk verdict with rationale.

### Reporting
- **Per-repo Markdown report** with score breakdown table, architecture narrative, build output, test metrics, and originality assessment
- **Summary Markdown report** with leaderboard, dimension comparison tables, statistics, and highlighted concerns
- **Rich terminal output** with color-coded scores and progress indicators

---

## 6. Guiding Principles

1. **Transparency first** — every score has a traceable rationale. Judges can see exactly why a project scored 0.3 on testing (e.g., "no test files found").

2. **Evidence over impression** — scores derive from objective measurements (file counts, LOC ratios, tool outputs), not subjective reading.

3. **Fair by design** — non-Python projects are not penalized for the absence of Python-specific tools; heuristics provide neutral baseline scores when language-specific analysis isn't available.

4. **Reproducibility** — same repo + same tool version = same score (within AI model non-determinism bounds for Claude-generated narratives).

5. **Safety above speed** — no command runs without a timeout; no shell string interpolation; max size guards prevent resource exhaustion.

6. **Privacy by default** — no repo code is stored beyond the local cache. GitHub search API only receives 6-8 token query strings, not full code blocks.

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Analysis time per repo (no build, no plagiarism) | < 3 minutes |
| Analysis time per repo (full analysis) | < 10 minutes |
| Batch of 10 repos (full analysis) | < 30 minutes on standard laptop |
| Plagiarism detection rate | ≥ 80% of known-copied repos flagged medium/high |
| Judge score correlation | ≥ 70% agreement between tool score and judge score (±1.5 points) |
| Crash rate on top-10 GitHub language repos | 0% |
| Graceful degradation on missing tools | 100% (all analyzers have fallbacks) |

---

## 8. Future Directions

| Direction | Description | Priority |
|-----------|-------------|----------|
| **Plugin system** | Register custom analyzers via Python entry points | High |
| **Web UI** | FastAPI + React dashboard for visual report review | Medium |
| **Submission API integration** | Connect to Devpost or GitHub Hackathons APIs to pull repo lists automatically | Medium |
| **Differential analysis** | Compare submission against a known starter template to detect low-effort entries | High |
| **Async pipeline** | `asyncio` + concurrent repo analysis for large batches | Medium |
| **SQLite persistence** | Store results across runs for trend analysis | Low |
| **LLM code review** | Embed line-level AI comments in the report | Low |
| **SBOM generation** | Software Bill of Materials for license compliance checking | Low |

---

## 9. Why This Fits the Bigger Picture

Software quality is not optional — it is the foundation of maintainable, scalable, secure systems. Hackathons, by their nature, compress the development lifecycle into 24-48 hours. This creates a selection pressure for impressive demos over solid engineering.

By making quality analysis instant and automatic, this tool shifts that pressure. Teams that write tests, document their code, follow architectural patterns, and produce original work should be rewarded — not just teams with the flashiest UI.

In the long run, the vision is a world where every developer — whether in a hackathon or at a startup — gets immediate, actionable feedback on the technical quality of their work. This tool is a step toward that.

---

*"The bitterness of poor quality remains long after the sweetness of meeting the deadline is forgotten."*

---

*Vision Document v1.0 — Hackathon Repository Analyzer*
