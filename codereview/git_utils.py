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
    """Run a git command and return stdout."""
    try:
        result = subprocess.run(
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
        logger.error(f"git {' '.join(args)} timed out")
        return ""
    except FileNotFoundError:
        logger.error("git not found in PATH")
        return ""


def is_git_repo() -> bool:
    """Check if current directory is a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_staged_diff() -> str:
    """Get diff of staged files."""
    return run_git(["diff", "--cached"])


def get_diff_between(ref: str) -> str:
    """Get diff between ref and HEAD."""
    return run_git(["diff", ref, "HEAD"])


def get_diff_last_n(n: int = 1) -> str:
    """Get diff of last n commits using --stat for efficiency on large repos."""
    return run_git(["diff", f"HEAD~{n}", "HEAD", "--no-ext-diff"])


def get_file_content(filepath: str) -> str:
    """Read a file's content with error handling."""
    try:
        with open(filepath, encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(filepath, encoding="latin-1") as f:
            return f.read()


def get_changed_files(ref: Optional[str] = None) -> List[str]:
    """Get list of changed files."""
    if ref:
        output = run_git(["diff", "--name-only", ref, "HEAD"])
    else:
        output = run_git(["diff", "--name-only", "--cached"])
    return [f for f in output.strip().split("\n") if f]


def parse_diff(diff_text: str) -> List[DiffHunk]:
    """Parse unified diff into structured hunks."""
    hunks: List[DiffHunk] = []
    current_file: Optional[str] = None
    current_content: List[str] = []
    added: List[str] = []
    removed: List[str] = []

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            if current_file and current_content:
                hunks.append(DiffHunk(
                    file=current_file,
                    old_start=0,
                    new_start=0,
                    content="\n".join(current_content),
                    added_lines=added,
                    removed_lines=removed,
                ))
            parts = line.split(" b/")
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

    if current_file and current_content:
        hunks.append(DiffHunk(
            file=current_file,
            old_start=0,
            new_start=0,
            content="\n".join(current_content),
            added_lines=added,
            removed_lines=removed,
        ))

    return hunks


def get_repo_language_stats() -> Dict[str, int]:
    """Get rough language breakdown of repo."""
    result = run_git(["ls-files"])
    files = result.strip().split("\n")
    extensions: Dict[str, int] = {}
    for f in files:
        if "." in f:
            ext = f.rsplit(".", 1)[-1].lower()
            extensions[ext] = extensions.get(ext, 0) + 1
    return dict(sorted(extensions.items(), key=lambda x: -x[1])[:10])
