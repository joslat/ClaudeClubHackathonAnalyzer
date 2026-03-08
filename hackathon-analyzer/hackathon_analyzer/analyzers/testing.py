"""Analyzer: test file discovery, framework detection, and test coverage ratio."""

import re
from pathlib import Path

from hackathon_analyzer.core.models import StructureResult, TestingResult
from hackathon_analyzer.utils.file_utils import safe_read_text, walk_repo

# Patterns: (language, file glob patterns, framework import patterns)
_TEST_PATTERNS: dict[str, dict] = {
    "Python": {
        "globs": ["test_*.py", "*_test.py"],
        "frameworks": {
            "pytest": [r"import pytest", r"from pytest"],
            "unittest": [r"import unittest", r"class.*TestCase"],
        },
    },
    "JavaScript": {
        "globs": ["*.test.js", "*.spec.js", "*.test.ts", "*.spec.ts", "*.test.jsx", "*.test.tsx"],
        "frameworks": {
            "jest": [r"from ['\"]jest['\"]", r"describe\(", r"it\(", r"test\("],
            "mocha": [r"require.*mocha", r"describe\(", r"it\("],
        },
    },
    "TypeScript": {
        "globs": ["*.test.ts", "*.spec.ts", "*.test.tsx"],
        "frameworks": {
            "jest": [r"from ['\"]jest['\"]", r"describe\(", r"it\(", r"test\("],
            "vitest": [r"from ['\"]vitest['\"]"],
        },
    },
    "Java": {
        "globs": ["*Test.java", "*Tests.java"],
        "frameworks": {
            "junit": [r"import org\.junit", r"@Test"],
            "testng": [r"import org\.testng"],
        },
    },
    "C#": {
        "globs": ["*Test.cs", "*Tests.cs", "*Spec.cs", "*Fixture.cs"],
        "frameworks": {
            "xunit": [r"using Xunit", r"\[Fact\]", r"\[Theory\]"],
            "nunit": [r"using NUnit", r"\[Test\]", r"\[TestFixture\]"],
            "mstest": [r"using Microsoft\.VisualStudio\.TestTools", r"\[TestMethod\]"],
        },
    },
    "Go": {
        "globs": ["*_test.go"],
        "frameworks": {
            "testing": [r"import.*testing", r"func Test"],
        },
    },
    "Rust": {
        "globs": ["*.rs"],
        "frameworks": {
            "cargo-test": [r"#\[test\]", r"#\[cfg\(test\)\]"],
        },
    },
    "Ruby": {
        "globs": ["*_spec.rb", "*_test.rb"],
        "frameworks": {
            "rspec": [r"require .rspec", r"describe ", r"it ."],
            "minitest": [r"require .minitest"],
        },
    },
}

_CI_TEST_KEYWORDS = re.compile(
    r"\b(pytest|jest|cargo test|go test|mvn test|npm test|yarn test|rspec|mocha|vitest"
    r"|dotnet test|xunit|nunit|mstest)\b",
    re.IGNORECASE,
)


def analyze_testing(
    repo_path: Path,
    language: str,
    structure: StructureResult,
) -> TestingResult:
    result = TestingResult()
    result.has_test_dir = structure.has_tests_dir

    test_files = _find_test_files(repo_path, language)
    result.test_files_count = len(test_files)

    if test_files:
        result.test_frameworks_detected = _detect_frameworks(test_files, language)
        result.test_loc = _count_loc(test_files)

    result.code_loc = _count_code_loc(repo_path, language, test_files)
    if result.code_loc > 0:
        result.test_to_code_ratio = round(result.test_loc / result.code_loc, 3)

    result.has_ci_test_step = _check_ci_for_tests(repo_path)
    return result


def _find_test_files(repo_path: Path, language: str) -> list[Path]:
    patterns = _TEST_PATTERNS.get(language, {}).get("globs", [])
    if not patterns:
        # Generic fallback
        patterns = ["test_*.py", "*_test.*", "*.test.*", "*.spec.*", "*Test.*", "*Tests.*"]

    found: set[Path] = set()
    for pattern in patterns:
        found.update(repo_path.rglob(pattern))

    # Filter out node_modules, .git, etc.
    ignore = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"}
    return [p for p in found if not any(part in ignore for part in p.parts)]


def _detect_frameworks(test_files: list[Path], language: str) -> list[str]:
    frameworks_patterns = _TEST_PATTERNS.get(language, {}).get("frameworks", {})
    detected: set[str] = set()

    sample = test_files[:10]  # check first 10 files
    for fpath in sample:
        content = safe_read_text(fpath, max_bytes=50_000) or ""
        for framework, patterns in frameworks_patterns.items():
            if any(re.search(p, content) for p in patterns):
                detected.add(framework)

    return list(detected)


def _count_loc(files: list[Path]) -> int:
    total = 0
    for f in files:
        try:
            total += f.read_bytes().count(b"\n")
        except OSError:
            pass
    return total


def _count_code_loc(repo_path: Path, language: str, exclude: list[Path]) -> int:
    from hackathon_analyzer.analyzers.language import _EXT_MAP

    lang_exts = {ext for ext, lang in _EXT_MAP.items() if lang == language}
    if not lang_exts:
        lang_exts = {".py", ".js", ".ts", ".java", ".go", ".rs"}

    exclude_set = set(exclude)
    total = 0
    for dirpath, _, filenames in walk_repo(repo_path):
        for fname in filenames:
            fpath = dirpath / fname
            if fpath in exclude_set:
                continue
            if Path(fname).suffix.lower() in lang_exts:
                try:
                    total += fpath.read_bytes().count(b"\n")
                except OSError:
                    pass
    return total


def _check_ci_for_tests(repo_path: Path) -> bool:
    ci_paths = list((repo_path / ".github" / "workflows").glob("*.yml"))
    ci_paths += list((repo_path / ".github" / "workflows").glob("*.yaml"))
    gitlab_ci = repo_path / ".gitlab-ci.yml"
    if gitlab_ci.exists():
        ci_paths.append(gitlab_ci)

    for ci_path in ci_paths:
        content = safe_read_text(ci_path, max_bytes=100_000) or ""
        if _CI_TEST_KEYWORDS.search(content):
            return True
    return False
