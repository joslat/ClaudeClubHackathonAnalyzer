"""Analyzer: README quality, license, changelog, and docs presence."""

import re
from pathlib import Path

from hackathon_analyzer.core.models import DocumentationResult
from hackathon_analyzer.utils.file_utils import find_file_icase, safe_read_text

_README_NAMES = ["README.md", "README.rst", "README.txt", "README"]
_LICENSE_NAMES = ["LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING"]
_CHANGELOG_NAMES = ["CHANGELOG.md", "CHANGELOG", "CHANGES.md", "HISTORY.md"]
_CONTRIBUTING_NAMES = ["CONTRIBUTING.md", "CONTRIBUTING"]

_BADGE_PATTERN = re.compile(r"!\[.*?\]\(https?://", re.IGNORECASE)
_SECTION_PATTERN = re.compile(r"^#{1,3}\s+(.+)", re.MULTILINE)


def analyze_documentation(repo_path: Path) -> DocumentationResult:
    result = DocumentationResult()

    readme_path = find_file_icase(repo_path, _README_NAMES)
    if readme_path:
        result.has_readme = True
        content = safe_read_text(readme_path) or ""
        words = content.split()
        result.readme_word_count = len(words)
        result.readme_has_badges = bool(_BADGE_PATTERN.search(content))

        sections = [s.lower() for s in _SECTION_PATTERN.findall(content)]
        result.readme_has_installation_section = any(
            "install" in s or "setup" in s or "getting started" in s for s in sections
        )
        result.readme_has_usage_section = any(
            "usage" in s or "how to" in s or "example" in s or "quickstart" in s
            for s in sections
        )

    result.has_license = find_file_icase(repo_path, _LICENSE_NAMES) is not None
    result.has_changelog = find_file_icase(repo_path, _CHANGELOG_NAMES) is not None
    result.has_contributing = find_file_icase(repo_path, _CONTRIBUTING_NAMES) is not None
    result.has_docs_dir = any(
        (repo_path / d).is_dir() for d in ["docs", "doc", "documentation"]
    )

    # Check for API docs (OpenAPI, Sphinx, JSDoc, etc.)
    result.has_api_docs = (
        any((repo_path / f).exists() for f in ["openapi.yml", "openapi.yaml", "swagger.yml"])
        or (repo_path / "docs" / "api").is_dir()
        or any(repo_path.glob("docs/**/*.rst"))
    )

    result.doc_score = _compute_doc_score(result)
    return result


def _compute_doc_score(r: DocumentationResult) -> float:
    score = 0.0
    if r.has_readme:
        score += 0.30
    if r.readme_word_count > 200:
        score += 0.10
    if r.readme_has_installation_section:
        score += 0.10
    if r.readme_has_usage_section:
        score += 0.10
    if r.readme_has_badges:
        score += 0.05
    if r.has_license:
        score += 0.15
    if r.has_changelog:
        score += 0.05
    if r.has_docs_dir:
        score += 0.10
    if r.has_api_docs:
        score += 0.05
    return min(score, 1.0)
