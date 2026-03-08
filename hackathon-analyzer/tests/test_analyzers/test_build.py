"""Tests for the build analyzer."""

from hackathon_analyzer.analyzers.build import detect_build_system


def test_detect_pip(python_clean_repo):
    result = detect_build_system(python_clean_repo)
    assert result.build_system == "pip"
    assert "requirements.txt" in result.build_files_found


def test_detect_npm(js_no_tests_repo):
    result = detect_build_system(js_no_tests_repo)
    assert result.build_system == "npm"
    assert "package.json" in result.build_files_found


def test_no_build_system(tmp_path):
    """An empty directory should have no build system."""
    result = detect_build_system(tmp_path)
    assert result.build_system is None
    assert result.build_files_found == []
