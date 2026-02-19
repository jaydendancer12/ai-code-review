"""Beautiful terminal output using rich."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.markdown import Markdown
from rich import box

from .reviewer import ReviewResult, Severity, Issue

console = Console()

SEVERITY_STYLES = {
    Severity.CRITICAL: ("🔴", "bold red"),
    Severity.WARNING: ("🟡", "bold yellow"),
    Severity.INFO: ("🔵", "bold blue"),
    Severity.STYLE: ("⚪", "dim"),
}

SCORE_COLORS = {
    range(0, 4): "bold red",
    range(4, 7): "bold yellow",
    range(7, 9): "bold green",
    range(9, 11): "bold bright_green",
}


def get_score_color(score: int) -> str:
    """Get color for a given score."""
    for score_range, color in SCORE_COLORS.items():
        if score in score_range:
            return color
    return "white"


def get_score_bar(score: int) -> str:
    """Generate visual score bar."""
    filled = "█" * score
    empty = "░" * (10 - score)
    return f"{filled}{empty}"


def format_issue(issue: Issue, index: int) -> Panel:
    """Format a single issue as a rich panel."""
    icon, style = SEVERITY_STYLES.get(issue.severity, ("❓", "white"))

    content = Text()
    content.append(f"{issue.description}\n\n", style="white")

    if issue.file:
        content.append("File: ", style="dim")
        content.append(f"{issue.file}", style="cyan")
        if issue.line:
            content.append(f":{issue.line}", style="cyan")
        content.append("\n")

    if issue.suggestion:
        content.append("\n💡 Suggestion: ", style="bold green")
        content.append(f"{issue.suggestion}", style="green")

    title = f"{icon} [{style}]{issue.severity.value.upper()}[/] — {issue.title}"

    return Panel(
        content,
        title=title,
        title_align="left",
        border_style=style.replace("bold ", ""),
        padding=(0, 1),
    )


def print_review(result: ReviewResult, filename: str = "stdin") -> None:
    """Print complete review to terminal."""
    console.print()

    # Header
    score_color = get_score_color(result.score)
    score_bar = get_score_bar(result.score)

    header = Table(show_header=False, box=None, padding=(0, 2))
    header.add_column(ratio=1)
    header.add_column(ratio=1)

    score_text = Text()
    score_text.append("Score: ", style="bold")
    score_text.append(f"{result.score}/10 ", style=score_color)
    score_text.append(score_bar, style=score_color)

    info_text = Text()
    info_text.append("File: ", style="dim")
    info_text.append(f"{filename}\n", style="cyan")
    info_text.append(f"Lines: ", style="dim")
    info_text.append(f"{result.lines_reviewed}\n", style="white")
    info_text.append(f"Issues: ", style="dim")
    info_text.append(f"{len(result.issues)}", style="white")

    header.add_row(score_text, info_text)

    console.print(Panel(
        header,
        title="[bold]🔍 Code Review[/bold]",
        subtitle=f"[dim]ai-code-review v1.0.0[/dim]",
        border_style="bright_blue",
        padding=(1, 2),
    ))

    # Summary
    console.print(Panel(
        f"[italic]{result.summary}[/italic]",
        title="📋 Summary",
        border_style="blue",
        padding=(0, 1),
    ))

    # Issue counts
    counts = {s: 0 for s in Severity}
    for issue in result.issues:
        counts[issue.severity] += 1

    if any(counts.values()):
        count_text = Text()
        count_text.append(f"🔴 {counts[Severity.CRITICAL]} critical  ", style="red")
        count_text.append(f"🟡 {counts[Severity.WARNING]} warning  ", style="yellow")
        count_text.append(f"🔵 {counts[Severity.INFO]} info  ", style="blue")
        count_text.append(f"⚪ {counts[Severity.STYLE]} style", style="dim")
        console.print(count_text)
        console.print()

    # Issues
    if result.issues:
        sorted_issues = sorted(
            result.issues,
            key=lambda i: list(Severity).index(i.severity),
        )
        for i, issue in enumerate(sorted_issues):
            console.print(format_issue(issue, i + 1))
            console.print()
    else:
        console.print(Panel(
            "✅ No issues found! Code looks clean.",
            border_style="green",
        ))

    console.print()


def print_error(message: str) -> None:
    """Print error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"[bold green]✅[/bold green] {message}")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"[bold blue]ℹ[/bold blue]  {message}")
