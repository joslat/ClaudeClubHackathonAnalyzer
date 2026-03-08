"""Analyzer: Hackathon Freshness — detect whether the repo was created during a hackathon window.

Uses git log timestamps to determine repo age and commit spread.
Optionally uses a configured hackathon_start_date for calendar comparison.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from hackathon_analyzer.core.models import HackathonFreshnessResult
from hackathon_analyzer.utils.subprocess_runner import run_with_timeout


def analyze_hackathon_freshness(
    repo_path: Path,
    hackathon_start_date: str = "",
) -> HackathonFreshnessResult:
    """Assess whether this repo was freshly created for a hackathon."""
    result = HackathonFreshnessResult()

    # 0. Unshallow the clone so we have full commit history
    _unshallow_if_needed(repo_path)

    # 1. Get first commit date
    first_commit = _get_first_commit_date(repo_path)
    if first_commit:
        result.first_commit_date = first_commit.isoformat()

    # 2. Get last commit date
    last_commit = _get_last_commit_date(repo_path)
    if last_commit:
        result.last_commit_date = last_commit.isoformat()

    # 3. Count total commits
    result.total_commits = _count_commits(repo_path)

    # 4. Calculate commit span
    if first_commit and last_commit:
        span = (last_commit - first_commit).days
        result.commit_span_days = max(0, span)
    else:
        result.commit_span_days = 0

    # Use first_commit as repo_created_at (best available from git)
    if first_commit:
        result.repo_created_at = first_commit.isoformat()

    # 5. Score freshness
    if first_commit is None:
        result.freshness_score = 0.5
        result.freshness_flag = "unknown"
        result.flag_reason = "Could not determine commit history."
        return result

    # Check against hackathon start date if configured
    if hackathon_start_date:
        result.freshness_score, result.freshness_flag, result.flag_reason = (
            _score_with_hackathon_date(first_commit, last_commit, hackathon_start_date)
        )
    else:
        # Score based on commit span and recency
        result.freshness_score, result.freshness_flag, result.flag_reason = (
            _score_by_span(first_commit, last_commit, result.commit_span_days, result.total_commits)
        )

    return result


def _unshallow_if_needed(repo_path: Path) -> None:
    """Fetch full commit history if the repo is a shallow clone."""
    # Check if shallow
    shallow_file = repo_path / ".git" / "shallow"
    if not shallow_file.exists():
        return  # already full clone
    # Unshallow to get complete history for freshness analysis
    run_with_timeout(
        ["git", "fetch", "--unshallow"],
        cwd=repo_path,
        timeout=120,
    )


def _get_first_commit_date(repo_path: Path) -> Optional[datetime]:
    """Get the date of the first commit via git log --reverse."""
    res = run_with_timeout(
        ["git", "log", "--format=%aI", "--reverse"],
        cwd=repo_path,
        timeout=30,
    )
    if not res.succeeded or not res.stdout.strip():
        return None
    first_line = res.stdout.strip().splitlines()[0]
    return _parse_iso_date(first_line)


def _get_last_commit_date(repo_path: Path) -> Optional[datetime]:
    """Get the date of the most recent commit."""
    res = run_with_timeout(
        ["git", "log", "-1", "--format=%aI"],
        cwd=repo_path,
        timeout=15,
    )
    if not res.succeeded or not res.stdout.strip():
        return None
    return _parse_iso_date(res.stdout.strip())


def _count_commits(repo_path: Path) -> int:
    """Count total commits in the repository."""
    res = run_with_timeout(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=repo_path,
        timeout=15,
    )
    if not res.succeeded or not res.stdout.strip():
        return 0
    try:
        return int(res.stdout.strip())
    except ValueError:
        return 0


def _parse_iso_date(date_str: str) -> Optional[datetime]:
    """Parse an ISO 8601 date string from git."""
    date_str = date_str.strip()
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def _score_with_hackathon_date(
    first_commit: datetime,
    last_commit: Optional[datetime],
    hackathon_start_date: str,
) -> tuple[float, str, str]:
    """Score against a known hackathon start date."""
    try:
        hack_start = datetime.fromisoformat(hackathon_start_date)
        if hack_start.tzinfo is None:
            hack_start = hack_start.replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.5, "unknown", f"Invalid hackathon_start_date: {hackathon_start_date}"

    # Ensure first_commit is timezone-aware
    fc = first_commit
    if fc.tzinfo is None:
        fc = fc.replace(tzinfo=timezone.utc)

    days_before = (hack_start - fc).days

    if days_before <= 0:
        # First commit is ON or AFTER hackathon start → fresh
        return 1.0, "fresh", f"First commit after hackathon start ({hackathon_start_date})"
    elif days_before <= 3:
        return 0.9, "fresh", f"First commit {days_before}d before hackathon (likely setup)"
    elif days_before <= 7:
        return 0.7, "fresh", f"First commit {days_before}d before hackathon (recent prep)"
    elif days_before <= 30:
        return 0.4, "old", f"First commit {days_before}d before hackathon — pre-existing project?"
    else:
        return 0.2, "old", f"First commit {days_before}d before hackathon — likely pre-built"


def _score_by_span(
    first_commit: datetime,
    last_commit: Optional[datetime],
    span_days: int,
    total_commits: int,
) -> tuple[float, str, str]:
    """Score based on commit span when no hackathon date is configured."""
    if span_days <= 3:
        return 1.0, "fresh", f"All commits within {span_days}d — hackathon-fresh"
    elif span_days <= 7:
        return 0.8, "fresh", f"Commit span: {span_days}d — likely hackathon project"
    elif span_days <= 14:
        return 0.6, "fresh", f"Commit span: {span_days}d — short project"
    elif span_days <= 30:
        return 0.4, "old", f"Commit span: {span_days}d — may be pre-existing"
    elif span_days <= 90:
        return 0.25, "old", f"Commit span: {span_days}d ({total_commits} commits) — likely pre-built"
    else:
        return 0.15, "old", f"Commit span: {span_days}d ({total_commits} commits) — established project"
