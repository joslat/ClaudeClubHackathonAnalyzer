"""Pytest fixtures for hackathon-analyzer tests."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "sample_repos"


@pytest.fixture
def python_clean_repo() -> Path:
    """Path to the minimal clean Python fixture repo."""
    return FIXTURES_DIR / "python-clean"


@pytest.fixture
def js_no_tests_repo() -> Path:
    """Path to the minimal JS fixture repo (no tests)."""
    return FIXTURES_DIR / "js-no-tests"
