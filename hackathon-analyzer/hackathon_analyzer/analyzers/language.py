"""Analyzer: programming language detection using pygments + extension mapping."""

import json
from pathlib import Path

from hackathon_analyzer.core.models import LanguageResult
from hackathon_analyzer.utils.file_utils import walk_repo
from hackathon_analyzer.utils.subprocess_runner import run_with_timeout, tool_available

# Extension → canonical language name
_EXT_MAP: dict[str, str] = {
    ".py": "Python", ".pyw": "Python",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".java": "Java",
    ".kt": "Kotlin", ".kts": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++",
    ".c": "C", ".h": "C",
    ".swift": "Swift",
    ".r": "R", ".rmd": "R",
    ".scala": "Scala",
    ".ex": "Elixir", ".exs": "Elixir",
    ".hs": "Haskell",
    ".lua": "Lua",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".html": "HTML", ".htm": "HTML",
    ".css": "CSS", ".scss": "CSS", ".sass": "CSS",
    ".sql": "SQL",
    ".dart": "Dart",
}

# Directories to ignore when counting LOC
_IGNORE_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"}


def detect_languages(repo_path: Path) -> LanguageResult:
    """Detect languages, trying cloc first then falling back to extension counting."""
    result = _try_cloc(repo_path)
    if result:
        return result
    return _detect_by_extension(repo_path)


def _try_cloc(repo_path: Path) -> LanguageResult | None:
    """Run cloc and parse its JSON output."""
    if not tool_available("cloc"):
        return None
    res = run_with_timeout(
        ["cloc", "--json", "--quiet", str(repo_path)],
        cwd=repo_path,
        timeout=60,
    )
    if not res.succeeded:
        return None
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        return None

    loc_by_lang: dict[str, int] = {}
    for lang, info in data.items():
        if lang in ("header", "SUM"):
            continue
        loc_by_lang[lang] = info.get("code", 0)

    if not loc_by_lang:
        return None

    total = sum(loc_by_lang.values())
    primary = max(loc_by_lang, key=lambda k: loc_by_lang[k])
    breakdown = {k: round(v / total * 100, 1) for k, v in loc_by_lang.items()}

    return LanguageResult(
        primary_language=primary,
        language_breakdown=breakdown,
        detection_method="cloc",
        loc_by_language=loc_by_lang,
        total_loc=total,
    )


def _detect_by_extension(repo_path: Path) -> LanguageResult:
    """Fall back to counting source lines by file extension."""
    lang_loc: dict[str, int] = {}

    for dirpath, _, filenames in walk_repo(repo_path):
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            lang = _EXT_MAP.get(ext)
            if lang is None:
                continue
            fpath = dirpath / fname
            try:
                lines = fpath.read_bytes().count(b"\n")
            except OSError:
                lines = 0
            lang_loc[lang] = lang_loc.get(lang, 0) + lines

    if not lang_loc:
        return LanguageResult(detection_method="extension")

    total = sum(lang_loc.values())
    primary = max(lang_loc, key=lambda k: lang_loc[k])
    breakdown = {k: round(v / total * 100, 1) for k, v in lang_loc.items()}

    return LanguageResult(
        primary_language=primary,
        language_breakdown=breakdown,
        detection_method="extension",
        loc_by_language=lang_loc,
        total_loc=total,
    )
