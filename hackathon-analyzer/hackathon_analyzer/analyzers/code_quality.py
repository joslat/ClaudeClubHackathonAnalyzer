"""Analyzer: code quality via flake8, radon, bandit (Python); heuristics for others."""

import json
import re
from pathlib import Path
from typing import Optional

from hackathon_analyzer.core.models import CodeQualityResult
from hackathon_analyzer.utils.subprocess_runner import run_with_timeout, tool_available


def analyze_code_quality(repo_path: Path, language: str) -> CodeQualityResult:
    result = CodeQualityResult(language=language)

    if language == "Python":
        result = _analyze_python(repo_path, result)
    else:
        result = _heuristic_analysis(repo_path, result)

    result.complexity_score = _compute_complexity_score(
        result.cyclomatic_complexity_avg, result.linter_issues
    )
    return result


def _analyze_python(repo_path: Path, result: CodeQualityResult) -> CodeQualityResult:
    # Flake8
    if tool_available("flake8"):
        r = run_with_timeout(
            ["flake8", ".", "--count", "--statistics", "--exit-zero", "--max-line-length=120"],
            cwd=repo_path,
            timeout=60,
        )
        result.linter_tool = "flake8"
        result.linter_issues = _parse_flake8_count(r.stdout + r.stderr)

    # Radon cyclomatic complexity
    if tool_available("radon"):
        r = run_with_timeout(
            ["radon", "cc", ".", "-a", "-s", "--min", "A"],
            cwd=repo_path,
            timeout=60,
        )
        result.cyclomatic_complexity_avg = _parse_radon_cc(r.stdout)

        r = run_with_timeout(
            ["radon", "mi", ".", "-s"],
            cwd=repo_path,
            timeout=60,
        )
        result.maintainability_index_avg = _parse_radon_mi(r.stdout)

    # Bandit security scanner
    if tool_available("bandit"):
        r = run_with_timeout(
            ["bandit", "-r", ".", "-f", "json", "-q", "--exit-zero"],
            cwd=repo_path,
            timeout=60,
        )
        _parse_bandit(r.stdout, result)

    return result


def _heuristic_analysis(repo_path: Path, result: CodeQualityResult) -> CodeQualityResult:
    """For non-Python repos: estimate quality from average file size."""
    from hackathon_analyzer.utils.file_utils import walk_repo

    total_lines = 0
    file_count = 0
    large_files = 0

    code_exts = {
        ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
        ".rb", ".php", ".cs", ".cpp", ".c", ".swift",
    }
    for dirpath, _, filenames in walk_repo(repo_path):
        for fname in filenames:
            if Path(fname).suffix.lower() in code_exts:
                fpath = dirpath / fname
                try:
                    lines = fpath.read_bytes().count(b"\n")
                    total_lines += lines
                    file_count += 1
                    if lines > 500:
                        large_files += 1
                except OSError:
                    pass

    result.linter_tool = "heuristic"
    if file_count > 0:
        avg_lines = total_lines / file_count
        result.linter_issues = large_files  # proxy: large files = issues
        result.cyclomatic_complexity_avg = max(1.0, avg_lines / 50)  # rough proxy
    return result


def _parse_flake8_count(output: str) -> int:
    lines = output.strip().splitlines()
    for line in reversed(lines):
        line = line.strip()
        if line.isdigit():
            return int(line)
    # Try to count lines that look like errors (file:line:col: Exxxx)
    count = sum(1 for l in lines if re.match(r".+:\d+:\d+:", l))
    return count


def _parse_radon_cc(output: str) -> Optional[float]:
    # "Average complexity: A (2.5)"
    m = re.search(r"Average complexity:\s+\w+\s+\(([0-9.]+)\)", output)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _parse_radon_mi(output: str) -> Optional[float]:
    scores = re.findall(r"\s+([0-9.]+)\s*$", output, re.MULTILINE)
    if scores:
        try:
            values = [float(s) for s in scores]
            return sum(values) / len(values)
        except ValueError:
            pass
    return None


def _parse_bandit(output: str, result: CodeQualityResult) -> None:
    try:
        data = json.loads(output)
        metrics = data.get("metrics", {}).get("_totals", {})
        result.security_issues_high = metrics.get("SEVERITY.HIGH", 0)
        result.security_issues_medium = metrics.get("SEVERITY.MEDIUM", 0)
        result.security_issues_low = metrics.get("SEVERITY.LOW", 0)
    except (json.JSONDecodeError, AttributeError):
        pass


def _compute_complexity_score(cc_avg: Optional[float], linter_issues: int) -> float:
    cc_score = 1.0
    if cc_avg is not None:
        if cc_avg <= 5:
            cc_score = 1.0
        elif cc_avg <= 10:
            cc_score = 0.7
        elif cc_avg <= 15:
            cc_score = 0.4
        else:
            cc_score = 0.2

    linter_score = 1.0
    if linter_issues > 100:
        linter_score = 0.1
    elif linter_issues > 50:
        linter_score = 0.3
    elif linter_issues > 10:
        linter_score = 0.5
    elif linter_issues > 0:
        linter_score = 0.8

    return round((cc_score * 0.6 + linter_score * 0.4), 3)
