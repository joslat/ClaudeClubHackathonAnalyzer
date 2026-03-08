# New Ideas for Hackathon Analyzer — Proposed Metrics & Dimensions

> **Purpose**: Expand analysis beyond structural code quality into dimensions that capture innovation, ambition, trustworthiness, and real-world viability of a hackathon submission.
>
> Each idea is scored for **Originality** (how novel it is as an automated metric, 1–10) and **Value** (how useful it would be to a hackathon judge, 1–10). Ideas are ordered by their consensus score (average of both).

---

## Summary Table

| # | Name | Description | Originality | Value | Score |
|---|------|-------------|:-----------:|:-----:|:-----:|
| 1 | [Promise–Reality Gap](#1-promisereality-gap) | Claude reads the README then audits the codebase: does the project actually build what it claims? | 9 | 10 | **9.5** |
| 2 | [Vision Ambition Score](#2-vision-ambition-score) | Claude evaluates the README for problem clarity, novelty of the idea, and ambition of the stated solution | 9 | 9 | **9.0** |
| 3 | [Tech Stack Novelty](#3-tech-stack-novelty) | Score how modern and innovative the dependency choices are — LLM APIs, vector DBs, edge runtimes, etc. | 8 | 9 | **8.5** |
| 4 | [Hackathon Freshness](#4-hackathon-freshness) | Detect if the repo was created during the hackathon window; flag pre-existing projects submitted as new work | 8 | 9 | **8.5** |
| 5 | [AI / LLM Integration Depth](#5-ai--llm-integration-depth) | Detect and score use of AI APIs, agents, embeddings, RAG patterns, and prompt engineering | 7 | 9 | **8.0** |
| 6 | [Demo Readiness](#6-demo-readiness) | Does it have a live link, demo video, one-command startup, or hosted deployment? | 6 | 9 | **7.5** |
| 7 | [Deployment Readiness](#7-deployment-readiness) | Dockerfile, cloud deployment configs, IaC, Railway/Vercel/Render setup, one-click deploy | 6 | 9 | **7.5** |
| 8 | [Hardcoded Secrets Scan](#8-hardcoded-secrets-scan) | Regex scan for leaked API keys, passwords, tokens, and connection strings in source code | 5 | 9 | **7.0** → corrected: 6/9 = **7.5** |
| 9 | [External Integration Breadth](#9-external-integration-breadth) | How many distinct external APIs, services, and data sources does it connect to? | 7 | 8 | **7.5** |
| 10 | [Business Model / Use Case Clarity](#10-business-model--use-case-clarity) | Does the README articulate who benefits, what problem is solved, and how it creates value? | 8 | 7 | **7.5** |
| 11 | [Vertical Domain Depth](#11-vertical-domain-depth) | Does the project go deep into a specific domain (healthcare, climate, fintech) using domain-specific data/APIs? | 8 | 7 | **7.5** |
| 12 | [Ethical AI Considerations](#12-ethical-ai-considerations) | For AI projects: bias documentation, privacy handling, fairness considerations, content moderation | 9 | 6 | **7.5** |
| 13 | [Observability Score](#13-observability-score) | Structured logging, metrics endpoints, health checks, distributed tracing — is the system observable in production? | 7 | 7 | **7.0** |
| 14 | [Collaborative Signals](#14-collaborative-signals) | Multiple contributors, meaningful commit distribution, non-trivial commit messages, PR evidence | 6 | 7 | **6.5** |
| 15 | [Dependency Security](#15-dependency-security) | Known CVEs in declared dependencies, outdated packages with security patches available | 5 | 8 | **6.5** |
| 16 | [Performance Patterns](#16-performance-patterns) | Async I/O, caching, pagination, connection pooling, lazy loading — evidence of performance awareness | 5 | 7 | **6.0** |
| 17 | [Error Handling Depth](#17-error-handling-depth) | Custom exception classes, retry logic, circuit breakers, graceful degradation, user-friendly error messages | 4 | 7 | **5.5** |
| 18 | [Cross-platform / Portability](#18-cross-platform--portability) | Works in Docker, browser, or multiple OS without manual setup | 5 | 6 | **5.5** |
| 19 | [Feedback Loop Quality](#19-feedback-loop-quality) | User-facing progress indicators, logging to stderr not stdout, meaningful exit codes, helpful CLI output | 5 | 6 | **5.5** |
| 20 | [Accessibility Score](#20-accessibility-score) | ARIA labels, semantic HTML, keyboard navigation, color contrast, screen-reader support (for web projects) | 6 | 5 | **5.5** |

---

## Detailed Descriptions

---

### 1. Promise–Reality Gap

**Consensus Score: 9.5** | Originality: 9 | Value: 10

The single most impactful addition. The current analyzer scores structural quality but has no opinion on *what* the project actually does. This dimension sends Claude two things:

1. The README / documentation (what the project *claims* to do)
2. A summary of the actual codebase (files, modules, key functions)

Claude then assesses: *Does the implementation match the promise?* A project that claims to be a "real-time collaborative AI coding assistant" but has a single 50-line script scores very differently from one whose codebase genuinely reflects that ambition.

**Why it matters for hackathons**: This is the #1 thing judges manually check. Automating it catches projects that submitted polished pitches with hollow implementations.

**Implementation sketch**:
- Collect: README text + architecture summary + top-level file list + function signatures
- Claude prompt: "Based on the following README and codebase summary, assess on a scale of 0–1 whether the implementation matches the stated goals. Provide a rationale."
- Output: `promise_reality_score` (0.0–1.0), `claude_verdict` text

---

### 2. Vision Ambition Score

**Consensus Score: 9.0** | Originality: 9 | Value: 9

A separate Claude call that evaluates the README purely as a vision document, independently of implementation quality. Scores on:

- **Problem clarity**: Is the problem well-defined and real?
- **Solution novelty**: Is the proposed approach meaningfully different from existing tools?
- **Scope ambition**: Is the goal bold but achievable within hackathon timeframe?
- **Target audience specificity**: Is there a clear user who benefits?

**Why it matters**: Hackathons reward ideas, not just execution. A team that tackled a hard, novel problem with moderate implementation quality often deserves more credit than one that polished a trivial problem.

**Implementation sketch**:
- Claude prompt: structured rubric (4 sub-dimensions, each 0–1) applied to README text
- Weighted: problem clarity (30%), solution novelty (30%), ambition (25%), audience (15%)
- Output: `vision_score` (0.0–1.0), `vision_rationale`

---

### 3. Tech Stack Novelty

**Consensus Score: 8.5** | Originality: 8 | Value: 9

Parse `requirements.txt`, `package.json`, `go.mod`, `.csproj`, etc. and map each dependency to a novelty category:

| Category | Examples | Score |
|----------|----------|-------|
| Bleeding edge (released <18 months) | Newest LLM SDKs, latest web frameworks | 1.0 |
| Modern (2–4 years) | FastAPI, Next.js 13+, Axum | 0.7 |
| Established (5+ years) | Flask, Express, Spring | 0.4 |
| Legacy | jQuery, PHP 5, Python 2 libs | 0.1 |

Also boost for cross-domain combinations (ML library in a mobile app, blockchain + AI, etc.) which signal creative synthesis.

**Why it matters**: A hackathon judge values seeing whether teams are working with modern tools or submitting something they built in 2019.

---

### 4. Hackathon Freshness

**Consensus Score: 8.5** | Originality: 8 | Value: 9

Use the GitHub API to check:
- `created_at`: When was the repo created? If before the hackathon window → flag
- `pushed_at`: Last push (already available from API response)
- Commit count and date spread (if GitHub token available)
- First commit timestamp: Was there meaningful code before the event started?

**Why it matters**: This is a fairness dimension. Projects submitted to hackathons that were substantially pre-built before the event started should be flagged, not disqualified, but surfaced for judge review.

**Implementation sketch**:
- GitHub API `/repos/{owner}/{name}` already returns `created_at`
- Ask judges to configure `hackathon_start_date` in config
- Output: `repo_age_days` at submission, `freshness_flag` (old/fresh/unknown)

---

### 5. AI / LLM Integration Depth

**Consensus Score: 8.0** | Originality: 7 | Value: 9

Detect and score the sophistication of AI/ML integration by scanning imports, config files, and code patterns:

| Pattern | Score |
|---------|-------|
| Raw LLM API call (OpenAI, Anthropic, etc.) | 0.3 |
| Structured prompting / system messages | 0.5 |
| Function/tool calling | 0.6 |
| RAG (vector DB + retrieval) | 0.7 |
| Multi-agent orchestration | 0.8 |
| Fine-tuned model usage | 0.9 |
| Custom training pipeline | 1.0 |

Detect: `openai`, `anthropic`, `langchain`, `llamaindex`, `chromadb`, `pinecone`, `weaviate`, `crewai`, `autogen`, `semantic_kernel`, `ollama`, `transformers`, etc.

**Why it matters**: In AI hackathons, depth of AI integration is a primary judging criterion. This makes it measurable.

---

### 6. Demo Readiness

**Consensus Score: 7.5** | Originality: 6 | Value: 9

Scan README and repository for evidence that the project can be demonstrated immediately:

- Demo video link (YouTube, Loom, etc.) in README → +0.30
- Live hosted URL (Vercel, Render, Railway, Streamlit Cloud, HuggingFace Spaces) → +0.30
- One-command startup (`docker compose up`, `npm start`, `streamlit run app.py`) → +0.20
- Sample data or fixtures included → +0.10
- Screenshot(s) in README → +0.10

**Why it matters**: Judges evaluate hundreds of projects. A project that can be seen live in 30 seconds beats one that requires a 20-step local setup, regardless of code quality.

---

### 7. Deployment Readiness

**Consensus Score: 7.5** | Originality: 6 | Value: 9

Beyond a Dockerfile (already detected), score deployment sophistication:

- `Dockerfile` → base (already in Architecture)
- `docker-compose.yml` → multi-service orchestration
- Cloud config files (`railway.json`, `render.yaml`, `vercel.json`, `fly.toml`) → one-click deploy
- Kubernetes manifests (`k8s/`, `helm/`) → production-grade
- Infrastructure as Code (`terraform/`, `pulumi/`) → full IaC
- CI/CD that deploys (not just tests) → automated deployment pipeline
- Environment variable documentation (`.env.example`) → proper config management

---

### 8. Hardcoded Secrets Scan

**Consensus Score: 7.5** | Originality: 6 | Value: 9

Regex-scan all non-binary files for patterns matching real credentials:

- API key patterns: `sk-[a-zA-Z0-9]{40,}`, `ghp_[a-zA-Z0-9]{36}`, `AKIA[A-Z0-9]{16}` (AWS)
- Generic patterns: `password\s*=\s*["'][^"']{6,}`, `secret\s*=\s*["'][^"']{8,}`
- Connection strings: `mongodb+srv://`, `postgresql://user:pass@`
- Private key blocks: `-----BEGIN RSA PRIVATE KEY-----`

Score: 0 secrets = 1.0, 1 found = 0.3, 2+ found = 0.0 (automatic flag to judges)

**Why it matters**: Submitted hackathon repos with hardcoded credentials is a safety and security concern. It also signals carelessness. This is easy to detect automatically.

---

### 9. External Integration Breadth

**Consensus Score: 7.5** | Originality: 7 | Value: 8

Count and categorize distinct external services the project integrates with:

- Payment APIs (Stripe, PayPal)
- Communication (Twilio, SendGrid, Slack)
- Maps / geospatial (Google Maps, Mapbox)
- Auth providers (Auth0, Firebase Auth, OAuth flows)
- Cloud storage (S3, GCS, Azure Blob)
- Databases (Supabase, PlanetScale, Neon)
- Real-time (WebSockets, Pusher, Firebase Realtime)
- Data/analytics (Amplitude, Mixpanel)
- Domain-specific APIs (Spotify, GitHub, Twitter, etc.)

Score based on count and diversity: 0 = 0.3 (neutral), 1–2 = 0.6, 3–4 = 0.8, 5+ = 1.0

**Why it matters**: Integration breadth signals real-world applicability. A project that connects multiple live services is closer to a real product.

---

### 10. Business Model / Use Case Clarity

**Consensus Score: 7.5** | Originality: 8 | Value: 7

Claude evaluates the README for business/product thinking:

- Is there an identified target user or customer?
- Is the problem quantified or grounded in reality?
- Is there a clear value proposition?
- Is there a monetization concept or sustainability model?
- Is the competitive landscape acknowledged?

**Why it matters**: The best hackathon projects have both working code *and* a clear "why does this exist" narrative. This dimension captures product thinking that pure code analysis misses.

---

### 11. Vertical Domain Depth

**Consensus Score: 7.5** | Originality: 8 | Value: 7

Detect how deep the project goes into a specific vertical domain:

- **Domain APIs used**: NHS API, FHIR (healthcare), Plaid (fintech), NOAA (climate), etc.
- **Domain datasets**: Medical records, financial data, environmental sensors
- **Domain terminology in code/docs**: medical codes (ICD-10), financial instruments, climate metrics
- **Domain-specific libraries**: `biopython`, `QuantLib`, `rasterio`

Classify domain (healthcare, climate, education, fintech, agriculture, accessibility, security) and score depth within it.

**Why it matters**: A project that integrates real domain data and APIs (rather than mock data) demonstrates genuine domain understanding and real-world applicability.

---

### 12. Ethical AI Considerations

**Consensus Score: 7.5** | Originality: 9 | Value: 6

For AI/ML projects, scan for evidence of responsible AI practices:

- Bias documentation or mitigation code present?
- Privacy policy or data handling docs?
- Model card or model documentation?
- PII handling code (anonymization, pseudonymization)?
- Content filtering / safety layers?
- User consent mechanisms?
- Explainability features (SHAP, LIME, explanation endpoints)?

This dimension only activates when AI/ML libraries are detected. Score 0 if AI detected but no ethical considerations found; scale up with evidence.

**Why it matters**: AI hackathon judges increasingly care about responsible deployment. This makes it measurable and rewards teams that think beyond accuracy.

---

### 13. Observability Score

**Consensus Score: 7.0** | Originality: 7 | Value: 7

Detect production-readiness signals for monitoring and debugging:

- Structured logging (not `print()` / `console.log`) → `logging`, `winston`, `serilog`
- Log levels used (DEBUG/INFO/WARN/ERROR differentiated)
- Health check endpoint (`/health`, `/ping`, `/status`)
- Metrics endpoint (`/metrics`, Prometheus exporter)
- Distributed tracing (`opentelemetry`, `jaeger`)
- Error tracking integration (`sentry`, `rollbar`)

**Why it matters**: A system you can't observe in production is a system you can't trust. Observability signals engineering maturity that goes beyond making the happy path work.

---

### 14. Collaborative Signals

**Consensus Score: 6.5** | Originality: 6 | Value: 7

From git log (requires deeper clone, e.g. `--depth 50`) and GitHub API:

- Contributor count (solo vs. team)
- Commit distribution across contributors (is it one person doing 95% of work?)
- Commit message quality: descriptive ("Add rate limiting to /api/search") vs. noise ("fix", "wip", "asdfjkl")
- Presence of PR-merged commits (evidence of code review)
- Author email diversity (different people, not just git aliases)

**Why it matters**: Hackathons are team events. Understanding team dynamics — and whether collaboration was genuine — is relevant context for judges evaluating fairness and team cohesion.

---

### 15. Dependency Security

**Consensus Score: 6.5** | Originality: 5 | Value: 8

Check declared dependencies against known vulnerability databases:

- Python: `pip-audit` or check against PyPI safety DB
- Node.js: `npm audit --json` (dry-run, no install needed)
- Go: `govulncheck` on `go.mod`
- .NET: `dotnet list package --vulnerable`

Score: 0 known CVEs = 1.0, low-severity only = 0.7, medium = 0.4, high severity = 0.1, critical = 0.0

**Why it matters**: A hackathon project with critical security vulnerabilities in its dependencies is not production-ready regardless of code quality. Surface it early.

---

### 16. Performance Patterns

**Consensus Score: 6.0** | Originality: 5 | Value: 7

Detect evidence of performance-awareness in code:

- Async patterns: `async/await`, coroutines, goroutines, Tokio tasks
- Caching: `redis`, `memcached`, LRU cache decorators, HTTP caching headers
- Pagination: limit/offset params, cursor-based pagination, page tokens
- Database query optimization: index hints, select specific columns, avoid N+1
- Connection pooling: DB connection pool configs
- Background task processing: Celery, BullMQ, Sidekiq

**Why it matters**: A project that anticipates scale — even at prototype stage — shows systems thinking. This separates engineers from beginners.

---

### 17. Error Handling Depth

**Consensus Score: 5.5** | Originality: 4 | Value: 7

Beyond what code quality covers, measure error-handling *architecture*:

- Custom exception/error classes defined (not just catching generic `Exception`)
- Retry logic present (`tenacity`, `backoff`, exponential backoff patterns)
- Circuit breaker pattern
- Timeout handling on all external calls
- Fallback / graceful degradation when services are unavailable
- User-facing error messages are informative (not "Internal Server Error")

---

### 18. Cross-platform / Portability

**Consensus Score: 5.5** | Originality: 5 | Value: 6

How many environments can the project run in without modification?

- Web-based (universal, any browser): +0.30
- Docker container: +0.20 (already covered, bonus here)
- Cross-OS (Windows + Mac + Linux paths, no hardcoded `/tmp`): +0.20
- Mobile PWA or native: +0.20
- Cloud-agnostic (no vendor lock-in): +0.10

**Why it matters**: Judges often need to run projects on their own machines. Portability is a practical signal of developer empathy.

---

### 19. Feedback Loop Quality

**Consensus Score: 5.5** | Originality: 5 | Value: 6

How well does the system communicate its state to users and operators?

- Progress indicators for long operations (not just silent waiting)
- Meaningful CLI output (not silent success or undescriptive errors)
- Log output goes to `stderr`, results to `stdout` (proper Unix convention)
- Meaningful exit codes (not always 0)
- Confirmation prompts for destructive operations
- Success/failure notifications for async operations

---

### 20. Accessibility Score

**Consensus Score: 5.5** | Originality: 6 | Value: 5

For web-based projects: scan HTML/JSX/TSX for accessibility signals:

- ARIA labels on interactive elements (`aria-label`, `role=`)
- Semantic HTML (`<nav>`, `<main>`, `<button>` vs `<div onClick>`)
- `alt` text on all `<img>` tags
- Form labels linked to inputs (`<label for=...>`)
- No `tabindex` abuse
- Keyboard navigation (no `outline: none` without replacement)
- Color contrast (requires CSS analysis — heuristic only)

**Why it matters**: Accessibility is increasingly a requirement, not a nice-to-have. Projects that bake it in from the start show professional maturity.

---

## Implementation Priority Recommendation

If implementing in phases, the recommended order based on **implementation effort vs. value delivered**:

| Phase | Dimensions | Effort | Value Added |
|-------|-----------|--------|-------------|
| 1 (Quick wins) | Hardcoded Secrets Scan, Hackathon Freshness, Demo Readiness, Deployment Readiness | Low | Very High |
| 2 (Claude-powered) | Promise–Reality Gap, Vision Ambition Score | Medium | Highest |
| 3 (Dependency analysis) | Tech Stack Novelty, AI/LLM Integration Depth, Dependency Security, External Integration Breadth | Medium | High |
| 4 (Deep signals) | Collaborative Signals, Observability, Vertical Domain Depth, Business Model Clarity | High | Medium-High |
| 5 (Specialized) | Ethical AI, Accessibility, Performance Patterns, Error Handling | High | Domain-specific |

---

*Document authored during hackathon-analyzer development session | 2026-03-07*
