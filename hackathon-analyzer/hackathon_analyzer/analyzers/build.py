"""Analyzer: build system detection and safe dry-run build attempts."""

import time
from pathlib import Path
from typing import Optional

from hackathon_analyzer.core.models import BuildResult
from hackathon_analyzer.utils.subprocess_runner import run_with_timeout, tool_available

# Ordered by priority: first match wins
_BUILD_SYSTEMS: list[tuple[str, list[str], list[str]]] = [
    # (system_name, detection_files, dry-run build command)
    ("poetry",      ["pyproject.toml"],         ["poetry", "install", "--dry-run"]),
    ("pip",         ["requirements.txt"],        ["pip", "install", "-r", "requirements.txt", "--dry-run"]),
    ("pipenv",      ["Pipfile"],                 ["pipenv", "install", "--dry-run"]),
    ("npm",         ["package.json"],            ["npm", "install", "--dry-run"]),
    ("cargo",       ["Cargo.toml"],              ["cargo", "fetch", "--quiet"]),
    ("maven",       ["pom.xml"],                 ["mvn", "dependency:resolve", "-q"]),
    ("gradle",      ["build.gradle", "build.gradle.kts"], ["./gradlew", "dependencies", "-q"]),
    ("go",          ["go.mod"],                  ["go", "mod", "download"]),
    ("bundler",     ["Gemfile"],                 ["bundle", "install"]),
    ("composer",    ["composer.json"],           ["composer", "install", "--dry-run"]),
    ("dotnet",      ["*.sln", "*.csproj"],       ["dotnet", "restore"]),
    ("mix",         ["mix.exs"],                 ["mix", "deps.get"]),
    ("cmake",       ["CMakeLists.txt"],          ["cmake", "--version"]),  # just verify cmake exists
    ("make",        ["Makefile"],                ["make", "--dry-run"]),
]


def detect_build_system(repo_path: Path) -> BuildResult:
    result = BuildResult()
    found_files: list[str] = []

    for system, detection_files, _ in _BUILD_SYSTEMS:
        matched = _find_any(repo_path, detection_files)
        if matched:
            found_files.extend(matched)
            if result.build_system is None:
                result.build_system = system

    result.build_files_found = list(set(found_files))
    return result


def attempt_build(result: BuildResult, repo_path: Path, timeout: int) -> BuildResult:
    """Run the dry-run build command for the detected build system."""
    if not result.build_system:
        return result

    cmd = _get_build_command(result.build_system)
    if not cmd:
        return result

    # Check if the primary tool is available
    if not tool_available(cmd[0]):
        result.build_error = f"Build tool not found: {cmd[0]}"
        return result

    result.build_attempted = True
    start = time.monotonic()
    proc = run_with_timeout(cmd, cwd=repo_path, timeout=timeout)
    result.build_duration_seconds = time.monotonic() - start
    result.build_succeeded = proc.succeeded

    output = proc.combined_output
    result.build_output = output[:2000]
    if not proc.succeeded:
        result.build_error = proc.stderr[:500] if proc.stderr else "Build failed"
    return result


def _find_any(repo_path: Path, patterns: list[str]) -> list[str]:
    found = []
    for pattern in patterns:
        if "*" in pattern:
            found.extend(str(p.name) for p in repo_path.glob(pattern))
        elif (repo_path / pattern).exists():
            found.append(pattern)
    return found


def _get_build_command(system: str) -> Optional[list[str]]:
    for name, _, cmd in _BUILD_SYSTEMS:
        if name == system:
            return cmd
    return None
