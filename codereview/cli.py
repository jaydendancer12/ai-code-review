"""Command-line interface."""

import sys
import argparse
import logging
from . import __version__
from .config import load_config, init_config, PROVIDER_DEFAULTS
from .reviewer import review_code
from .formatter import print_review, print_error, print_info, console
from .git_utils import (
    is_git_repo,
    get_staged_diff,
    get_diff_last_n,
    get_diff_between,
    get_file_content,
)

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser."""
    parser = argparse.ArgumentParser(
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
    parser.add_argument("--provider", choices=list(PROVIDER_DEFAULTS.keys()), help="Override provider")
    parser.add_argument("--init", metavar="PROVIDER", choices=list(PROVIDER_DEFAULTS.keys()), help="Initialize config for a provider")
    parser.add_argument("--version", action="version", version=f"codereview {__version__}")

    return parser


def _resolve_code_from_args(args) -> tuple:
    """Extract code to review from CLI arguments. Returns (code, filename, is_diff)."""
    if args.stdin or not sys.stdin.isatty():
        return sys.stdin.read(), "stdin", False

    if args.staged:
        _require_git_repo()
        code = get_staged_diff()
        if not code.strip():
            print_error("No staged changes. Run: git add <files>")
            sys.exit(1)
        return code, "staged changes", True

    if args.diff:
        _require_git_repo()
        return get_diff_between(args.diff), f"diff {args.diff}..HEAD", True

    if args.last:
        _require_git_repo()
        return get_diff_last_n(args.last), f"last {args.last} commits", True

    if args.files:
        return _read_files(args.files)

    return None, None, False


def _require_git_repo():
    """Exit if not in a git repository."""
    if not is_git_repo():
        print_error("Not a git repository")
        sys.exit(1)


def _read_files(filepaths: list) -> tuple:
    """Read and combine multiple files. Returns (code, filename, is_diff)."""
    combined = []
    for filepath in filepaths:
        try:
            content = get_file_content(filepath)
            combined.append(f"# File: {filepath}\n{content}")
        except FileNotFoundError:
            print_error(f"File not found: {filepath}")
            sys.exit(1)
        except PermissionError:
            print_error(f"Permission denied: {filepath}")
            sys.exit(1)
    return "\n\n".join(combined), ", ".join(filepaths), False


def _apply_config_overrides(config: dict, args) -> dict:
    """Apply CLI argument overrides to config."""
    if args.model:
        config["model"] = args.model
    if args.provider:
        config["provider"] = args.provider
        defaults = PROVIDER_DEFAULTS.get(args.provider, {})
        config["base_url"] = defaults.get("base_url", config["base_url"])
    return config


def _validate_config(config: dict) -> None:
    """Validate config has required fields."""
    if config["provider"] != "ollama" and not config.get("api_key"):
        env_key = PROVIDER_DEFAULTS.get(config["provider"], {}).get("env_key", "API_KEY")
        print_error(f"No API key found. Set {env_key} or run: codereview --init {config['provider']}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.init:
        config = init_config(args.init)
        print_info(f"Config initialized for {args.init}")
        print_info(f"Model: {config['model']}")
        if args.init == "ollama":
            print_info("Make sure Ollama is running: ollama serve")
        else:
            env_key = PROVIDER_DEFAULTS[args.init].get("env_key", "")
            if env_key:
                print_info(f"Set your API key: export {env_key}=your-key-here")
        return

    config = load_config()
    config = _apply_config_overrides(config, args)
    _validate_config(config)

    code, filename, is_diff = _resolve_code_from_args(args)

    if not code or not code.strip():
        if not args.files and not args.staged and not args.diff and not args.last and not args.stdin:
            parser.print_help()
            sys.exit(0)
        print_error("No code to review")
        sys.exit(1)

    with console.status("[bold blue]🤖 Analyzing code...[/bold blue]", spinner="dots"):
        try:
            result = review_code(code, config, is_diff=is_diff)
        except RuntimeError as e:
            logger.error(f"Review failed: {e}")
            print_error(str(e))
            sys.exit(1)

    print_review(result, filename)


if __name__ == "__main__":
    main()
