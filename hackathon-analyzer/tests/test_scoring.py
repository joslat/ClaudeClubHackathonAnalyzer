"""Tests for scoring logic."""

from hackathon_analyzer.core.models import (
    BuildResult,
    CodeQualityResult,
    DocumentationResult,
    LanguageResult,
    OriginalityResult,
    RepoAnalysisResult,
    RepoMeta,
    StructureResult,
    TestingResult,
    ArchitectureResult,
)
from hackathon_analyzer.scoring.scorer import compute_score
from pathlib import Path


def _make_meta() -> RepoMeta:
    return RepoMeta(
        url="https://github.com/test/repo",
        owner="test",
        name="repo",
        slug="test-repo",
        local_path=Path("/tmp/test-repo"),
    )


def test_score_range_minimum():
    """An empty result should score >= 1.0."""
    result = RepoAnalysisResult(meta=_make_meta())
    score, dims = compute_score(result)
    assert 1.0 <= score <= 10.0


def test_score_range_maximum():
    """A perfect result should score close to 10.0."""
    result = RepoAnalysisResult(
        meta=_make_meta(),
        documentation=DocumentationResult(
            has_readme=True, readme_word_count=500,
            readme_has_usage_section=True, readme_has_installation_section=True,
            readme_has_badges=True, has_license=True, has_changelog=True,
            has_docs_dir=True, has_api_docs=True, doc_score=1.0,
        ),
        code_quality=CodeQualityResult(
            language="Python", linter_issues=0, linter_tool="flake8",
            cyclomatic_complexity_avg=2.0, maintainability_index_avg=90.0,
            security_issues_high=0, security_issues_medium=0, security_issues_low=0,
            complexity_score=1.0,
        ),
        testing=TestingResult(
            has_test_dir=True, test_files_count=20,
            test_frameworks_detected=["pytest"],
            test_loc=500, code_loc=1000, test_to_code_ratio=0.5,
            has_ci_test_step=True,
        ),
        build=BuildResult(
            build_system="pip", build_attempted=True, build_succeeded=True,
            build_duration_seconds=5.0,
        ),
        structure=StructureResult(
            has_src_layout=True, has_tests_dir=True, has_ci=True, has_docker=True,
            max_depth=3, total_files=50, layout_patterns=["src-layout"],
        ),
        architecture=ArchitectureResult(
            pattern_detected="MVC", top_level_packages=["src", "tests"],
            god_files=[], summary_text="Clean MVC architecture.",
        ),
        originality=OriginalityResult(
            snippets_checked=5, matches_found=[],
            similarity_score=0.0, plagiarism_risk="low",
            claude_verdict="RISK: LOW",
        ),
        language=LanguageResult(primary_language="Python", total_loc=1000),
    )
    score, dims = compute_score(result)
    assert score >= 8.0  # Near-perfect should be high


def test_build_no_system_scores_neutral():
    result = RepoAnalysisResult(
        meta=_make_meta(),
        build=BuildResult(build_system=None),
    )
    score, dims = compute_score(result)
    build_dim = next(d for d in dims if d.name == "build_success")
    assert build_dim.raw_score == 0.3  # neutral score for no build system


def test_build_success_scores_full():
    result = RepoAnalysisResult(
        meta=_make_meta(),
        build=BuildResult(
            build_system="npm", build_attempted=True, build_succeeded=True,
        ),
    )
    score, dims = compute_score(result)
    build_dim = next(d for d in dims if d.name == "build_success")
    assert build_dim.raw_score == 1.0


def test_high_plagiarism_risk_lowers_originality():
    result = RepoAnalysisResult(
        meta=_make_meta(),
        originality=OriginalityResult(
            snippets_checked=5, matches_found=[],
            similarity_score=0.8, plagiarism_risk="high",
            claude_verdict="RISK: HIGH",
        ),
    )
    score, dims = compute_score(result)
    orig_dim = next(d for d in dims if d.name == "originality")
    assert orig_dim.raw_score <= 0.15


def test_dimension_scores_sum_correctly():
    result = RepoAnalysisResult(meta=_make_meta())
    total, dims = compute_score(result)
    weighted_sum = sum(d.weighted_score for d in dims)
    expected = round(1.0 + (weighted_sum * 9.0), 1)
    assert abs(total - expected) < 0.05


def test_weights_sum_to_one():
    from hackathon_analyzer.scoring.rubric import DIMENSIONS
    total_weight = sum(d.weight for d in DIMENSIONS)
    assert abs(total_weight - 1.0) < 1e-9
