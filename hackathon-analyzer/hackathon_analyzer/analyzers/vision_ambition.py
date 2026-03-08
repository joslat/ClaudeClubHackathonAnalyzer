"""Analyzer: Vision Ambition Score — evaluate the README as a vision document.

Uses Claude to score problem clarity, solution novelty, scope ambition,
and audience specificity. Falls back to keyword heuristic without Claude.
"""

import re
from pathlib import Path
from typing import Optional

from hackathon_analyzer.core.models import VisionAmbitionResult
from hackathon_analyzer.utils.file_utils import find_file_icase, safe_read_text


def analyze_vision_ambition(
    repo_path: Path,
    claude_client=None,
) -> VisionAmbitionResult:
    """Evaluate the project's vision and ambition from its README."""
    result = VisionAmbitionResult()

    # 1. Extract README
    readme_path = find_file_icase(repo_path, ["README.md", "README.rst", "README.txt", "README"])
    if readme_path is None:
        result.vision_rationale = "No README found — cannot assess vision."
        result.vision_score = 0.2
        return result

    readme_text = safe_read_text(readme_path, max_bytes=12_000) or ""
    if len(readme_text.split()) < 30:
        result.vision_rationale = "README is too short to assess vision."
        result.vision_score = 0.2
        return result

    # 2. Claude assessment (preferred)
    if claude_client is not None:
        verdict = claude_client.assess_vision(readme_text)
        if verdict:
            result.vision_rationale = verdict
            scores = _parse_vision_scores(verdict)
            result.problem_clarity = scores.get("problem_clarity", 0.5)
            result.solution_novelty = scores.get("solution_novelty", 0.5)
            result.scope_ambition = scores.get("scope_ambition", 0.5)
            result.audience_specificity = scores.get("audience_specificity", 0.5)
            result.vision_score = _compute_weighted(result)
            # Extract per-dimension rationales from Claude's text
            rationales = _parse_vision_rationales(verdict)
            result.problem_clarity_rationale = rationales.get("problem_clarity", "")
            result.solution_novelty_rationale = rationales.get("solution_novelty", "")
            result.scope_ambition_rationale = rationales.get("scope_ambition", "")
            result.audience_specificity_rationale = rationales.get("audience_specificity", "")
            return result

    # 3. Heuristic fallback
    result.problem_clarity, result.problem_clarity_rationale = _heuristic_problem_clarity(readme_text)
    result.solution_novelty, result.solution_novelty_rationale = _heuristic_novelty(readme_text)
    result.scope_ambition, result.scope_ambition_rationale = _heuristic_ambition(readme_text)
    result.audience_specificity, result.audience_specificity_rationale = _heuristic_audience(readme_text)
    result.vision_score = _compute_weighted(result)
    result.vision_rationale = (
        f"Heuristic assessment (Claude unavailable): "
        f"clarity={result.problem_clarity:.2f}, novelty={result.solution_novelty:.2f}, "
        f"ambition={result.scope_ambition:.2f}, audience={result.audience_specificity:.2f}"
    )
    return result


def _compute_weighted(r: VisionAmbitionResult) -> float:
    """Weighted composite: clarity 30% + novelty 30% + ambition 25% + audience 15%."""
    score = (
        r.problem_clarity * 0.30
        + r.solution_novelty * 0.30
        + r.scope_ambition * 0.25
        + r.audience_specificity * 0.15
    )
    return round(max(0.0, min(1.0, score)), 3)


def _parse_vision_scores(verdict: str) -> dict[str, float]:
    """Parse structured scores from Claude's response."""
    scores: dict[str, float] = {}
    patterns = {
        "problem_clarity": r"PROBLEM_CLARITY:\s*([\d.]+)",
        "solution_novelty": r"SOLUTION_NOVELTY:\s*([\d.]+)",
        "scope_ambition": r"SCOPE_AMBITION:\s*([\d.]+)",
        "audience_specificity": r"AUDIENCE_SPECIFICITY:\s*([\d.]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, verdict, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            scores[key] = max(0.0, min(1.0, val))
    return scores


# --- Heuristic sub-scorers (keyword-based) ---

_PROBLEM_KEYWORDS = {
    "problem", "challenge", "issue", "pain", "gap", "need", "struggle",
    "inefficient", "difficult", "complex", "costly", "slow", "broken",
    "solve", "address", "fix", "improve", "reduce", "eliminate",
}

_NOVELTY_KEYWORDS = {
    "novel", "unique", "innovative", "new approach", "first", "unlike",
    "breakthrough", "rethink", "reimagine", "original", "different",
    "state-of-the-art", "cutting-edge", "next-generation", "ai-powered",
}

_AMBITION_KEYWORDS = {
    "real-time", "scalable", "distributed", "autonomous", "end-to-end",
    "production", "enterprise", "platform", "framework", "ecosystem",
    "multi-agent", "pipeline", "infrastructure", "orchestrat",
}

_AUDIENCE_KEYWORDS = {
    "user", "developer", "team", "organization", "company", "patient",
    "student", "researcher", "analyst", "engineer", "doctor", "teacher",
    "customer", "client", "stakeholder", "community",
}


def _keyword_score_with_rationale(
    text: str, keywords: set[str], dimension_name: str
) -> tuple[float, str]:
    """Score 0-1 based on keyword presence density, with explanation."""
    text_lower = text.lower()
    found_keywords = [kw for kw in keywords if kw in text_lower]
    found = len(found_keywords)

    if found == 0:
        score = 0.1
        rationale = f"No {dimension_name.lower()} indicators found in README."
    elif found <= 2:
        score = 0.4
        shown = ", ".join(f'"{kw}"' for kw in found_keywords[:3])
        rationale = f"Few {dimension_name.lower()} signals ({found} found: {shown})."
    elif found <= 5:
        score = 0.7
        shown = ", ".join(f'"{kw}"' for kw in found_keywords[:4])
        rationale = f"Good {dimension_name.lower()} signals ({found} found incl. {shown})."
    else:
        score = 0.9
        shown = ", ".join(f'"{kw}"' for kw in found_keywords[:4])
        rationale = f"Strong {dimension_name.lower()} indicators ({found} found incl. {shown})."

    return score, rationale


def _heuristic_problem_clarity(readme: str) -> tuple[float, str]:
    return _keyword_score_with_rationale(readme, _PROBLEM_KEYWORDS, "problem clarity")


def _heuristic_novelty(readme: str) -> tuple[float, str]:
    return _keyword_score_with_rationale(readme, _NOVELTY_KEYWORDS, "solution novelty")


def _heuristic_ambition(readme: str) -> tuple[float, str]:
    return _keyword_score_with_rationale(readme, _AMBITION_KEYWORDS, "scope ambition")


def _heuristic_audience(readme: str) -> tuple[float, str]:
    return _keyword_score_with_rationale(readme, _AUDIENCE_KEYWORDS, "audience specificity")


def _parse_vision_rationales(verdict: str) -> dict[str, str]:
    """Extract per-dimension rationale text from Claude's response.

    Looks for patterns like:
    **Problem Clarity** (0.7): The README clearly defines...
    or numbered list items near each dimension name.
    """
    rationales: dict[str, str] = {}
    dim_patterns = {
        "problem_clarity": r"(?:problem.clarity|clarity)[^:]*:\s*(.+?)(?=\n\s*(?:\*\*|[A-Z_]+:|$|\d\.))",
        "solution_novelty": r"(?:solution.novelty|novelty)[^:]*:\s*(.+?)(?=\n\s*(?:\*\*|[A-Z_]+:|$|\d\.))",
        "scope_ambition": r"(?:scope.ambition|ambition)[^:]*:\s*(.+?)(?=\n\s*(?:\*\*|[A-Z_]+:|$|\d\.))",
        "audience_specificity": r"(?:audience.specificity|audience)[^:]*:\s*(.+?)(?=\n\s*(?:\*\*|[A-Z_]+:|$|\d\.))",
    }
    for key, pattern in dim_patterns.items():
        match = re.search(pattern, verdict, re.IGNORECASE | re.DOTALL)
        if match:
            text = match.group(1).strip()
            # Clean up and truncate
            text = re.sub(r"\s+", " ", text)[:200]
            rationales[key] = text
    return rationales
