"""Tests for the structure analyzer."""

from hackathon_analyzer.analyzers.structure import analyze_structure


def test_structure_python_clean(python_clean_repo):
    result = analyze_structure(python_clean_repo)
    assert result.total_files > 0
    assert result.has_tests_dir


def test_structure_js_no_tests(js_no_tests_repo):
    result = analyze_structure(js_no_tests_repo)
    assert result.total_files >= 2  # package.json + index.js
    assert not result.has_tests_dir


def test_structure_max_depth(python_clean_repo):
    result = analyze_structure(python_clean_repo)
    assert result.max_depth >= 1  # has at least myapp/ subdir


def test_structure_extension_count(js_no_tests_repo):
    result = analyze_structure(js_no_tests_repo)
    assert ".js" in result.file_extensions
    assert result.file_extensions[".js"] >= 1


def test_structure_tree_summary_not_empty(python_clean_repo):
    result = analyze_structure(python_clean_repo)
    assert len(result.tree_summary) > 0
