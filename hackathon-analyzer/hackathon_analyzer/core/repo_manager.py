"""Repo cloning, updating, URL parsing, and cleanup."""

import re
import subprocess
from pathlib import Path
from typing import Optional

from hackathon_analyzer.config import Config
from hackathon_analyzer.core.models import RepoMeta
from hackathon_analyzer.utils.subprocess_runner import run_with_timeout

# Supported URL patterns
_GITHUB_PATTERN = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<name>[^/\s]+?)(?:\.git)?/?$"
)
_GITLAB_PATTERN = re.compile(
    r"https?://gitlab\.com/(?P<owner>[^/]+)/(?P<name>[^/\s]+?)(?:\.git)?/?$"
)


def parse_repo_url(url: str, repos_dir: Path) -> RepoMeta:
    """Parse a GitHub or GitLab URL into a RepoMeta.

    Raises ValueError for unsupported URL formats.
    """
    url = url.strip().rstrip("/")
    for pattern in [_GITHUB_PATTERN, _GITLAB_PATTERN]:
        m = pattern.match(url)
        if m:
            owner = m.group("owner")
            name = m.group("name").removesuffix(".git")
            slug = f"{owner}-{name}"
            return RepoMeta(
                url=url,
                owner=owner,
                name=name,
                slug=slug,
                local_path=repos_dir / slug,
            )
    raise ValueError(
        f"Unsupported repo URL: {url!r}. "
        "Only github.com and gitlab.com URLs are supported."
    )


def repo_exists_locally(meta: RepoMeta) -> bool:
    """Return True if the local path already contains a valid git repo."""
    return (meta.local_path / ".git").is_dir()


def clone_repo(meta: RepoMeta, config: Config) -> RepoMeta:
    """Clone a repo to meta.local_path. Returns updated RepoMeta."""
    meta.local_path.parent.mkdir(parents=True, exist_ok=True)

    result = run_with_timeout(
        cmd=["git", "clone", "--depth", "1", meta.url, meta.local_path.name],
        cwd=meta.local_path.parent,
        timeout=config.clone_timeout_seconds,
    )

    if result.succeeded:
        meta.clone_success = True
    else:
        meta.clone_success = False
        meta.clone_error = result.stderr[:500] or "Unknown clone error"

    return meta


def update_repo(meta: RepoMeta, config: Config) -> None:
    """Run git pull on an existing clone."""
    run_with_timeout(
        cmd=["git", "pull", "--ff-only"],
        cwd=meta.local_path,
        timeout=config.clone_timeout_seconds,
    )


def cleanup_repo(meta: RepoMeta) -> None:
    """Delete the local clone directory."""
    import shutil

    if meta.local_path.exists():
        shutil.rmtree(meta.local_path, ignore_errors=True)


def get_repo_size_mb_from_api(owner: str, name: str, token: str) -> Optional[float]:
    """Fetch repo size in MB from GitHub API (size field is in KB)."""
    try:
        import requests

        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        resp = requests.get(
            f"https://api.github.com/repos/{owner}/{name}",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            size_kb = resp.json().get("size", 0)
            return size_kb / 1024
    except Exception:
        pass
    return None
