"""Bridge between the chat agent and the hackathon-analyzer CLI.

Calls `hackanalyze` via subprocess and reads generated report files.
This file is the single point of change when the analyzer evolves.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Config ────────────────────────────────────────────────────────────────────

def _hackanalyze_bin() -> str:
    """Return path to the hackanalyze binary.

    Resolution order:
    1. HACKANALYZE_PATH env var (explicit override)
    2. 'hackanalyze' on system PATH (normal after `pip install -e .`)
    3. `python -m hackathon_analyzer.cli` via the sibling project directory
    """
    # 1. Explicit override
    explicit = os.getenv("HACKANALYZE_PATH")
    if explicit:
        return explicit

    # 2. Check if 'hackanalyze' is available on PATH
    import shutil
    if shutil.which("hackanalyze"):
        return "hackanalyze"

    # 3. Fall back to running the module directly from the sibling project.
    #    This works even when the package is not installed system-wide.
    sibling = Path(__file__).parent.parent.parent / "hackathon-analyzer"
    if sibling.exists():
        import sys
        # Return a synthetic command list marker — _run_hackanalyze handles this.
        return f"__module__:{sibling}"

    return "hackanalyze"  # last resort — will fail with a clear error


def _analyzer_project_dir() -> Path:
    """Return the hackathon-analyzer project root directory."""
    return Path(__file__).resolve().parent.parent.parent / "hackathon-analyzer"


def _reports_dir() -> Path:
    """Return the reports directory used by the analyzer."""
    env = os.getenv("HACKANALYZE_REPORTS_DIR")
    if env:
        return Path(env)
    return _analyzer_project_dir() / "reports"


# ── Core runner ───────────────────────────────────────────────────────────────

def _run_hackanalyze(args: list[str], timeout: int = 600) -> tuple[bool, str]:
    """Run hackanalyze with the given args. Returns (success, output_text)."""
    import sys
    bin_or_marker = _hackanalyze_bin()

    if bin_or_marker.startswith("__module__:"):
        # Fall back to `python -m hackathon_analyzer.cli` from the sibling project
        project_dir = bin_or_marker[len("__module__:"):]
        cmd = [sys.executable, "-m", "hackathon_analyzer.cli"] + args
        env = {**os.environ, "PYTHONPATH": project_dir}
    else:
        cmd = [bin_or_marker] + args
        env = None
    try:
        run_env = env or dict(os.environ)
        # Ensure UTF-8 mode on Windows to avoid encoding crashes
        run_env["PYTHONUTF8"] = "1"
        # Always run from the analyzer project dir so repos/ and reports/
        # are created there, not in whatever CWD the chat app launched from.
        cwd = str(_analyzer_project_dir())
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=run_env,
            cwd=cwd,
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        combined = stdout + ("\n" + stderr if stderr else "")
        return result.returncode == 0, combined.strip()
    except FileNotFoundError:
        return False, (
            f"hackanalyze not found. Make sure it is installed and on PATH "
            f"(or set HACKANALYZE_PATH). Binary tried: {cmd[0]}"
        )
    except subprocess.TimeoutExpired:
        return False, f"hackanalyze timed out after {timeout}s."
    except Exception as exc:
        return False, f"Unexpected error running hackanalyze: {exc}"


# ── Report parsing ─────────────────────────────────────────────────────────────

def _slug_from_url(url: str) -> str:
    """Convert a GitHub URL to the report slug used by hackanalyze."""
    # https://github.com/owner/repo -> owner-repo
    url = url.rstrip("/")
    parts = url.split("/")
    if len(parts) >= 2:
        return f"{parts[-2]}-{parts[-1]}"
    return parts[-1]


def _find_report(slug: str) -> Path | None:
    """Find the per-repo report file for a given slug."""
    per_repo = _reports_dir() / "per-repo"
    if not per_repo.exists():
        return None
    # Exact match first
    exact = per_repo / f"{slug}-report.md"
    if exact.exists():
        return exact
    # Fuzzy: any file containing the slug
    for f in per_repo.glob("*.md"):
        if slug in f.name:
            return f
    return None


def _parse_score_from_report(text: str) -> float | None:
    """Extract total score from markdown report text."""
    # Look for patterns like "**Total Score**: 7.4" or "Total Score: 7.4/10"
    patterns = [
        r"(?i)total\s+score[:\s*|]+([0-9]+\.?[0-9]*)",
        r"(?i)\*\*score\*\*[:\s]+([0-9]+\.?[0-9]*)",
        r"(?i)final\s+score[:\s*|]+([0-9]+\.?[0-9]*)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            try:
                return float(m.group(1))
            except ValueError as exc:
                logger.debug("Could not parse score from '%s': %s", m.group(1), exc)
    return None


def _parse_dimensions_from_report(text: str) -> list[dict]:
    """Extract dimension scores from markdown report table."""
    dimensions = []
    # Look for table rows matching dimension data
    # Expected format: | Dimension | Weight | Score | Rationale |
    table_pattern = r"\|\s*([^|]+?)\s*\|\s*([0-9.%]+)\s*\|\s*([0-9.]+)\s*\|\s*([^|]*?)\s*\|"
    for m in re.finditer(table_pattern, text):
        name, weight, score, rationale = m.groups()
        name = name.strip()
        # Skip header rows
        if name.lower() in ("dimension", "---", "name"):
            continue
        try:
            dimensions.append({
                "name": name,
                "weight": weight.strip(),
                "score": float(score),
                "rationale": rationale.strip(),
            })
        except ValueError as exc:
            logger.debug("Could not parse dimension score for '%s': %s", name, exc)
    return dimensions


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_repo(
    url: str,
    skip_build: bool = False,
    skip_plagiarism: bool = False,
) -> dict:
    """Analyze a single repo. Returns a result dict."""
    args = ["analyze", url]
    if skip_build:
        args.append("--skip-build")
    if skip_plagiarism:
        args.append("--skip-plagiarism")

    success, output = _run_hackanalyze(args)
    slug = _slug_from_url(url)
    result: dict = {
        "url": url,
        "slug": slug,
        "success": success,
        "cli_output": output,
        "report_text": None,
        "total_score": None,
        "dimensions": [],
    }

    if success:
        report_path = _find_report(slug)
        if report_path:
            result["report_path"] = str(report_path)
            text = report_path.read_text(encoding="utf-8", errors="replace")
            result["report_text"] = text
            result["total_score"] = _parse_score_from_report(text)
            result["dimensions"] = _parse_dimensions_from_report(text)
        # Auto-update the summary after each analysis
        generate_summary()

    return result


def batch_analyze(
    urls: list[str],
    skip_build: bool = False,
    skip_plagiarism: bool = False,
) -> dict:
    """Analyze multiple repos at once."""
    args = ["analyze"] + urls
    if skip_build:
        args.append("--skip-build")
    if skip_plagiarism:
        args.append("--skip-plagiarism")

    success, output = _run_hackanalyze(args)
    results = []
    for url in urls:
        slug = _slug_from_url(url)
        r: dict = {"url": url, "slug": slug, "success": success, "total_score": None, "dimensions": []}
        if success:
            report_path = _find_report(slug)
            if report_path:
                r["report_path"] = str(report_path)
                text = report_path.read_text(encoding="utf-8", errors="replace")
                r["report_text"] = text
                r["total_score"] = _parse_score_from_report(text)
                r["dimensions"] = _parse_dimensions_from_report(text)
        results.append(r)

    # Auto-generate summary after batch analysis
    summary_result = generate_summary()
    summary_path = summary_result.get("summary_path")

    return {
        "success": success,
        "cli_output": output,
        "results": results,
        "summary_report_path": summary_path,
        "summary_text": summary_result.get("summary_text"),
    }


def list_reports() -> dict:
    """List all existing per-repo and summary reports."""
    reports_root = _reports_dir()
    per_repo: list[dict] = []
    summaries: list[dict] = []

    per_repo_dir = reports_root / "per-repo"
    if per_repo_dir.exists():
        for f in sorted(per_repo_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            slug = f.stem.replace("-report", "")
            per_repo.append({
                "slug": slug,
                "path": str(f),
                "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            })

    summary_dir = reports_root / "summary"
    if summary_dir.exists():
        for f in sorted(summary_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            summaries.append({
                "name": f.name,
                "path": str(f),
                "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            })

    return {
        "reports_dir": str(reports_root),
        "per_repo": per_repo,
        "summaries": summaries,
        "total": len(per_repo) + len(summaries),
    }


def read_report(slug: str) -> dict:
    """Read a specific report by slug."""
    # Try per-repo first
    report_path = _find_report(slug)
    if report_path:
        text = report_path.read_text(encoding="utf-8", errors="replace")
        return {
            "found": True,
            "slug": slug,
            "path": str(report_path),
            "text": text,
            "total_score": _parse_score_from_report(text),
            "dimensions": _parse_dimensions_from_report(text),
        }

    # Try summary reports
    summary_dir = _reports_dir() / "summary"
    if summary_dir.exists():
        for f in summary_dir.glob("*.md"):
            if slug in f.name:
                text = f.read_text(encoding="utf-8", errors="replace")
                return {"found": True, "slug": slug, "path": str(f), "text": text}

    return {"found": False, "slug": slug, "error": f"No report found for '{slug}'."}


def generate_summary() -> dict:
    """Run hackanalyze summarize to build/update the summary report."""
    success, output = _run_hackanalyze(["summarize", "-r", str(_reports_dir())])
    result: dict = {"success": success, "cli_output": output}
    summary_path = _reports_dir() / "summary" / "summary.md"
    if summary_path.exists():
        text = summary_path.read_text(encoding="utf-8", errors="replace")
        result["summary_text"] = text
        result["summary_path"] = str(summary_path)
    return result


def clean_repos() -> dict:
    """Run hackanalyze clean to delete cloned repos."""
    success, output = _run_hackanalyze(["clean"])
    return {"success": success, "output": output}
