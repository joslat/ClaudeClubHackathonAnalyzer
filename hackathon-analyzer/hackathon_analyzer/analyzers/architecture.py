"""Analyzer: architectural pattern detection and Claude-powered narrative summary."""

from pathlib import Path
from typing import Optional

from hackathon_analyzer.core.models import ArchitectureResult, StructureResult
from hackathon_analyzer.utils.file_utils import count_lines, walk_repo

_GOD_FILE_THRESHOLD = 500  # LOC

_MVC_DIRS = {"controllers", "controller", "models", "model", "views", "view", "templates"}
_SERVICE_DIRS = {"services", "service", "repositories", "repository", "handlers", "handler"}
_LAYERED_DIRS = {"domain", "application", "infrastructure", "presentation", "core"}


def analyze_architecture(
    repo_path: Path,
    language: str,
    structure: StructureResult,
    claude_client=None,
) -> ArchitectureResult:
    result = ArchitectureResult()

    result.top_level_packages = _get_top_level_packages(repo_path, language)
    result.god_files = _find_god_files(repo_path)
    result.pattern_detected = _detect_pattern(repo_path, structure)

    # Build a compact structure summary for Claude
    tree = structure.tree_summary or "(no tree available)"
    summary_input = (
        f"Language: {language}\n"
        f"Top-level packages: {', '.join(result.top_level_packages) or 'none'}\n"
        f"Pattern hint: {result.pattern_detected or 'unknown'}\n"
        f"God files (>500 LOC): {len(result.god_files)}\n"
        f"Has CI: {structure.has_ci} | Has Docker: {structure.has_docker}\n\n"
        f"File structure:\n{tree}"
    )

    if claude_client is not None:
        narrative = claude_client.analyze_architecture(summary_input, language)
        if narrative:
            result.summary_text = narrative

    if not result.summary_text:
        result.summary_text = _heuristic_summary(result, structure, language)

    return result


def _get_top_level_packages(repo_path: Path, language: str) -> list[str]:
    packages = []
    try:
        for entry in sorted(repo_path.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name.startswith(".") or entry.name in {
                "node_modules", "__pycache__", ".venv", "venv", "dist", "build"
            }:
                continue
            if language == "Python" and (entry / "__init__.py").exists():
                packages.append(entry.name)
            elif language in ("JavaScript", "TypeScript") and (entry / "index.js").exists():
                packages.append(entry.name)
            else:
                packages.append(entry.name)
    except OSError:
        pass
    return packages[:10]


def _find_god_files(repo_path: Path) -> list[str]:
    god_files = []
    for dirpath, _, filenames in walk_repo(repo_path):
        for fname in filenames:
            fpath = dirpath / fname
            suffix = fpath.suffix.lower()
            if suffix not in {".py", ".js", ".ts", ".java", ".go", ".rs", ".rb", ".php", ".cs"}:
                continue
            loc = count_lines(fpath)
            if loc > _GOD_FILE_THRESHOLD:
                rel = str(fpath.relative_to(repo_path))
                god_files.append(f"{rel} ({loc} LOC)")
    return god_files[:10]


def _detect_pattern(repo_path: Path, structure: StructureResult) -> Optional[str]:
    try:
        all_dirs = {
            entry.name.lower()
            for entry in repo_path.rglob("*")
            if entry.is_dir() and not entry.name.startswith(".")
        }
    except OSError:
        return None

    if _MVC_DIRS & all_dirs:
        return "MVC"
    if _SERVICE_DIRS & all_dirs:
        return "Service-Oriented / Layered"
    if _LAYERED_DIRS & all_dirs:
        return "Clean / Hexagonal"
    if structure.has_docker and structure.has_ci:
        # docker-compose with multiple services suggests microservices
        docker_compose = repo_path / "docker-compose.yml"
        if docker_compose.exists():
            try:
                content = docker_compose.read_text(encoding="utf-8", errors="replace")
                if content.count("image:") >= 3 or content.count("build:") >= 3:
                    return "Microservices (hint)"
            except OSError:
                pass
    if structure.total_files < 15 and structure.max_depth <= 2:
        return "Script / Minimal"
    return "Modular"


def _heuristic_summary(
    result: ArchitectureResult,
    structure: StructureResult,
    language: str,
) -> str:
    pattern = result.pattern_detected or "an unidentified"
    god_note = (
        f" {len(result.god_files)} large file(s) detected (>{_GOD_FILE_THRESHOLD} LOC), "
        "which may indicate complexity concentration."
        if result.god_files
        else " No oversized files detected."
    )
    ci_note = " CI/CD configuration is present." if structure.has_ci else ""
    docker_note = " Docker support is included." if structure.has_docker else ""
    return (
        f"This {language} project follows {pattern} architectural pattern. "
        f"It has {structure.total_files} files across {structure.max_depth} directory levels."
        f"{god_note}{ci_note}{docker_note}"
    )
