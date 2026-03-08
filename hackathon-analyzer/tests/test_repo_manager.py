"""Tests for repo URL parsing and local repo detection."""

from pathlib import Path

import pytest

from hackathon_analyzer.core.repo_manager import parse_repo_url, repo_exists_locally


@pytest.mark.parametrize("url,expected_owner,expected_name,expected_slug", [
    ("https://github.com/owner/repo", "owner", "repo", "owner-repo"),
    ("https://github.com/owner/repo.git", "owner", "repo", "owner-repo"),
    ("https://github.com/owner/repo/", "owner", "repo", "owner-repo"),
    ("https://gitlab.com/mygroup/myproject", "mygroup", "myproject", "mygroup-myproject"),
])
def test_parse_repo_url(url, expected_owner, expected_name, expected_slug, tmp_path):
    meta = parse_repo_url(url, tmp_path)
    assert meta.owner == expected_owner
    assert meta.name == expected_name
    assert meta.slug == expected_slug
    assert meta.local_path == tmp_path / expected_slug


def test_parse_repo_url_invalid(tmp_path):
    with pytest.raises(ValueError):
        parse_repo_url("https://bitbucket.org/owner/repo", tmp_path)


def test_parse_repo_url_not_a_url(tmp_path):
    with pytest.raises(ValueError):
        parse_repo_url("not-a-url", tmp_path)


def test_repo_exists_locally_false(tmp_path):
    from hackathon_analyzer.core.models import RepoMeta
    meta = RepoMeta(
        url="https://github.com/x/y",
        owner="x", name="y", slug="x-y",
        local_path=tmp_path / "x-y",
    )
    assert not repo_exists_locally(meta)


def test_repo_exists_locally_true(tmp_path):
    from hackathon_analyzer.core.models import RepoMeta
    repo_dir = tmp_path / "x-y"
    (repo_dir / ".git").mkdir(parents=True)
    meta = RepoMeta(
        url="https://github.com/x/y",
        owner="x", name="y", slug="x-y",
        local_path=repo_dir,
    )
    assert repo_exists_locally(meta)
