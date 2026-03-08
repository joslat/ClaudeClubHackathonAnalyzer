"""Pipeline: orchestrates all analysis steps with error recovery per step."""

import time
from pathlib import Path
from typing import Optional

from hackathon_analyzer.config import Config
from hackathon_analyzer.core.models import RepoAnalysisResult, RepoMeta
from hackathon_analyzer.reporting import terminal


def run_pipeline(
    meta: RepoMeta,
    config: Config,
    skip_build: bool = False,
    skip_plagiarism: bool = False,
    github_client=None,
    claude_client=None,
) -> RepoAnalysisResult:
    """Run the full analysis pipeline for one repository.

    Each step is individually try/excepted — failures are recorded in
    result.errors and do not abort subsequent steps.
    """
    start_time = time.monotonic()
    result = RepoAnalysisResult(meta=meta)

    terminal.print_analysis_start(meta)

    # Step 1: Clone / Update
    _step_clone(meta, config, result)
    if not meta.clone_success:
        result.errors.append(f"Clone failed: {meta.clone_error}")
        result.analysis_duration_seconds = time.monotonic() - start_time
        return result

    # Step 2: Structure
    _step(result, "Structure analysis", lambda: _run_structure(meta.local_path, result))

    # Step 3: Language detection
    _step(result, "Language detection", lambda: _run_language(meta.local_path, result))

    # Step 4: Documentation
    _step(result, "Documentation analysis", lambda: _run_documentation(meta.local_path, result))

    # Step 5: Build
    if not skip_build:
        _step(result, "Build detection", lambda: _run_build(meta.local_path, config, result))
    else:
        terminal.print_step_warn("Build", "skipped (--skip-build)")

    # Step 6: Code quality
    lang = result.language.primary_language if result.language else "Unknown"
    _step(result, "Code quality", lambda: _run_code_quality(meta.local_path, lang, result))

    # Step 7: Testing
    _step(result, "Test analysis", lambda: _run_testing(meta.local_path, lang, result))

    # Step 8: Architecture
    _step(result, "Architecture", lambda: _run_architecture(meta.local_path, lang, result, claude_client))

    # Step 9: Originality
    if not skip_plagiarism:
        _step(result, "Originality check", lambda: _run_originality(
            meta.local_path, meta, lang, result, github_client, claude_client
        ))
    else:
        terminal.print_step_warn("Originality", "skipped (--skip-plagiarism)")

    # Step 10: Promise vs Reality
    _step(result, "Promise–Reality", lambda: _run_promise_reality(
        meta.local_path, result, claude_client
    ))

    # Step 11: Vision Ambition
    _step(result, "Vision Ambition", lambda: _run_vision_ambition(
        meta.local_path, result, claude_client
    ))

    # Step 12: Tech Stack Novelty
    _step(result, "Tech Stack Novelty", lambda: _run_tech_stack_novelty(
        meta.local_path, result
    ))

    # Step 13: Hackathon Freshness
    _step(result, "Hackathon Freshness", lambda: _run_hackathon_freshness(
        meta.local_path, config, result
    ))

    # Step 14: AI Integration Depth
    _step(result, "AI Integration", lambda: _run_ai_integration(
        meta.local_path, result
    ))

    # Step 15: Scoring
    _step(result, "Scoring", lambda: _run_scoring(result))

    result.analysis_duration_seconds = round(time.monotonic() - start_time, 2)
    terminal.print_score_summary(result)
    return result


def _step(result: RepoAnalysisResult, name: str, fn) -> None:
    try:
        fn()
        terminal.print_step_done(name)
    except Exception as e:
        result.errors.append(f"{name}: {e}")
        terminal.print_step_error(name, str(e)[:100])


def _step_clone(meta: RepoMeta, config: Config, result: RepoAnalysisResult) -> None:
    from hackathon_analyzer.core import repo_manager

    try:
        if repo_manager.repo_exists_locally(meta):
            terminal.print_step_done("Repository", "already cloned — updating")
            repo_manager.update_repo(meta, config)
            meta.clone_success = True
        else:
            terminal.print_step("Cloning repository...")
            updated = repo_manager.clone_repo(meta, config)
            meta.clone_success = updated.clone_success
            meta.clone_error = updated.clone_error
            if meta.clone_success:
                terminal.print_step_done("Clone", str(meta.local_path))
            else:
                terminal.print_step_error("Clone", meta.clone_error or "")
    except Exception as e:
        meta.clone_success = False
        meta.clone_error = str(e)
        terminal.print_step_error("Clone", str(e))


def _run_structure(repo_path: Path, result: RepoAnalysisResult) -> None:
    from hackathon_analyzer.analyzers.structure import analyze_structure
    result.structure = analyze_structure(repo_path)


def _run_language(repo_path: Path, result: RepoAnalysisResult) -> None:
    from hackathon_analyzer.analyzers.language import detect_languages
    result.language = detect_languages(repo_path)


def _run_documentation(repo_path: Path, result: RepoAnalysisResult) -> None:
    from hackathon_analyzer.analyzers.documentation import analyze_documentation
    result.documentation = analyze_documentation(repo_path)


def _run_build(repo_path: Path, config: Config, result: RepoAnalysisResult) -> None:
    from hackathon_analyzer.analyzers.build import attempt_build, detect_build_system
    build_result = detect_build_system(repo_path)
    if build_result.build_system:
        build_result = attempt_build(build_result, repo_path, config.build_timeout_seconds)
    result.build = build_result


def _run_code_quality(repo_path: Path, language: str, result: RepoAnalysisResult) -> None:
    from hackathon_analyzer.analyzers.code_quality import analyze_code_quality
    result.code_quality = analyze_code_quality(repo_path, language)


def _run_testing(repo_path: Path, language: str, result: RepoAnalysisResult) -> None:
    from hackathon_analyzer.analyzers.testing import analyze_testing
    structure = result.structure
    if structure is None:
        from hackathon_analyzer.core.models import StructureResult
        structure = StructureResult()
    result.testing = analyze_testing(repo_path, language, structure)


def _run_architecture(repo_path: Path, language: str, result: RepoAnalysisResult, claude_client) -> None:
    from hackathon_analyzer.analyzers.architecture import analyze_architecture
    structure = result.structure
    if structure is None:
        from hackathon_analyzer.core.models import StructureResult
        structure = StructureResult()
    result.architecture = analyze_architecture(repo_path, language, structure, claude_client)


def _run_originality(
    repo_path: Path,
    meta: RepoMeta,
    language: str,
    result: RepoAnalysisResult,
    github_client,
    claude_client,
) -> None:
    from hackathon_analyzer.analyzers.originality import analyze_originality
    result.originality = analyze_originality(
        repo_path, meta, language, github_client, claude_client
    )


def _run_scoring(result: RepoAnalysisResult) -> None:
    from hackathon_analyzer.scoring.scorer import compute_score
    total, dimension_scores = compute_score(result)
    result.total_score = total
    result.dimension_scores = dimension_scores


def _run_promise_reality(
    repo_path: Path, result: RepoAnalysisResult, claude_client
) -> None:
    from hackathon_analyzer.analyzers.promise_reality import analyze_promise_reality
    structure = result.structure
    if structure is None:
        from hackathon_analyzer.core.models import StructureResult
        structure = StructureResult()
    result.promise_reality = analyze_promise_reality(repo_path, structure, claude_client)


def _run_vision_ambition(
    repo_path: Path, result: RepoAnalysisResult, claude_client
) -> None:
    from hackathon_analyzer.analyzers.vision_ambition import analyze_vision_ambition
    result.vision_ambition = analyze_vision_ambition(repo_path, claude_client)


def _run_tech_stack_novelty(repo_path: Path, result: RepoAnalysisResult) -> None:
    from hackathon_analyzer.analyzers.tech_stack_novelty import analyze_tech_stack_novelty
    result.tech_stack_novelty = analyze_tech_stack_novelty(repo_path)


def _run_hackathon_freshness(
    repo_path: Path, config, result: RepoAnalysisResult
) -> None:
    from hackathon_analyzer.analyzers.hackathon_freshness import analyze_hackathon_freshness
    result.hackathon_freshness = analyze_hackathon_freshness(
        repo_path, hackathon_start_date=config.hackathon_start_date
    )


def _run_ai_integration(repo_path: Path, result: RepoAnalysisResult) -> None:
    from hackathon_analyzer.analyzers.ai_integration import analyze_ai_integration
    result.ai_integration = analyze_ai_integration(repo_path)
