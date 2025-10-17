"""
File system utilities for discovering and managing data files.

This module provides pathlib-based functions for finding video files, CSV
files, and discovering dataset directories in a cross-platform way.
"""

from pathlib import Path
from typing import List, Tuple, Optional
from ..constants import VIDEO_EXTENSIONS, EXCLUDED_DIRECTORIES


def _is_excluded_dir(name: str) -> bool:
    return name.lower() in EXCLUDED_DIRECTORIES


def find_video_file(directory: str) -> Optional[str]:
    """
    Find the first video file in the specified directory.

    Uses pathlib for cross-platform path handling. Returns an absolute
    string path or None if not found.
    """
    try:
        base = Path(directory).expanduser().resolve()
    except Exception:
        return None

    if not base.is_dir():
        return None

    # Check files in the directory itself first (sorted for determinism)
    try:
        for p in sorted(base.iterdir(), key=lambda p: p.name.lower()):
            if p.is_file():
                fname_lower = p.name.lower()
                if any(fname_lower.endswith(ext) for ext in VIDEO_EXTENSIONS) and 'anonym' in fname_lower:
                    return str(p)
    except Exception:
        pass

    # If not found, walk the tree but skip excluded directories
    try:
        for root, dirs, files in os_walk_with_excludes(base):
            for f in sorted(files, key=lambda s: s.lower()):
                fname_lower = f.lower()
                if any(fname_lower.endswith(ext) for ext in VIDEO_EXTENSIONS) and 'anonym' in fname_lower:
                    return str(Path(root) / f)
    except Exception:
        pass

    return None


def find_csv_file(directory: str, filename: str = 'L.csv') -> Optional[str]:
    """
    Find a specific CSV file in the directory.

    Searches first in the directory itself, then recursively if not found.
    Returns absolute string path or None.
    """
    try:
        base = Path(directory).expanduser().resolve()
    except Exception:
        return None

    if not base.is_dir():
        return None

    target = base / filename
    if target.exists():
        return str(target)

    try:
        for root, dirs, files in os_walk_with_excludes(base):
            if filename in files:
                return str(Path(root) / filename)
    except Exception:
        pass

    return None


def discover_datasets(base_directory: str, max_depth: int = 3) -> List[Tuple[str, str]]:
    """
    Discover dataset directories containing video or CSV files.

    Returns list of tuples (label, absolute_path) where label is the
    relative path from base_directory.
    """
    results = []
    seen = set()

    try:
        base = Path(base_directory).expanduser().resolve()
    except Exception:
        return results

    if not base.is_dir():
        return results

    try:
        for root, dirs, files in os_walk_with_excludes(base):
            root_path = Path(root)
            try:
                rel = root_path.relative_to(base)
                depth = 0 if str(rel) == '.' else len(rel.parts)
            except Exception:
                depth = 0

            if depth > max_depth:
                # don't descend further
                dirs[:] = []
                continue

            has_video = any((f.lower().endswith(tuple(VIDEO_EXTENSIONS)) and 'anonym' in f.lower()) for f in files)
            has_csv = any(f.lower() == 'l.csv' or f.lower().endswith('l.csv') for f in files)

            if has_video or has_csv:
                abs_path = str(root_path)
                if abs_path not in seen:
                    seen.add(abs_path)
                    label = str(root_path.relative_to(base))
                    results.append((label, abs_path))
    except Exception:
        pass

    results.sort()
    return results


# Helper: os.walk wrapper that yields directories/files but skips excluded names
def os_walk_with_excludes(base_path: Path):
    """Yield (root, dirs, files) while skipping excluded directories."""
    # Use a generator based on os.walk to preserve behavior across platforms
    import os

    for root, dirs, files in os.walk(str(base_path)):
        # mutate dirs in-place to prevent walking into excluded directories
        dirs[:] = [d for d in dirs if not _is_excluded_dir(d)]
        yield root, dirs, files
