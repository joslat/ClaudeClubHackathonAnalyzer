"""Analyzer: file tree, directory depth, layout patterns."""

from pathlib import Path

from hackathon_analyzer.core.models import StructureResult
from hackathon_analyzer.utils.file_utils import walk_repo


def analyze_structure(repo_path: Path) -> StructureResult:
    result = StructureResult()
    ext_counts: dict[str, int] = {}
    tree_lines: list[str] = []
    max_depth = 0

    for dirpath, dirnames, filenames in walk_repo(repo_path):
        depth = len(dirpath.relative_to(repo_path).parts)
        max_depth = max(max_depth, depth)

        if depth <= 2 and len(tree_lines) < 60:
            indent = "  " * depth
            if depth > 0:
                tree_lines.append(f"{indent}{dirpath.name}/")

        result.total_dirs += len(dirnames)
        result.total_files += len(filenames)

        for fname in filenames:
            suffix = Path(fname).suffix.lower()
            if suffix:
                ext_counts[suffix] = ext_counts.get(suffix, 0) + 1
            if depth <= 2 and len(tree_lines) < 60:
                indent = "  " * (depth + 1)
                tree_lines.append(f"{indent}{fname}")

    result.max_depth = max_depth
    result.file_extensions = dict(sorted(ext_counts.items(), key=lambda x: -x[1]))
    result.tree_summary = "\n".join(tree_lines[:50])

    # Detect presence of key directories/files
    root_entries = {p.name.lower() for p in repo_path.iterdir()} if repo_path.exists() else set()
    result.has_src_layout = "src" in root_entries
    result.has_tests_dir = bool(
        any(n in root_entries for n in ["tests", "test", "spec", "__tests__"])
    )
    result.has_docs_dir = bool(any(n in root_entries for n in ["docs", "doc", "documentation"]))
    result.has_ci = (repo_path / ".github" / "workflows").is_dir() or (
        repo_path / ".gitlab-ci.yml"
    ).exists()
    result.has_docker = (
        (repo_path / "Dockerfile").exists() or (repo_path / "docker-compose.yml").exists()
    )

    # Layout patterns
    patterns = []
    if result.has_src_layout:
        patterns.append("src-layout")
    if (repo_path / "packages").is_dir() or (repo_path / "apps").is_dir():
        patterns.append("monorepo")
    if result.total_files < 10 and result.max_depth <= 2:
        patterns.append("flat-layout")
    if result.has_docs_dir:
        patterns.append("docs-as-code")
    result.layout_patterns = patterns

    return result
