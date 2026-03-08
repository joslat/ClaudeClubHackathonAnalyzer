"""Data models — the lingua franca shared by all modules.

Every analyzer returns one of these models. The pipeline assembles them into
RepoAnalysisResult. No business logic here, only data shapes.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class RepoMeta:
    url: str
    owner: str
    name: str
    slug: str  # "owner-reponame" — used as folder/report name
    local_path: Path
    clone_success: bool = False
    clone_error: Optional[str] = None


@dataclass
class StructureResult:
    total_files: int = 0
    total_dirs: int = 0
    max_depth: int = 0
    file_extensions: dict = field(default_factory=dict)  # ext → count
    has_src_layout: bool = False
    has_tests_dir: bool = False
    has_docs_dir: bool = False
    has_ci: bool = False
    has_docker: bool = False
    tree_summary: str = ""  # Top-3-level indented tree (max 50 entries)
    layout_patterns: list = field(default_factory=list)  # e.g. ["src-layout", "monorepo"]


@dataclass
class LanguageResult:
    primary_language: str = "Unknown"
    language_breakdown: dict = field(default_factory=dict)  # lang → % of code
    detection_method: str = "extension"  # "linguist" | "pygments" | "extension"
    loc_by_language: dict = field(default_factory=dict)  # lang → LOC count
    total_loc: int = 0


@dataclass
class DocumentationResult:
    has_readme: bool = False
    readme_word_count: int = 0
    readme_has_badges: bool = False
    readme_has_usage_section: bool = False
    readme_has_installation_section: bool = False
    has_changelog: bool = False
    has_contributing: bool = False
    has_license: bool = False
    has_api_docs: bool = False
    has_docs_dir: bool = False
    doc_score: float = 0.0  # 0.0-1.0 composite


@dataclass
class BuildResult:
    build_system: Optional[str] = None  # "pip", "npm", "cargo", "maven", etc.
    build_files_found: list = field(default_factory=list)
    build_attempted: bool = False
    build_succeeded: Optional[bool] = None
    build_output: Optional[str] = None  # First 2000 chars of stdout+stderr
    build_duration_seconds: Optional[float] = None
    build_error: Optional[str] = None


@dataclass
class CodeQualityResult:
    language: str = "Unknown"
    linter_issues: int = 0
    linter_tool: str = "none"
    cyclomatic_complexity_avg: Optional[float] = None
    maintainability_index_avg: Optional[float] = None
    security_issues_high: int = 0
    security_issues_medium: int = 0
    security_issues_low: int = 0
    complexity_score: float = 0.5  # 0.0-1.0 (higher = better quality)


@dataclass
class TestingResult:
    has_test_dir: bool = False
    test_files_count: int = 0
    test_frameworks_detected: list = field(default_factory=list)
    test_loc: int = 0
    code_loc: int = 0
    test_to_code_ratio: float = 0.0
    has_ci_test_step: bool = False


@dataclass
class ArchitectureResult:
    pattern_detected: Optional[str] = None  # "MVC", "layered", "microservice", "script", etc.
    top_level_packages: list = field(default_factory=list)
    god_files: list = field(default_factory=list)  # Files >500 LOC
    summary_text: str = ""  # Claude's 2-3 paragraph narrative (or heuristic fallback)


@dataclass
class SnippetMatch:
    snippet: str
    matched_repo: str
    matched_url: str
    similarity_method: str  # "github-search" | "claude-analysis"


@dataclass
class OriginalityResult:
    snippets_checked: int = 0
    matches_found: list = field(default_factory=list)  # List[SnippetMatch]
    similarity_score: float = 0.0  # 0.0-1.0 (lower = more original)
    claude_verdict: str = ""  # Claude's assessment text
    plagiarism_risk: str = "unknown"  # "low" | "medium" | "high" | "unknown"


@dataclass
class PromiseRealityResult:
    readme_summary: str = ""
    codebase_summary: str = ""
    alignment_score: float = 0.0  # 0.0-1.0 (1.0 = perfect match)
    alignment_rationale: str = ""  # Short 1-2 sentence explanation
    claude_assessment: str = ""
    key_claims: list = field(default_factory=list)  # Claims found in README
    claims_supported: int = 0
    claims_unsupported: int = 0


@dataclass
class VisionAmbitionResult:
    problem_clarity: float = 0.0  # 0.0-1.0
    solution_novelty: float = 0.0  # 0.0-1.0
    scope_ambition: float = 0.0  # 0.0-1.0
    audience_specificity: float = 0.0  # 0.0-1.0
    vision_score: float = 0.0  # Weighted composite 0.0-1.0
    vision_rationale: str = ""
    problem_clarity_rationale: str = ""
    solution_novelty_rationale: str = ""
    scope_ambition_rationale: str = ""
    audience_specificity_rationale: str = ""


@dataclass
class TechStackNoveltyResult:
    dependencies_found: dict = field(default_factory=dict)  # package → tier
    novelty_score: float = 0.0  # 0.0-1.0
    bleeding_edge_count: int = 0
    modern_count: int = 0
    established_count: int = 0
    legacy_count: int = 0
    cross_domain_bonus: bool = False
    notable_deps: list = field(default_factory=list)
    novelty_rationale: str = ""


@dataclass
class HackathonFreshnessResult:
    repo_created_at: str = ""  # ISO date from GitHub API or git
    first_commit_date: str = ""
    last_commit_date: str = ""
    total_commits: int = 0
    commit_span_days: int = 0
    freshness_score: float = 0.0  # 0.0-1.0
    freshness_flag: str = "unknown"  # "fresh" | "old" | "unknown"
    flag_reason: str = ""


@dataclass
class AIIntegrationResult:
    ai_libraries_detected: list = field(default_factory=list)
    ai_patterns_detected: list = field(default_factory=list)
    integration_depth: str = "none"  # none | basic | intermediate | advanced | expert
    depth_score: float = 0.0  # 0.0-1.0
    evidence: list = field(default_factory=list)  # "file:pattern" evidence strings


@dataclass
class DimensionScore:
    name: str
    raw_score: float  # 0.0-1.0
    weight: float
    weighted_score: float
    rationale: str


@dataclass
class RepoAnalysisResult:
    meta: RepoMeta
    structure: Optional[StructureResult] = None
    language: Optional[LanguageResult] = None
    documentation: Optional[DocumentationResult] = None
    build: Optional[BuildResult] = None
    code_quality: Optional[CodeQualityResult] = None
    testing: Optional[TestingResult] = None
    architecture: Optional[ArchitectureResult] = None
    originality: Optional[OriginalityResult] = None
    promise_reality: Optional[PromiseRealityResult] = None
    vision_ambition: Optional[VisionAmbitionResult] = None
    tech_stack_novelty: Optional[TechStackNoveltyResult] = None
    hackathon_freshness: Optional[HackathonFreshnessResult] = None
    ai_integration: Optional[AIIntegrationResult] = None
    dimension_scores: list = field(default_factory=list)  # List[DimensionScore]
    total_score: float = 0.0  # 1.0-10.0
    analysis_duration_seconds: float = 0.0
    errors: list = field(default_factory=list)  # Non-fatal errors during analysis
