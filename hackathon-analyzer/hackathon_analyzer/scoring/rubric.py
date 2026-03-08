"""Scoring rubric: dimension definitions and weights. Weights sum to 1.0."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Dimension:
    name: str
    weight: float
    description: str


DIMENSIONS: list[Dimension] = [
    # Original dimensions (rebalanced)
    Dimension("code_quality",       0.12, "Linter issues, cyclomatic complexity, security findings"),
    Dimension("architecture",       0.12, "Architectural pattern, god files, CI/CD, Docker"),
    Dimension("testing",            0.10, "Test files, frameworks, test/code ratio, CI test step"),
    Dimension("build_success",      0.08, "Build system detected and dry-run succeeded"),
    Dimension("originality",        0.10, "GitHub search + Claude plagiarism verdict (inverted)"),
    Dimension("documentation",      0.08, "README quality, license, changelog, docs"),
    Dimension("structure",          0.03, "Layout cleanliness, depth, naming"),
    # New dimensions
    Dimension("promise_reality",    0.12, "Does the implementation match what the README claims?"),
    Dimension("vision_ambition",    0.08, "Problem clarity, solution novelty, scope ambition"),
    Dimension("tech_stack_novelty", 0.06, "Modern vs legacy dependency choices"),
    Dimension("hackathon_freshness",0.06, "Was the repo created during the hackathon window?"),
    Dimension("ai_integration",     0.05, "Depth and sophistication of AI/LLM usage"),
]

assert abs(sum(d.weight for d in DIMENSIONS) - 1.0) < 1e-9, "Weights must sum to 1.0"

DIMENSION_NAMES = [d.name for d in DIMENSIONS]
