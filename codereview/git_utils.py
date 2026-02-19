"""Git utilities for extracting diffs and file content."""

import subprocess
import os
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DiffHunk:
    """Represents a section of changed code."""
    file: str
    old_start: int
    new_start: int
    content: str
    added_lines: List[str]
    removed_lines: List[str]


def run_git(args: List[str], cwd: Optional[str] = None) -> str:
    """Run a git command and return stdout.

    Args:
        args: Git subcommand and arguments.
        cwd: Working directory for the command.

    Returns:
        Stdout text from the command, or empty string on failure.
    """
    try:
        result: subprocess.CompletedProcess = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd(),
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout
    except subprocess.TimeoutExpired:
        logger.error(f"git {' '.join(args)} timed out after 30s")
        return ""
    except FileNotFoundError:
        logger.error("git executable not found in PATH")
        return ""


def is_git_repo() -> bool:
    """Check if the current directory is inside a git repository.

    Returns:
        True if inside a git repo, False otherwise.
    """
    try:
        result: subprocess.CompletedProcess = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_staged_diff() -> str:
    """Get the diff of staged (added) files.

    Returns:
        Unified diff text of staged changes.
    """
    return run_git(["diff", "--cached"])


def get_diff_between(ref: str) -> str:
    """Get diff between a git ref and HEAD.

    Args:
        ref: Git reference (branch, tag, commit hash).

    Returns:
        Unified diff text.
    """
    return run_git(["diff", ref, "HEAD"])


def get_diff_last_n(n: int = 1) -> str:
    """Get the diff of the last N commits.

    Args:
        n: Number of commits to include in the diff.

    Returns:
        Unified diff text.
    """
    return run_git(["diff", f"HEAD~{n}", "HEAD", "--no-ext-diff"])


def get_file_content(filepath: str) -> str:
    """Read a file's content with encoding fallback.

    Args:
        filepath: Path to the file to read.

    Returns:
        File content as a string.

    Raises:
        FileNotFoundError: If file does not exist.
        PermissionError: If file cannot be read.
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(filepath, encoding="latin-1") as f:
            return f.read()


def get_changed_files(ref: Optional[str] = None) -> List[str]:
    """Get list of changed file paths.

    Args:
        ref: Git ref to compare against. If None, uses staged changes.

    Returns:
        List of changed file paths.
    """
    if ref:
        output: str = run_git(["diff", "--name-only", ref, "HEAD"])
    else:
        output = run_git(["diff", "--name-only", "--cached"])
    return [f for f in output.strip().split("\n") if f]


def _finalize_hunk(
    file: Optional[str],
    content: List[str],
    added: List[str],
    removed: List[str],
) -> Optional[DiffHunk]:
    """Create a DiffHunk from accumulated data.

    Args:
        file: Filename for this hunk.
        content: All diff lines for this hunk.
        added: Lines that were added.
        removed: Lines that were removed.

    Returns:
        DiffHunk instance, or None if no data.
    """
    if file and content:
        return DiffHunk(
            file=file,
            old_start=0,
            new_start=0,
            content="\n".join(content),
            added_lines=list(added),
            removed_lines=list(removed),
        )
    return None


def parse_diff(diff_text: str) -> List[DiffHunk]:
    """Parse unified diff text into structured DiffHunk objects.

    Args:
        diff_text: Raw unified diff output from git.

    Returns:
        List of DiffHunk objects, one per file changed.
    """
    hunks: List[DiffHunk] = []
    current_file: Optional[str] = None
    current_content: List[str] = []
    added: List[str] = []
    removed: List[str] = []

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            hunk: Optional[DiffHunk] = _finalize_hunk(
                current_file, current_content, added, removed
            )
            if hunk:
                hunks.append(hunk)

            parts: List[str] = line.split(" b/")
            current_file = parts[-1] if len(parts) > 1 else "unknown"
            current_content = []
            added = []
            removed = []
        elif line.startswith("@@"):
            current_content.append(line)
        elif line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
            current_content.append(line)
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
            current_content.append(line)
        else:
            current_content.append(line)

    final: Optional[DiffHunk] = _finalize_hunk(
        current_file, current_content, added, removed
    )
    if final:
        hunks.append(final)

    return hunks


def get_repo_language_stats() -> Dict[str, int]:
    """Get rough language breakdown by file extension.

    Returns:
        Dictionary mapping extensions to file counts, top 10.
    """
    result: str = run_git(["ls-files"])
    files: List[str] = result.strip().split("\n")
    extensions: Dict[str, int] = {}
    for f in files:
        if "." in f:
            ext: str = f.rsplit(".", 1)[-1].lower()
            extensions[ext] = extensions.get(ext, 0) + 1
    return dict(sorted(extensions.items(), key=lambda x: -x[1])[:10])
