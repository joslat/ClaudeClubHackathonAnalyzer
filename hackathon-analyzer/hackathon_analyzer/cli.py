"""CLI entry point: hackanalyze analyze / batch / clean / summarize commands."""

import sys

# On Windows, legacy console encoding (cp1252) breaks Rich's Unicode output.
# Reconfigure stdout/stderr to UTF-8 before anything else runs.
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from hackathon_analyzer import __version__

app = typer.Typer(
    name="hackanalyze",
    help="Analyze hackathon repository submissions for technical quality and originality.",
    add_completion=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"hackathon-analyzer {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", callback=_version_callback, is_eager=True, help="Show version"),
    ] = None,
) -> None:
    pass


@app.command()
def analyze(
    repo_urls: Annotated[list[str], typer.Argument(help="One or more GitHub/GitLab repository URLs")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o", help="Directory for reports")] = Path("./reports"),
    timeout: Annotated[int, typer.Option("--timeout", "-t", help="Build timeout in seconds")] = 120,
    skip_build: Annotated[bool, typer.Option("--skip-build", help="Skip build attempts")] = False,
    skip_plagiarism: Annotated[bool, typer.Option("--skip-plagiarism", help="Skip originality check")] = False,
    github_token: Annotated[Optional[str], typer.Option("--github-token", envvar="GITHUB_TOKEN", help="GitHub PAT")] = None,
    claude_api_key: Annotated[Optional[str], typer.Option("--claude-api-key", envvar="ANTHROPIC_API_KEY", help="Anthropic API key")] = None,
    repos_dir: Annotated[Path, typer.Option("--repos-dir", help="Directory for cloned repos")] = Path("./repos"),
) -> None:
    """Analyze one or more repositories and generate Markdown reports."""
    from hackathon_analyzer.config import Config
    from hackathon_analyzer.core import repo_manager
    from hackathon_analyzer.core.pipeline import run_pipeline
    from hackathon_analyzer.reporting import terminal
    from hackathon_analyzer.reporting.summary_report import generate_summary_report
    from hackathon_analyzer.utils.cache import DiskCache

    config = Config(
        github_token=github_token or "",
        anthropic_api_key=claude_api_key or "",
        repos_dir=repos_dir,
        reports_dir=output_dir,
        build_timeout_seconds=timeout,
    )
    config.ensure_dirs()

    github_client = None
    claude_client = None

    if config.has_github_token and not skip_plagiarism:
        from hackathon_analyzer.integrations.github_api import GitHubClient
        cache = DiskCache(config.cache_dir / "github_search", ttl_seconds=config.cache_ttl_seconds)
        github_client = GitHubClient(config.github_token, cache, config.github_search_rate_limit)

    if config.has_anthropic_key:
        from hackathon_analyzer.integrations.claude_api import ClaudeClient
        claude_client = ClaudeClient(config.anthropic_api_key, model=config.claude_model)

    if not config.has_github_token and not skip_plagiarism:
        terminal.print_step_warn("Plagiarism", "No GITHUB_TOKEN set — GitHub search disabled")
    if not config.has_anthropic_key:
        terminal.print_step_warn("AI Analysis", "No ANTHROPIC_API_KEY set — using heuristics only")

    all_results = []

    for url in repo_urls:
        try:
            meta = repo_manager.parse_repo_url(url, config.repos_dir)
        except ValueError as e:
            terminal.print_error(str(e))
            continue

        result = run_pipeline(
            meta=meta,
            config=config,
            skip_build=skip_build,
            skip_plagiarism=skip_plagiarism,
            github_client=github_client,
            claude_client=claude_client,
        )
        all_results.append(result)

        from hackathon_analyzer.reporting.per_repo_report import generate_per_repo_report
        report_path = generate_per_repo_report(result, config.reports_dir / "per-repo")
        terminal.print_info(f"Report: {report_path}")

    if len(all_results) > 1:
        summary_path = generate_summary_report(all_results, config.reports_dir / "summary")
        terminal.print_info(f"Summary: {summary_path}")
        terminal.print_batch_summary(all_results)


@app.command()
def batch(
    input_file: Annotated[Path, typer.Argument(help="File with one repo URL per line")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")] = Path("./reports"),
    timeout: Annotated[int, typer.Option("--timeout", "-t")] = 120,
    skip_build: Annotated[bool, typer.Option("--skip-build")] = False,
    skip_plagiarism: Annotated[bool, typer.Option("--skip-plagiarism")] = False,
    github_token: Annotated[Optional[str], typer.Option("--github-token", envvar="GITHUB_TOKEN")] = None,
    claude_api_key: Annotated[Optional[str], typer.Option("--claude-api-key", envvar="ANTHROPIC_API_KEY")] = None,
    repos_dir: Annotated[Path, typer.Option("--repos-dir")] = Path("./repos"),
) -> None:
    """Analyze repos listed in a file (one URL per line)."""
    if not input_file.exists():
        console.print(f"[red]File not found: {input_file}[/red]")
        raise typer.Exit(1)

    urls = [
        line.strip()
        for line in input_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not urls:
        console.print("[yellow]No URLs found in file.[/yellow]")
        raise typer.Exit(0)

    console.print(f"[cyan]Found {len(urls)} repositories to analyze.[/cyan]")
    ctx = typer.get_current_context()
    ctx.invoke(
        analyze,
        repo_urls=urls,
        output_dir=output_dir,
        timeout=timeout,
        skip_build=skip_build,
        skip_plagiarism=skip_plagiarism,
        github_token=github_token,
        claude_api_key=claude_api_key,
        repos_dir=repos_dir,
    )


@app.command()
def summarize(
    reports_dir: Annotated[Path, typer.Option("--reports-dir", "-r", help="Directory containing per-repo reports")] = Path("./reports"),
) -> None:
    """Generate a summary report from all existing per-repo reports on disk."""
    from hackathon_analyzer.reporting.summary_report import generate_summary_report_from_files

    per_repo_dir = reports_dir / "per-repo"
    if not per_repo_dir.exists() or not list(per_repo_dir.glob("*-report.md")):
        console.print(f"[yellow]No per-repo reports found in {per_repo_dir}[/yellow]")
        raise typer.Exit(1)

    report_files = sorted(per_repo_dir.glob("*-report.md"))
    console.print(f"[cyan]Building summary from {len(report_files)} report(s)...[/cyan]")

    summary_path = generate_summary_report_from_files(report_files, reports_dir / "summary")
    console.print(f"[green]Summary: {summary_path}[/green]")


@app.command()
def clean(
    repos_dir: Annotated[Path, typer.Option("--repos-dir")] = Path("./repos"),
    confirm: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete all cloned repositories from the repos directory."""
    import shutil

    if not repos_dir.exists():
        console.print("[yellow]Repos directory does not exist.[/yellow]")
        return

    cloned = [p for p in repos_dir.iterdir() if p.is_dir()]
    if not cloned:
        console.print("[yellow]No cloned repos found.[/yellow]")
        return

    console.print(f"[yellow]Found {len(cloned)} cloned repo(s) in {repos_dir}[/yellow]")
    if not confirm:
        typer.confirm("Delete all cloned repos?", abort=True)

    for p in cloned:
        shutil.rmtree(p, ignore_errors=True)
        console.print(f"  [dim]Deleted {p.name}[/dim]")
    console.print("[green]Done.[/green]")


if __name__ == "__main__":
    app()
