"""Command-line interface for codereview."""

import sys
import argparse
import logging
from typing import Optional, Tuple

from . import __version__
from .config import (
    load_config,
    init_config,
    validate_api_key,
    ConfigError,
    PROVIDER_DEFAULTS,
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
  codereview --init ollama             Set up with local Ollama
  codereview --init groq               Set up with Groq (free tier)
  codereview --init anthropic          Set up with Anthropic
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

    print_info(f"Config initialized for {provider}")
    print_info(f"Model: {config['model']}")

    if provider == "ollama":
        print_info("Make sure Ollama is running: ollama serve")
    else:
        env_key: str = PROVIDER_DEFAULTS[provider].get("env_key", "")
        if env_key:
            print_info(f"Set your API key: export {env_key}=your-key-here")


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

    # Handle --init
    if args.init:
        handle_init(args.init)
        return

    # Load and validate config
    config: dict = load_config()
    config = apply_overrides(config, args)

    try:
        validate_api_key(config.get("api_key"), config.get("provider", "openai"))
    except ConfigError as e:
        print_error(str(e))
        sys.exit(1)

    # Resolve code source
    resolved: Optional[Tuple[str, str, bool]] = resolve_code(args)

    if resolved is None:
        parser.print_help()
        sys.exit(0)

    code, filename, is_diff = resolved

    # Run review
    run_review(code, filename, is_diff, config)


if __name__ == "__main__":
    main()
