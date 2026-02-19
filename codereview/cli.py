"""Command-line interface for codereview."""

import sys
import argparse
import logging
from typing import Optional, Tuple

from rich.console import Console
from rich.panel import Panel

from . import __version__
from .config import (
    load_config,
    init_config,
    validate_api_key,
    is_first_run,
    ConfigError,
    PROVIDER_DEFAULTS,
    GROQ_SETUP_INSTRUCTIONS,
)
from .reviewer import review_code, ReviewResult
from .formatter import print_review, print_error, print_info, console
from .git_utils import (
    is_git_repo,
    get_staged_diff,
    get_diff_last_n,
    get_diff_between,
    get_file_content,
)

logger = logging.getLogger(__name__)


# ─── Welcome Message ───

WELCOME_MESSAGE: str = """
[bold bright_blue]🔍 Welcome to codereview![/bold bright_blue]

AI-powered code review in your terminal.

[bold]Quick setup (free, 60 seconds):[/bold]

  [dim]1.[/dim] Go to [cyan]https://console.groq.com[/cyan]
  [dim]2.[/dim] Sign up with Google or GitHub
  [dim]3.[/dim] Click [bold]API Keys[/bold] → [bold]Create API Key[/bold]
  [dim]4.[/dim] Run these two commands:

     [green]export GROQ_API_KEY="gsk_your_key_here"[/green]
     [green]codereview --init groq[/green]

  [dim]5.[/dim] Review any file:

     [green]codereview app.py[/green]

[dim]To make the key permanent so you don't set it every session:[/dim]

  [green]echo 'export GROQ_API_KEY="gsk_your_key_here"' >> ~/.zshrc[/green]
  [green]source ~/.zshrc[/green]

[dim]Other providers: --init openai | --init anthropic | --init ollama[/dim]
"""


def show_welcome() -> None:
    """Display welcome message for first-time users."""
    console.print(Panel(
        WELCOME_MESSAGE,
        title="[bold]First Time Setup[/bold]",
        border_style="bright_blue",
        padding=(1, 2),
    ))


# ─── Argument Parsing ───

def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="codereview",
        description="AI-powered code review in your terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  codereview app.py                    Review a file
  codereview src/ --recursive          Review all files in directory
  codereview --staged                  Review staged git changes
  codereview --diff HEAD~3             Review last 3 commits
  codereview --stdin                   Review code from stdin (piped)
  cat file.py | codereview --stdin     Pipe code in

Providers:
  codereview --init openai             Set up with OpenAI
  codereview --init ollama             Set up with local Ollama (free, offline)
  codereview --init groq               Set up with Groq (free, no credit card)
  codereview --init anthropic          Set up with Anthropic

Free setup:
  1. Go to https://console.groq.com
  2. Sign up (Google or GitHub)
  3. Create an API key
  4. export GROQ_API_KEY="gsk_your_key_here"
  5. codereview --init groq
        """,
    )

    parser.add_argument("files", nargs="*", help="Files to review")
    parser.add_argument("--staged", action="store_true", help="Review staged git changes")
    parser.add_argument("--diff", metavar="REF", help="Review diff between REF and HEAD")
    parser.add_argument("--last", type=int, metavar="N", help="Review last N commits")
    parser.add_argument("--stdin", action="store_true", help="Read code from stdin")
    parser.add_argument("--model", help="Override model (e.g. gpt-4, llama3)")
    parser.add_argument(
        "--provider",
        choices=list(PROVIDER_DEFAULTS.keys()),
        help="Override provider",
    )
    parser.add_argument(
        "--init",
        metavar="PROVIDER",
        choices=list(PROVIDER_DEFAULTS.keys()),
        help="Initialize config for a provider",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Show setup instructions",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"codereview {__version__}",
    )

    return parser


# ─── Init Command ───

def handle_init(provider: str) -> None:
    """Handle the --init command to configure a provider.

    Args:
        provider: Provider name to initialize.
    """
    try:
        config = init_config(provider)
    except ConfigError as e:
        print_error(str(e))
        sys.exit(1)

    console.print()
    console.print(f"[bold green]✅ Config initialized for {provider}[/bold green]")
    console.print(f"[dim]   Model: {config['model']}[/dim]")
    console.print()

    if provider == "ollama":
        console.print("[bold]Next steps:[/bold]")
        console.print("  1. Make sure Ollama is running: [green]ollama serve[/green]")
        console.print("  2. Pull a model: [green]ollama pull llama3[/green]")
        console.print("  3. Review code: [green]codereview yourfile.py[/green]")
    else:
        env_key: str = PROVIDER_DEFAULTS[provider].get("env_key", "")
        has_key: bool = bool(config.get("api_key"))

        if has_key:
            console.print("[bold green]✅ API key detected![/bold green]")
            console.print()
            console.print("[bold]You're ready! Try:[/bold]")
            console.print("  [green]codereview yourfile.py[/green]")
        else:
            console.print(f"[bold yellow]⚠️  No API key detected.[/bold yellow]")
            console.print()
            if provider == "groq":
                console.print("[bold]Get your free key:[/bold]")
                console.print("  1. Go to [cyan]https://console.groq.com[/cyan]")
                console.print("  2. Sign up → API Keys → Create API Key")
                console.print(f"  3. Run: [green]export {env_key}=\"gsk_your_key_here\"[/green]")
                console.print()
                console.print("[dim]To make it permanent:[/dim]")
                console.print(f'  [green]echo \'export {env_key}="gsk_your_key_here"\' >> ~/.zshrc && source ~/.zshrc[/green]')
            else:
                console.print(f"[bold]Set your API key:[/bold]")
                console.print(f"  [green]export {env_key}=\"your-key-here\"[/green]")

    console.print()


# ─── Git Requirement ───

def require_git_repo() -> None:
    """Exit with an error if not inside a git repository."""
    if not is_git_repo():
        print_error("Not a git repository. Run this from inside a git project.")
        sys.exit(1)


# ─── Code Source Resolvers ───

def resolve_from_stdin() -> Tuple[str, str, bool]:
    """Read code from stdin.

    Returns:
        Tuple of (code, filename_label, is_diff).
    """
    code: str = sys.stdin.read()
    if not code.strip():
        print_error("No input received from stdin")
        sys.exit(1)
    return code, "stdin", False


def resolve_from_staged() -> Tuple[str, str, bool]:
    """Read staged git changes.

    Returns:
        Tuple of (diff_text, filename_label, is_diff).
    """
    require_git_repo()
    code: str = get_staged_diff()
    if not code.strip():
        print_error("No staged changes found. Stage files first: git add <files>")
        sys.exit(1)
    return code, "staged changes", True


def resolve_from_diff(ref: str) -> Tuple[str, str, bool]:
    """Read diff between a ref and HEAD.

    Args:
        ref: Git ref to diff against HEAD.

    Returns:
        Tuple of (diff_text, filename_label, is_diff).
    """
    require_git_repo()
    code: str = get_diff_between(ref)
    if not code.strip():
        print_error(f"No diff found between {ref} and HEAD")
        sys.exit(1)
    return code, f"diff {ref}..HEAD", True


def resolve_from_last_n(n: int) -> Tuple[str, str, bool]:
    """Read diff of last N commits.

    Args:
        n: Number of commits to include.

    Returns:
        Tuple of (diff_text, filename_label, is_diff).
    """
    require_git_repo()
    if n < 1:
        print_error("--last requires a positive integer")
        sys.exit(1)
    code: str = get_diff_last_n(n)
    if not code.strip():
        print_error(f"No changes found in the last {n} commits")
        sys.exit(1)
    return code, f"last {n} commits", True


def resolve_from_files(filepaths: list) -> Tuple[str, str, bool]:
    """Read and combine content from file paths.

    Args:
        filepaths: List of file paths to review.

    Returns:
        Tuple of (combined_code, filename_label, is_diff).
    """
    combined: list = []
    for filepath in filepaths:
        try:
            content: str = get_file_content(filepath)
            if not content.strip():
                print_error(f"File is empty: {filepath}")
                sys.exit(1)
            combined.append(f"# File: {filepath}\n{content}")
        except FileNotFoundError:
            print_error(f"File not found: {filepath}")
            sys.exit(1)
        except PermissionError:
            print_error(f"Permission denied: {filepath}")
            sys.exit(1)
        except IOError as e:
            print_error(f"Cannot read {filepath}: {e}")
            sys.exit(1)

    return "\n\n".join(combined), ", ".join(filepaths), False


def resolve_code(args: argparse.Namespace) -> Optional[Tuple[str, str, bool]]:
    """Route to the correct code resolver based on CLI args.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Tuple of (code, filename, is_diff) or None if no source specified.
    """
    if args.stdin or not sys.stdin.isatty():
        return resolve_from_stdin()
    if args.staged:
        return resolve_from_staged()
    if args.diff:
        return resolve_from_diff(args.diff)
    if args.last:
        return resolve_from_last_n(args.last)
    if args.files:
        return resolve_from_files(args.files)
    return None


# ─── Config Overrides ───

def apply_overrides(config: dict, args: argparse.Namespace) -> dict:
    """Apply CLI argument overrides to loaded config.

    Args:
        config: Base config dictionary.
        args: Parsed CLI arguments.

    Returns:
        Config with overrides applied.
    """
    if args.model:
        config["model"] = args.model
    if args.provider:
        config["provider"] = args.provider
        defaults = PROVIDER_DEFAULTS.get(args.provider, {})
        config["base_url"] = defaults.get("base_url", config["base_url"])
    return config


# ─── Review Execution ───

def run_review(code: str, filename: str, is_diff: bool, config: dict) -> None:
    """Execute the code review and print results.

    Args:
        code: Source code or diff to review.
        filename: Display name for the reviewed file(s).
        is_diff: Whether the input is a diff.
        config: API configuration.
    """
    with console.status("[bold blue]🤖 Analyzing code...[/bold blue]", spinner="dots"):
        try:
            result: ReviewResult = review_code(code, config, is_diff=is_diff)
        except ValueError as e:
            logger.error(f"Invalid input: {e}")
            print_error(str(e))
            sys.exit(1)
        except RuntimeError as e:
            logger.error(f"Review failed: {e}")
            print_error(str(e))
            sys.exit(1)

    print_review(result, filename)


# ─── Main Entry Point ───

def main() -> None:
    """Main entry point for the codereview CLI."""
    parser: argparse.ArgumentParser = build_parser()
    args: argparse.Namespace = parser.parse_args()

    # Handle --setup
    if args.setup:
        show_welcome()
        return

    # Handle --init
    if args.init:
        handle_init(args.init)
        return

    # First run detection — show welcome if no config and no args
    if is_first_run():
        resolved_check: Optional[Tuple[str, str, bool]] = resolve_code(args) if (
            args.files or args.staged or args.diff or args.last or args.stdin
        ) else None

        if resolved_check is None:
            show_welcome()
            return

    # Load and validate config
    config: dict = load_config()
    config = apply_overrides(config, args)

    try:
        validate_api_key(config.get("api_key"), config.get("provider", "openai"))
    except ConfigError as e:
        console.print(str(e))
        sys.exit(1)

    # Resolve code source
    resolved: Optional[Tuple[str, str, bool]] = resolve_code(args)

    if resolved is None:
        parser.print_help()
        console.print()
        console.print("[dim]Need help? Run: codereview --setup[/dim]")
        sys.exit(0)

    code, filename, is_diff = resolved

    # Run review
    run_review(code, filename, is_diff, config)


if __name__ == "__main__":
    main()
