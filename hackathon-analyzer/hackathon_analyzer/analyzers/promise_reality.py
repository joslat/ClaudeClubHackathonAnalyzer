"""Analyzer: Promise vs Reality — does the implementation match the README claims?

Uses Claude to compare README claims against actual codebase evidence.
Falls back to keyword-overlap heuristic when Claude is unavailable.
"""

import re
from pathlib import Path
from typing import Optional

from hackathon_analyzer.core.models import (
    PromiseRealityResult,
    StructureResult,
)
from hackathon_analyzer.utils.file_utils import find_file_icase, safe_read_text, walk_repo


def analyze_promise_reality(
    repo_path: Path,
    structure: StructureResult,
    claude_client=None,
) -> PromiseRealityResult:
    """Assess alignment between README promises and actual codebase."""
    result = PromiseRealityResult()

    # 1. Extract README text
    readme_path = find_file_icase(repo_path, ["README.md", "README.rst", "README.txt", "README"])
    if readme_path is None:
        result.claude_assessment = "No README found — cannot assess promise vs reality."
        result.alignment_score = 0.3
        return result

    readme_text = safe_read_text(readme_path, max_bytes=15_000) or ""
    if len(readme_text.split()) < 20:
        result.claude_assessment = "README is too short to extract meaningful claims."
        result.alignment_score = 0.3
        return result

    result.readme_summary = readme_text[:3000]

    # 2. Build codebase summary
    codebase_summary = _build_codebase_summary(repo_path, structure)
    result.codebase_summary = codebase_summary

    # 3. Claude assessment (preferred)
    if claude_client is not None:
        verdict = claude_client.assess_promise_reality(readme_text, codebase_summary)
        if verdict:
            result.claude_assessment = verdict
            result.alignment_score = _extract_alignment_score(verdict)
            supported, unsupported = _count_claim_verdicts(verdict)
            result.claims_supported = supported
            result.claims_unsupported = unsupported
            result.alignment_rationale = _summarize_alignment(
                result.alignment_score, supported, unsupported, claude=True
            )
            return result

    # 4. Heuristic fallback
    result.alignment_score, result.claude_assessment = _heuristic_alignment(
        readme_text, codebase_summary, repo_path
    )
    result.alignment_rationale = _summarize_alignment(
        result.alignment_score, 0, 0, claude=False
    )
    return result


def _build_codebase_summary(repo_path: Path, structure: StructureResult) -> str:
    """Build a compact summary of what the codebase actually contains."""
    parts: list[str] = []

    # File tree
    if structure.tree_summary:
        parts.append(f"File structure:\n{structure.tree_summary}")

    # Top-level dirs
    try:
        top_dirs = sorted(
            d.name for d in repo_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
            and d.name not in {"node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
        )
        parts.append(f"Top-level directories: {', '.join(top_dirs[:15])}")
    except OSError:
        pass

    # Key function/class names from largest source files
    signatures = _extract_key_signatures(repo_path)
    if signatures:
        parts.append(f"Key functions/classes found:\n{chr(10).join(signatures[:30])}")

    # Dependency files present
    dep_files = []
    for name in ["requirements.txt", "pyproject.toml", "package.json", "go.mod",
                  "Cargo.toml", "Gemfile", "pom.xml", "build.gradle"]:
        if (repo_path / name).exists():
            dep_files.append(name)
    if dep_files:
        parts.append(f"Dependency files: {', '.join(dep_files)}")

    return "\n\n".join(parts)


def _extract_key_signatures(repo_path: Path) -> list[str]:
    """Extract function/class names from the largest source files."""
    source_exts = {".py", ".js", ".ts", ".java", ".go", ".rs", ".rb", ".cs", ".tsx", ".jsx"}
    files_by_size: list[tuple[int, Path]] = []

    for dirpath, _, filenames in walk_repo(repo_path):
        for fname in filenames:
            fpath = dirpath / fname
            if fpath.suffix.lower() in source_exts:
                try:
                    files_by_size.append((fpath.stat().st_size, fpath))
                except OSError:
                    pass

    files_by_size.sort(reverse=True)
    signatures: list[str] = []

    func_pattern = re.compile(
        r"^\s*(?:(?:public|private|protected|static|async|export|def|func|fn|function|class)\s+)"
        r"(\w+)",
        re.MULTILINE,
    )

    for _, fpath in files_by_size[:10]:
        content = safe_read_text(fpath, max_bytes=50_000) or ""
        rel = str(fpath.relative_to(repo_path))
        for m in func_pattern.finditer(content):
            name = m.group(1)
            if name and len(name) > 2 and name not in {"__init__", "main", "test"}:
                signatures.append(f"  {rel}: {name}")
                if len(signatures) >= 30:
                    return signatures

    return signatures


def _extract_alignment_score(verdict: str) -> float:
    """Parse ALIGNMENT_SCORE: X.XX from Claude's response."""
    match = re.search(r"ALIGNMENT_SCORE:\s*([\d.]+)", verdict, re.IGNORECASE)
    if match:
        score = float(match.group(1))
        return max(0.0, min(1.0, score))
    # Fallback: look for any decimal score near "alignment" or "score"
    match = re.search(r"(?:alignment|score)[:\s]*(0\.\d+|1\.0)", verdict, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return 0.5  # neutral if unparseable


def _count_claim_verdicts(verdict: str) -> tuple[int, int]:
    """Count SUPPORTED/UNSUPPORTED tags in Claude's verdict."""
    supported = len(re.findall(r"\bSUPPORTED\b", verdict, re.IGNORECASE))
    unsupported = len(re.findall(r"\bUNSUPPORTED\b", verdict, re.IGNORECASE))
    # PARTIAL counts as half-supported
    partial = len(re.findall(r"\bPARTIAL\b", verdict, re.IGNORECASE))
    return supported + (partial // 2), unsupported + (partial - partial // 2)


def _summarize_alignment(
    score: float, supported: int, unsupported: int, claude: bool
) -> str:
    """Generate a short human-readable explanation of the alignment score."""
    if claude and (supported or unsupported):
        total = supported + unsupported
        pct = supported / total * 100 if total else 0
        qualifier = (
            "Strong alignment" if score >= 0.7
            else "Partial alignment" if score >= 0.4
            else "Weak alignment"
        )
        return (
            f"{qualifier}: {supported} of {total} README claims ({pct:.0f}%) "
            f"are backed by code evidence. "
            f"{'The implementation broadly delivers on its promises.' if score >= 0.7 else ''}"
            f"{'Key features are partially implemented but gaps remain.' if 0.4 <= score < 0.7 else ''}"
            f"{'Many claimed features lack corresponding implementation.' if score < 0.4 else ''}"
        )
    # Heuristic or no claims parsed
    if score >= 0.7:
        return "High keyword overlap between README and codebase suggests good alignment."
    if score >= 0.4:
        return "Moderate overlap between README terminology and code; some claims may lack implementation."
    return "Low overlap between README claims and actual codebase content; the project may be aspirational or incomplete."


def _heuristic_alignment(
    readme_text: str,
    codebase_summary: str,
    repo_path: Path,
) -> tuple[float, str]:
    """Keyword-overlap heuristic when Claude is unavailable."""
    # Extract meaningful words from README (skip common English words)
    stopwords = {
        "the", "is", "a", "an", "and", "or", "to", "in", "of", "for", "with",
        "this", "that", "it", "on", "by", "from", "as", "at", "be", "are",
        "was", "were", "will", "can", "has", "have", "do", "does", "not",
        "but", "if", "how", "what", "when", "where", "which", "who", "your",
        "you", "we", "our", "their", "about", "more", "all", "some", "any",
    }
    readme_words = set(
        w.lower() for w in re.findall(r"[a-zA-Z]{3,}", readme_text)
    ) - stopwords

    code_words = set(
        w.lower() for w in re.findall(r"[a-zA-Z]{3,}", codebase_summary)
    ) - stopwords

    if not readme_words:
        return 0.3, "Heuristic: README has too few meaningful words."

    overlap = readme_words & code_words
    overlap_ratio = len(overlap) / len(readme_words) if readme_words else 0

    # Scale: 0.3 overlap → 0.5 score, 0.6 overlap → 0.8 score
    score = min(1.0, 0.2 + overlap_ratio * 1.3)

    return round(score, 2), (
        f"Heuristic assessment (Claude unavailable): "
        f"{len(overlap)}/{len(readme_words)} README keywords found in codebase "
        f"({overlap_ratio:.0%} overlap)."
    )
