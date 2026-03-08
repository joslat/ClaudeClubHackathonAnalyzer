"""Analyzer: Tech Stack Novelty — score how modern and innovative the dependencies are.

Parses dependency files (requirements.txt, package.json, pyproject.toml, go.mod,
Cargo.toml, *.csproj) and maps each package to a novelty tier.
"""

import re
from pathlib import Path
from typing import Optional

from hackathon_analyzer.core.models import TechStackNoveltyResult
from hackathon_analyzer.utils.file_utils import safe_read_text


# --- Novelty tiers ---
# Bleeding edge (released <18 months, score 1.0)
_BLEEDING_EDGE = {
    # AI/LLM — very recent
    "crewai", "autogen", "phidata", "dspy", "instructor", "marvin",
    "outlines", "guidance", "lmql", "guardrails-ai", "nemoguardrails",
    "litellm", "ollama", "groq", "mistralai", "cohere",
    # Web/runtime — very recent
    "bun", "hono", "effect", "drizzle-orm", "turso",
    # Infra
    "modal", "replicate", "together",
}

# Modern (2-4 years, score 0.7)
_MODERN = {
    # AI/LLM
    "openai", "anthropic", "langchain", "langchain-core", "langchain-community",
    "llamaindex", "llama-index", "chromadb", "pinecone", "pinecone-client",
    "weaviate-client", "qdrant-client", "milvus", "semantic-kernel",
    "transformers", "huggingface-hub", "sentence-transformers",
    "tiktoken", "tokenizers",
    # Python web
    "fastapi", "uvicorn", "litestar", "pydantic", "pydantic-settings",
    "httpx", "polars", "duckdb", "streamlit", "gradio",
    # JS/TS
    "next", "@next/font", "astro", "svelte", "@sveltejs/kit",
    "solid-js", "qwik", "remix", "trpc", "@trpc/server",
    "prisma", "@prisma/client", "drizzle-orm", "zod", "vitest",
    "turborepo", "tailwindcss",
    # Rust
    "axum", "leptos", "dioxus", "tauri",
    # Go
    "fiber", "echo",
    # .NET
    "semantic-kernel", "microsoft.extensions.ai",
    # Data
    "dagster", "prefect", "dbt-core",
}

# Established (5+ years, score 0.4)
_ESTABLISHED = {
    # Python
    "flask", "django", "celery", "sqlalchemy", "requests", "boto3",
    "pandas", "numpy", "scipy", "matplotlib", "scikit-learn", "sklearn",
    "pillow", "pytest", "black", "mypy", "ruff",
    # JS
    "express", "react", "react-dom", "vue", "angular", "@angular/core",
    "webpack", "babel", "jest", "mocha", "lodash", "axios", "redux",
    "mongoose", "sequelize", "typeorm", "knex",
    # Java
    "spring-boot", "spring-web", "jackson", "lombok", "junit",
    # Go
    "gin", "mux", "cobra",
    # .NET
    "newtonsoft.json", "entity-framework", "xunit", "nunit",
    "microsoft.aspnetcore", "serilog", "mediatr", "automapper",
}

# Legacy (score 0.1)
_LEGACY = {
    "jquery", "backbone", "underscore", "grunt", "bower", "gulp",
    "coffeescript", "prototype", "mootools", "dojo",
    "php5", "python2", "web2py", "turbogears",
    "moment",  # replaced by dayjs/date-fns
}

# Cross-domain combinations that signal creative synthesis
_DOMAIN_CATEGORIES = {
    "ai": {"openai", "anthropic", "langchain", "transformers", "crewai", "autogen",
            "llamaindex", "llama-index", "chromadb", "pinecone", "ollama", "huggingface-hub"},
    "web": {"react", "vue", "svelte", "next", "fastapi", "django", "flask", "express", "angular"},
    "mobile": {"react-native", "flutter", "expo", "capacitor", "ionic"},
    "data": {"pandas", "polars", "duckdb", "spark", "dagster", "dbt-core"},
    "blockchain": {"web3", "ethers", "solana-web3", "hardhat", "foundry"},
    "iot": {"mqtt", "paho-mqtt", "bleak", "pyserial", "firmata"},
}


def analyze_tech_stack_novelty(repo_path: Path) -> TechStackNoveltyResult:
    """Analyze dependencies for tech stack novelty."""
    result = TechStackNoveltyResult()

    all_deps = _collect_all_dependencies(repo_path)
    if not all_deps:
        result.novelty_score = 0.4  # neutral
        return result

    bleeding = 0
    modern = 0
    established = 0
    legacy = 0
    tier_scores: list[float] = []

    for dep in all_deps:
        dep_lower = dep.lower().strip()
        if dep_lower in _BLEEDING_EDGE:
            tier = "bleeding_edge"
            tier_scores.append(1.0)
            bleeding += 1
            result.notable_deps.append(f"{dep} (bleeding edge)")
        elif dep_lower in _MODERN:
            tier = "modern"
            tier_scores.append(0.7)
            modern += 1
        elif dep_lower in _LEGACY:
            tier = "legacy"
            tier_scores.append(0.1)
            legacy += 1
            result.notable_deps.append(f"{dep} (legacy)")
        elif dep_lower in _ESTABLISHED:
            tier = "established"
            tier_scores.append(0.4)
            established += 1
        else:
            tier = "unknown"
            tier_scores.append(0.4)  # default to established tier
            established += 1  # count as established

        result.dependencies_found[dep] = tier

    result.bleeding_edge_count = bleeding
    result.modern_count = modern
    result.established_count = established
    result.legacy_count = legacy

    # Base score: weighted average of tier scores
    base_score = sum(tier_scores) / len(tier_scores) if tier_scores else 0.4

    # Cross-domain bonus
    domains_used = set()
    for dep in all_deps:
        dep_lower = dep.lower().strip()
        for domain, packages in _DOMAIN_CATEGORIES.items():
            if dep_lower in packages:
                domains_used.add(domain)
    if len(domains_used) >= 2:
        result.cross_domain_bonus = True
        base_score = min(1.0, base_score + 0.1)
        result.notable_deps.append(f"Cross-domain: {', '.join(sorted(domains_used))}")

    result.novelty_score = round(base_score, 3)

    # Build rationale
    total = len(all_deps)
    tier_parts = []
    if bleeding:
        tier_parts.append(f"{bleeding} bleeding-edge ({bleeding*100//total}%)")
    if modern:
        tier_parts.append(f"{modern} modern ({modern*100//total}%)")
    if established:
        tier_parts.append(f"{established} established ({established*100//total}%)")
    if legacy:
        tier_parts.append(f"{legacy} legacy ({legacy*100//total}%)")

    tier_summary = ", ".join(tier_parts)
    if base_score >= 0.7:
        verdict = "The stack leans modern/cutting-edge, suggesting familiarity with current tools."
    elif base_score >= 0.45:
        verdict = "A mix of modern and established libraries; solid but conventional choices."
    elif legacy:
        verdict = "Several legacy dependencies pull the score down; consider modernizing."
    else:
        verdict = "Mostly established/mature libraries; functional but not innovative in tooling."

    result.novelty_rationale = f"{total} dependencies analyzed: {tier_summary}. {verdict}"
    if result.cross_domain_bonus:
        result.novelty_rationale += f" Cross-domain bonus applied for spanning {', '.join(sorted(domains_used))}."

    return result


def _collect_all_dependencies(repo_path: Path) -> list[str]:
    """Parse all dependency files and return a flat list of package names."""
    deps: list[str] = []

    # Python: requirements.txt
    for req_file in ["requirements.txt", "requirements-dev.txt", "requirements_dev.txt"]:
        path = repo_path / req_file
        if path.exists():
            deps.extend(_parse_requirements_txt(path))

    # Python: pyproject.toml
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        deps.extend(_parse_pyproject_toml(pyproject))

    # Python: setup.py (basic extraction)
    setup_py = repo_path / "setup.py"
    if setup_py.exists():
        deps.extend(_parse_setup_py(setup_py))

    # Node.js: package.json
    pkg_json = repo_path / "package.json"
    if pkg_json.exists():
        deps.extend(_parse_package_json(pkg_json))

    # Go: go.mod
    go_mod = repo_path / "go.mod"
    if go_mod.exists():
        deps.extend(_parse_go_mod(go_mod))

    # Rust: Cargo.toml
    cargo = repo_path / "Cargo.toml"
    if cargo.exists():
        deps.extend(_parse_cargo_toml(cargo))

    # .NET: *.csproj / Directory.Packages.props
    deps.extend(_parse_dotnet_deps(repo_path))

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for d in deps:
        dl = d.lower().strip()
        if dl and dl not in seen:
            seen.add(dl)
            unique.append(d.strip())
    return unique


def _parse_requirements_txt(path: Path) -> list[str]:
    text = safe_read_text(path, max_bytes=50_000) or ""
    deps = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Extract package name before version specifier
        match = re.match(r"([a-zA-Z0-9_-]+)", line)
        if match:
            deps.append(match.group(1))
    return deps


def _parse_pyproject_toml(path: Path) -> list[str]:
    text = safe_read_text(path, max_bytes=50_000) or ""
    deps = []
    # Simple regex for dependencies = [...] and [project.dependencies]
    # Matches lines like: "fastapi>=0.100", 'pydantic', etc.
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"\[project\]", stripped) or "dependencies" in stripped.lower():
            in_deps = True
            continue
        if stripped.startswith("[") and "dependencies" not in stripped.lower():
            in_deps = False
            continue
        if in_deps:
            match = re.match(r'["\']([a-zA-Z0-9_-]+)', stripped)
            if match:
                deps.append(match.group(1))
    return deps


def _parse_setup_py(path: Path) -> list[str]:
    text = safe_read_text(path, max_bytes=50_000) or ""
    deps = []
    for match in re.finditer(r'["\']([a-zA-Z0-9_-]+)(?:[><=!]|$)', text):
        name = match.group(1)
        if len(name) > 1 and name not in {"python", "setup", "find_packages", "name", "version"}:
            deps.append(name)
    return deps


def _parse_package_json(path: Path) -> list[str]:
    import json
    text = safe_read_text(path, max_bytes=100_000) or ""
    deps = []
    try:
        data = json.loads(text)
        for section in ["dependencies", "devDependencies", "peerDependencies"]:
            for pkg in data.get(section, {}):
                # Strip org prefix for matching: @next/font → next
                name = pkg.lstrip("@").split("/")[0] if pkg.startswith("@") else pkg
                deps.append(name)
    except (json.JSONDecodeError, TypeError):
        pass
    return deps


def _parse_go_mod(path: Path) -> list[str]:
    text = safe_read_text(path, max_bytes=50_000) or ""
    deps = []
    for line in text.splitlines():
        line = line.strip()
        # go.mod format: github.com/gin-gonic/gin v1.9.1
        match = re.match(r"(?:github\.com|golang\.org|go\.uber\.org)/([^/\s]+)", line)
        if match:
            deps.append(match.group(1))
    return deps


def _parse_cargo_toml(path: Path) -> list[str]:
    text = safe_read_text(path, max_bytes=50_000) or ""
    deps = []
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and "dependencies" in stripped.lower():
            in_deps = True
            continue
        if stripped.startswith("[") and "dependencies" not in stripped.lower():
            in_deps = False
            continue
        if in_deps:
            match = re.match(r"([a-zA-Z0-9_-]+)\s*=", stripped)
            if match:
                deps.append(match.group(1))
    return deps


def _parse_dotnet_deps(repo_path: Path) -> list[str]:
    """Parse .NET PackageReference entries from .csproj and Directory.Packages.props."""
    deps = []
    patterns = list(repo_path.rglob("*.csproj"))
    props = repo_path / "Directory.Packages.props"
    if props.exists():
        patterns.append(props)

    for csproj in patterns[:10]:  # limit to 10 project files
        text = safe_read_text(csproj, max_bytes=50_000) or ""
        for match in re.finditer(r'PackageReference\s+Include="([^"]+)"', text, re.IGNORECASE):
            deps.append(match.group(1))
    return deps
