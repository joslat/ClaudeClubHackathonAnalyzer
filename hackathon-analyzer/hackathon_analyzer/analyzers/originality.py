"""Analyzer: code originality via GitHub code search + Claude AI assessment."""

import re
from pathlib import Path
from typing import Optional

from hackathon_analyzer.core.models import OriginalityResult, RepoMeta, SnippetMatch
from hackathon_analyzer.utils.file_utils import safe_read_text, walk_repo

_SNIPPETS_TO_CHECK = 5
_MIN_SNIPPET_LINES = 8
_MAX_SNIPPET_LINES = 30

# Common boilerplate to skip
_BOILERPLATE_PATTERNS = re.compile(
    r"(hello.world|if __name__|setup\.py|requirements|MIT License|Apache License)",
    re.IGNORECASE,
)


def analyze_originality(
    repo_path: Path,
    meta: RepoMeta,
    language: str,
    github_client=None,
    claude_client=None,
) -> OriginalityResult:
    result = OriginalityResult()

    snippets = _extract_signature_snippets(repo_path, language, n=_SNIPPETS_TO_CHECK)
    result.snippets_checked = len(snippets)

    if not snippets:
        result.plagiarism_risk = "unknown"
        result.claude_verdict = "No suitable code snippets found for analysis."
        return result

    # Layer 1: GitHub code search
    all_matches: list[SnippetMatch] = []
    if github_client is not None:
        for snippet in snippets:
            query = _build_search_query(snippet)
            if not query:
                continue
            raw_matches = github_client.search_code(query, language)
            for m in raw_matches:
                # Skip if it's the repo itself
                if f"{meta.owner}/{meta.name}" in m.get("repo", ""):
                    continue
                all_matches.append(
                    SnippetMatch(
                        snippet=snippet[:200],
                        matched_repo=m["repo"],
                        matched_url=m["url"],
                        similarity_method="github-search",
                    )
                )

    result.matches_found = all_matches
    result.similarity_score = _compute_similarity_score(all_matches, len(snippets))

    # Layer 2: Claude assessment
    if claude_client is not None:
        match_dicts = [
            {"repo": m.matched_repo, "url": m.matched_url} for m in all_matches
        ]
        verdict_text = claude_client.assess_plagiarism(snippets, match_dicts)
        if verdict_text:
            result.claude_verdict = verdict_text
            result.plagiarism_risk = _extract_risk_level(verdict_text)
        else:
            result.plagiarism_risk = _risk_from_score(result.similarity_score)
    else:
        result.plagiarism_risk = _risk_from_score(result.similarity_score)
        result.claude_verdict = (
            f"Heuristic assessment: {len(all_matches)} GitHub matches found "
            f"across {len(snippets)} snippets checked."
        )

    return result


def _extract_signature_snippets(repo_path: Path, language: str, n: int) -> list[str]:
    """Extract n characteristic code snippets (function/class bodies >= MIN_SNIPPET_LINES)."""
    from hackathon_analyzer.analyzers.language import _EXT_MAP

    lang_exts = {ext for ext, lang in _EXT_MAP.items() if lang == language}
    if not lang_exts:
        lang_exts = {".py", ".js", ".ts", ".java", ".go", ".rs"}

    # Collect candidate files sorted by size (largest first, excluding tests)
    candidates: list[tuple[int, Path]] = []
    for dirpath, _, filenames in walk_repo(repo_path):
        for fname in filenames:
            fpath = dirpath / fname
            if fpath.suffix.lower() not in lang_exts:
                continue
            if "test" in fname.lower() or "spec" in fname.lower():
                continue
            try:
                size = fpath.stat().st_size
                candidates.append((size, fpath))
            except OSError:
                pass

    candidates.sort(reverse=True)
    snippets: list[str] = []

    for _, fpath in candidates[:20]:  # examine top 20 largest files
        if len(snippets) >= n:
            break
        content = safe_read_text(fpath, max_bytes=200_000)
        if not content:
            continue
        extracted = _extract_functions(content, language)
        for snippet in extracted:
            if len(snippets) >= n:
                break
            # Skip boilerplate
            if _BOILERPLATE_PATTERNS.search(snippet):
                continue
            snippets.append(snippet)

    return snippets


def _extract_functions(content: str, language: str) -> list[str]:
    """Extract function/class definitions from source code."""
    lines = content.splitlines()
    snippets: list[str] = []
    i = 0

    if language == "Python":
        func_start = re.compile(r"^(def |class )\w+")
    elif language in ("JavaScript", "TypeScript"):
        func_start = re.compile(r"^(function |const \w+ = |class |\w+\()")
    elif language in ("Java", "C#", "C++"):
        # Matches method/class declarations like:
        #   public async Task<T> MethodName(   or   private void Foo() {
        func_start = re.compile(r"^\s*(public|private|protected|internal|static|override|async).*\{?\s*$")
    else:
        func_start = re.compile(r"^(func |fn |def |function |class )")

    while i < len(lines):
        if func_start.match(lines[i].lstrip()):
            # Collect up to MAX_SNIPPET_LINES
            end = min(i + _MAX_SNIPPET_LINES, len(lines))
            block = lines[i:end]
            if len(block) >= _MIN_SNIPPET_LINES:
                snippet = "\n".join(block)
                # Normalize whitespace
                snippet = re.sub(r"\s+", " ", snippet).strip()
                if len(snippet) > 50:
                    snippets.append(snippet[:800])
        i += 1

    return snippets


def _build_search_query(snippet: str) -> str:
    """Extract 6-8 distinctive tokens from a snippet for GitHub search."""
    # Remove common keywords and punctuation
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{3,}", snippet)
    stopwords = {
        "def", "class", "function", "return", "import", "from", "self",
        "this", "true", "false", "null", "None", "const", "let", "var",
        "public", "private", "static", "void", "string", "int", "float",
        # C# / Java extras
        "override", "async", "await", "internal", "protected", "sealed",
        "Task", "List", "Dictionary", "IEnumerable", "bool", "object",
    }
    unique_tokens = list(dict.fromkeys(t for t in tokens if t.lower() not in stopwords))
    query_tokens = unique_tokens[:7]
    return " ".join(query_tokens) if len(query_tokens) >= 3 else ""


def _compute_similarity_score(matches: list[SnippetMatch], total_snippets: int) -> float:
    if total_snippets == 0:
        return 0.0
    unique_snippets_matched = len({m.snippet[:50] for m in matches})
    return round(min(unique_snippets_matched / total_snippets, 1.0), 3)


def _extract_risk_level(verdict_text: str) -> str:
    text_upper = verdict_text.upper()
    if "RISK: HIGH" in text_upper:
        return "high"
    if "RISK: MEDIUM" in text_upper:
        return "medium"
    if "RISK: LOW" in text_upper:
        return "low"
    return _risk_from_score(0.0)


def _risk_from_score(score: float) -> str:
    if score >= 0.6:
        return "high"
    if score >= 0.3:
        return "medium"
    return "low"
