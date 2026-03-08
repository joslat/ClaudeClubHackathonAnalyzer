"""Path helpers, safe file reads, and size utilities."""

import os
from pathlib import Path
from typing import Optional

# Directories to skip when walking repo trees
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".mypy_cache", ".pytest_cache", "target",
    ".gradle", ".idea", ".vscode", "vendor",
}


def walk_repo(root: Path):
    """os.walk the repo, skipping common noise directories."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        yield Path(dirpath), dirnames, filenames


def get_dir_size_mb(path: Path) -> float:
    """Return total size of a directory in megabytes."""
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = Path(dirpath) / f
            try:
                total += fp.stat().st_size
            except OSError:
                pass
    return total / (1024 * 1024)


def safe_read_text(path: Path, max_bytes: int = 500_000) -> Optional[str]:
    """Read a text file safely, truncating at max_bytes. Returns None on error."""
    try:
        raw = path.read_bytes()
        raw = raw[:max_bytes]
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return None


def find_file_icase(directory: Path, names: list[str]) -> Optional[Path]:
    """Find a file in directory by case-insensitive name match."""
    try:
        entries = list(directory.iterdir())
    except OSError:
        return None
    lower_names = {n.lower() for n in names}
    for entry in entries:
        if entry.name.lower() in lower_names:
            return entry
    return None


def count_lines(path: Path) -> int:
    """Count non-empty lines in a file. Returns 0 on error."""
    try:
        text = path.read_bytes()
        return sum(1 for line in text.split(b"\n") if line.strip())
    except OSError:
        return 0
