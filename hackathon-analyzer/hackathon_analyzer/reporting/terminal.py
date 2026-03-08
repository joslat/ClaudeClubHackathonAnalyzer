"""Rich terminal output helpers — all console output goes through here."""

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

if TYPE_CHECKING:
    from hackathon_analyzer.core.models import RepoAnalysisResult, RepoMeta

console = Console()


def print_analysis_start(meta: "RepoMeta") -> None:
    console.print(Panel(
        f"[bold cyan]{meta.url}[/bold cyan]\n"
        f"[dim]Cloning to: {meta.local_path}[/dim]",
        title="[bold]Analyzing Repository[/bold]",
        border_style="cyan",
    ))


def print_step(step: str, status: str = "", style: str = "dim") -> None:
    indicator = f"[{style}]{status}[/{style}]" if status else ""
    console.print(f"  [bold]{step}[/bold] {indicator}")


def print_step_done(step: str, detail: str = "") -> None:
    detail_str = f"[dim]{detail}[/dim]" if detail else ""
    console.print(f"  [green]✓[/green] {step} {detail_str}")


def print_step_warn(step: str, detail: str = "") -> None:
    detail_str = f"[dim]{detail}[/dim]" if detail else ""
    console.print(f"  [yellow]![/yellow] {step} {detail_str}")


def print_step_error(step: str, detail: str = "") -> None:
    detail_str = f"[dim]{detail}[/dim]" if detail else ""
    console.print(f"  [red]✗[/red] {step} {detail_str}")


def print_score_summary(result: "RepoAnalysisResult") -> None:
    table = Table(
        title=f"Score: {result.total_score}/10",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Dimension", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Weight", justify="right")
    table.add_column("Notes", style="dim")

    for ds in result.dimension_scores:
        pct = f"{ds.weight:.0%}"
        score_str = f"{ds.raw_score:.2f}"
        color = "green" if ds.raw_score >= 0.7 else ("yellow" if ds.raw_score >= 0.4 else "red")
        table.add_row(
            ds.name.replace("_", " ").title(),
            f"[{color}]{score_str}[/{color}]",
            pct,
            ds.rationale[:60],
        )

    console.print(table)
    score_color = "green" if result.total_score >= 7 else ("yellow" if result.total_score >= 4 else "red")
    console.print(f"\n[bold {score_color}]  Final Score: {result.total_score} / 10[/bold {score_color}]\n")


def print_batch_summary(results: list) -> None:
    table = Table(
        title="Hackathon Analysis — Leaderboard",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Rank", justify="right", style="dim")
    table.add_column("Repository", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Language")
    table.add_column("Build")
    table.add_column("Tests")
    table.add_column("Originality")

    sorted_results = sorted(results, key=lambda r: r.total_score, reverse=True)
    for rank, r in enumerate(sorted_results, 1):
        lang = r.language.primary_language if r.language else "?"
        build_ok = "✓" if (r.build and r.build.build_succeeded) else "✗"
        has_tests = "✓" if (r.testing and r.testing.test_files_count > 0) else "✗"
        risk = r.originality.plagiarism_risk.upper() if r.originality else "?"
        score_color = "green" if r.total_score >= 7 else ("yellow" if r.total_score >= 4 else "red")
        table.add_row(
            str(rank),
            f"{r.meta.owner}/{r.meta.name}",
            f"[{score_color}]{r.total_score}[/{score_color}]",
            lang,
            build_ok,
            has_tests,
            risk,
        )

    console.print(table)


def print_error(message: str) -> None:
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_info(message: str) -> None:
    console.print(f"[cyan]{message}[/cyan]")
