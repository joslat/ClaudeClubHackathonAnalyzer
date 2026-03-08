"""Scorer: aggregates analyzer results into a 1.0-10.0 score."""

from hackathon_analyzer.core.models import (
    DimensionScore,
    RepoAnalysisResult,
)
from hackathon_analyzer.scoring.rubric import DIMENSIONS


def compute_score(result: RepoAnalysisResult) -> tuple[float, list[DimensionScore]]:
    """Compute the final 1.0-10.0 score and per-dimension breakdown."""
    scorers = {
        "code_quality": _score_code_quality,
        "architecture": _score_architecture,
        "testing": _score_testing,
        "build_success": _score_build,
        "originality": _score_originality,
        "documentation": _score_documentation,
        "structure": _score_structure,
        "promise_reality": _score_promise_reality,
        "vision_ambition": _score_vision_ambition,
        "tech_stack_novelty": _score_tech_stack_novelty,
        "hackathon_freshness": _score_hackathon_freshness,
        "ai_integration": _score_ai_integration,
    }

    dimension_scores: list[DimensionScore] = []
    weighted_sum = 0.0

    for dim in DIMENSIONS:
        scorer = scorers[dim.name]
        raw, rationale = scorer(result)
        raw = max(0.0, min(1.0, raw))
        weighted = raw * dim.weight
        weighted_sum += weighted
        dimension_scores.append(
            DimensionScore(
                name=dim.name,
                raw_score=round(raw, 3),
                weight=dim.weight,
                weighted_score=round(weighted, 4),
                rationale=rationale,
            )
        )

    final = round(1.0 + (weighted_sum * 9.0), 1)
    return final, dimension_scores


# --- Per-dimension scorers ---

def _score_documentation(r: RepoAnalysisResult) -> tuple[float, str]:
    if r.documentation is None:
        return 0.3, "Documentation not analyzed"
    doc = r.documentation
    score = doc.doc_score
    notes = []
    if doc.has_readme:
        notes.append(f"README ({doc.readme_word_count} words)")
    if doc.has_license:
        notes.append("license")
    if doc.has_changelog:
        notes.append("changelog")
    if doc.has_docs_dir:
        notes.append("docs dir")
    rationale = f"Score {score:.2f}: {', '.join(notes) or 'minimal documentation'}"
    return score, rationale


def _score_code_quality(r: RepoAnalysisResult) -> tuple[float, str]:
    if r.code_quality is None:
        return 0.5, "Code quality not analyzed"
    cq = r.code_quality

    # Linter score
    issues = cq.linter_issues
    if issues == 0:
        lint = 1.0
    elif issues <= 10:
        lint = 0.8
    elif issues <= 50:
        lint = 0.5
    elif issues <= 100:
        lint = 0.3
    else:
        lint = 0.1

    # Security score
    if cq.security_issues_high == 0:
        sec = 1.0
    elif cq.security_issues_high <= 2:
        sec = 0.5
    else:
        sec = 0.1

    cc = cq.cyclomatic_complexity_avg
    mi = cq.maintainability_index_avg

    if cc is None:
        cc_score = 0.7  # neutral if not measured
    elif cc <= 5:
        cc_score = 1.0
    elif cc <= 10:
        cc_score = 0.7
    elif cc <= 15:
        cc_score = 0.4
    else:
        cc_score = 0.2

    if mi is None:
        mi_score = 0.7
    elif mi >= 80:
        mi_score = 1.0
    elif mi >= 60:
        mi_score = 0.7
    elif mi >= 40:
        mi_score = 0.4
    else:
        mi_score = 0.2

    # Composite (tool-agnostic weights)
    score = lint * 0.35 + cc_score * 0.30 + mi_score * 0.20 + sec * 0.15
    rationale = (
        f"{cq.linter_tool}: {issues} issues, "
        f"CC avg: {cc:.1f}" if cc else f"{cq.linter_tool}: {issues} issues"
    )
    if cq.security_issues_high:
        rationale += f", {cq.security_issues_high} high-severity security issues"
    return score, rationale


def _score_testing(r: RepoAnalysisResult) -> tuple[float, str]:
    if r.testing is None:
        return 0.2, "Testing not analyzed"
    t = r.testing
    score = 0.0
    notes = []

    if t.test_files_count > 0:
        score += 0.30
        notes.append(f"{t.test_files_count} test files")
    if t.test_files_count >= 10:
        score += 0.20
    if t.test_to_code_ratio >= 0.20:
        score += 0.25
        notes.append(f"ratio {t.test_to_code_ratio:.0%}")
    elif t.test_to_code_ratio >= 0.10:
        score += 0.12
    if t.test_frameworks_detected:
        score += 0.15
        notes.append(", ".join(t.test_frameworks_detected))
    if t.has_ci_test_step:
        score += 0.10
        notes.append("CI test step")

    rationale = ", ".join(notes) if notes else "no tests found"
    return min(score, 1.0), rationale


def _score_build(r: RepoAnalysisResult) -> tuple[float, str]:
    if r.build is None:
        return 0.3, "Build not analyzed"
    b = r.build

    if b.build_system is None:
        return 0.3, "No build system detected"
    if not b.build_attempted:
        return 0.5, f"Build system: {b.build_system} (not attempted)"
    if b.build_succeeded is True:
        dur = f"{b.build_duration_seconds:.1f}s" if b.build_duration_seconds else ""
        return 1.0, f"{b.build_system} build succeeded {dur}"
    if r.build and r.build.build_error and "timed out" in (r.build.build_error or "").lower():
        return 0.2, f"{b.build_system} build timed out"
    return 0.3, f"{b.build_system} build failed: {(b.build_error or '')[:80]}"


def _score_architecture(r: RepoAnalysisResult) -> tuple[float, str]:
    arch = r.architecture
    struct = r.structure
    if arch is None:
        return 0.3, "Architecture not analyzed"

    score = 0.0
    notes = []

    if arch.pattern_detected:
        score += 0.30
        notes.append(arch.pattern_detected)
    if not arch.god_files:
        score += 0.20
        notes.append("no god files")
    else:
        notes.append(f"{len(arch.god_files)} god file(s)")
    if struct and struct.has_tests_dir and struct.has_src_layout:
        score += 0.15
        notes.append("src+tests layout")
    elif struct and (struct.has_tests_dir or struct.has_src_layout):
        score += 0.08
    if struct and struct.has_ci:
        score += 0.15
        notes.append("CI")
    if struct and struct.has_docker:
        score += 0.10
        notes.append("Docker")
    if arch.top_level_packages and len(arch.top_level_packages) >= 2:
        score += 0.10
        notes.append(f"{len(arch.top_level_packages)} packages")

    return min(score, 1.0), ", ".join(notes) if notes else "basic structure"


def _score_originality(r: RepoAnalysisResult) -> tuple[float, str]:
    if r.originality is None:
        return 0.7, "Originality not checked (assumed original)"
    orig = r.originality
    risk = orig.plagiarism_risk

    if risk == "low" or risk == "unknown":
        score = 1.0 - (orig.similarity_score * 0.4)  # small penalty for matches
    elif risk == "medium":
        score = 0.3
    elif risk == "high":
        score = 0.1
    else:
        score = 0.7

    matches = len(orig.matches_found)
    rationale = (
        f"Risk: {risk.upper()}, {orig.snippets_checked} snippets checked, "
        f"{matches} GitHub match(es)"
    )
    return max(0.0, min(score, 1.0)), rationale


def _score_structure(r: RepoAnalysisResult) -> tuple[float, str]:
    struct = r.structure
    if struct is None:
        return 0.3, "Structure not analyzed"

    score = 0.0
    notes = []

    if struct.has_src_layout:
        score += 0.30
        notes.append("src-layout")
    if 2 <= struct.max_depth <= 5:
        score += 0.20
        notes.append(f"depth {struct.max_depth}")
    if struct.total_files <= 200:
        score += 0.10
    if struct.layout_patterns:
        score += 0.20
        notes.extend(struct.layout_patterns)
    if struct.has_ci or struct.has_docker:
        score += 0.20

    return min(score, 1.0), ", ".join(notes) if notes else "flat or unstructured"


# --- New dimension scorers ---

def _score_promise_reality(r: RepoAnalysisResult) -> tuple[float, str]:
    if r.promise_reality is None:
        return 0.5, "Promise–reality not analyzed"
    pr = r.promise_reality
    notes = []
    if pr.claims_supported or pr.claims_unsupported:
        total = pr.claims_supported + pr.claims_unsupported
        notes.append(f"{pr.claims_supported}/{total} claims supported")
    if pr.claude_assessment and len(pr.claude_assessment) > 20:
        notes.append("Claude assessed")
    else:
        notes.append("heuristic")
    rationale = ", ".join(notes) if notes else f"alignment {pr.alignment_score:.2f}"
    return pr.alignment_score, rationale


def _score_vision_ambition(r: RepoAnalysisResult) -> tuple[float, str]:
    if r.vision_ambition is None:
        return 0.5, "Vision not analyzed"
    va = r.vision_ambition
    notes = [
        f"clarity={va.problem_clarity:.1f}",
        f"novelty={va.solution_novelty:.1f}",
        f"ambition={va.scope_ambition:.1f}",
        f"audience={va.audience_specificity:.1f}",
    ]
    return va.vision_score, ", ".join(notes)


def _score_tech_stack_novelty(r: RepoAnalysisResult) -> tuple[float, str]:
    if r.tech_stack_novelty is None:
        return 0.4, "Tech stack not analyzed"
    ts = r.tech_stack_novelty
    notes = []
    if ts.bleeding_edge_count:
        notes.append(f"{ts.bleeding_edge_count} bleeding-edge")
    if ts.modern_count:
        notes.append(f"{ts.modern_count} modern")
    if ts.established_count:
        notes.append(f"{ts.established_count} established")
    if ts.legacy_count:
        notes.append(f"{ts.legacy_count} legacy")
    if ts.cross_domain_bonus:
        notes.append("cross-domain bonus")
    rationale = ", ".join(notes) if notes else "no deps found"
    return ts.novelty_score, rationale


def _score_hackathon_freshness(r: RepoAnalysisResult) -> tuple[float, str]:
    if r.hackathon_freshness is None:
        return 0.5, "Freshness not analyzed"
    hf = r.hackathon_freshness
    flag_emoji = {"fresh": "🟢", "old": "🔴", "unknown": "⚪"}.get(hf.freshness_flag, "⚪")
    rationale = f"{flag_emoji} {hf.freshness_flag.upper()}: {hf.flag_reason}"
    if hf.total_commits:
        rationale += f" ({hf.total_commits} commits)"
    return hf.freshness_score, rationale


def _score_ai_integration(r: RepoAnalysisResult) -> tuple[float, str]:
    if r.ai_integration is None:
        return 0.3, "AI integration not analyzed"
    ai = r.ai_integration
    if ai.integration_depth == "none":
        return 0.0, "No AI/LLM integration detected"
    notes = [f"depth: {ai.integration_depth}"]
    if ai.ai_libraries_detected:
        notes.append(", ".join(ai.ai_libraries_detected[:4]))
    if ai.ai_patterns_detected:
        notes.append(f"{len(ai.ai_patterns_detected)} patterns")
    return ai.depth_score, "; ".join(notes)
