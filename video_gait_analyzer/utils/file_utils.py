"""
File system utilities for discovering and managing data files.

This module provides functions for finding video files, CSV data files,
and discovering dataset directories.
"""

import os
from typing import List, Tuple, Optional
from ..constants import VIDEO_EXTENSIONS, EXCLUDED_DIRECTORIES


def find_video_file(directory: str) -> Optional[str]:
    """
    Find the first video file in the specified directory.
    
    Searches first in the directory itself, then recursively if not found.
    Skips excluded directories (SITDOWN, STAND).
    
    Args:
        directory: Path to directory to search
        
    Returns:
        Absolute path to video file if found, None otherwise
    """
    if not os.path.isdir(directory):
        return None
    
    # First, check files in the directory itself
    try:
        for filename in sorted(os.listdir(directory)):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                if any(filename.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                    return file_path
    except Exception:
        pass
    
    # If not found, search recursively
    try:
        for dirpath, dirnames, filenames in os.walk(directory):
            # Skip excluded directories
            dirnames[:] = [d for d in dirnames if d.lower() not in EXCLUDED_DIRECTORIES]
            
            for filename in filenames:
                if any(filename.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                    return os.path.join(dirpath, filename)
    except Exception:
        pass
    
    return None


def find_csv_file(directory: str, filename: str = 'L.csv') -> Optional[str]:
    """
    Find a specific CSV file in the directory.
    
    Searches first in the directory itself, then recursively if not found.
    
    Args:
        directory: Path to directory to search
        filename: Name of CSV file to find (default: 'L.csv')
        
    Returns:
        Absolute path to CSV file if found, None otherwise
    """
    if not os.path.isdir(directory):
        return None
    
    # First, check files in the directory itself
    target = os.path.join(directory, filename)
    if os.path.exists(target):
        return target
    
    # If not found, search recursively
    try:
        for dirpath, dirnames, filenames in os.walk(directory):
            # Skip excluded directories
            dirnames[:] = [d for d in dirnames if d.lower() not in EXCLUDED_DIRECTORIES]
            
            if filename in filenames:
                return os.path.join(dirpath, filename)
    except Exception:
        pass
    
    return None


def discover_datasets(base_directory: str, max_depth: int = 3) -> List[Tuple[str, str]]:
    """
    Discover dataset directories containing video or CSV files.
    
    Searches for directories containing either video files or L.csv files
    up to a specified depth.
    
    Args:
        base_directory: Root directory to start search
        max_depth: Maximum directory depth to search (default: 3)
        
    Returns:
        List of tuples (label, absolute_path) for each discovered dataset
        
    Example:
        >>> datasets = discover_datasets('/data')
        >>> for label, path in datasets:
        ...     print(f"Dataset: {label} at {path}")
    """
    results = []
    seen = set()
    
    if not os.path.isdir(base_directory):
        return results
    
    try:
        for dirpath, dirnames, filenames in os.walk(base_directory):
            # Compute depth relative to base
            rel_path = os.path.relpath(dirpath, base_directory)
            depth = 0 if rel_path == '.' else rel_path.count(os.sep) + 1
            
            if depth > max_depth:
                # Prune deeper directories
                dirnames[:] = []
                continue
            
            # Check for video or CSV presence
            has_video = any(f.lower().endswith(tuple(VIDEO_EXTENSIONS)) for f in filenames)
            has_csv = any(f.lower() == 'l.csv' or f.lower().endswith('l.csv') for f in filenames)
            
            if has_video or has_csv:
                abs_path = os.path.abspath(dirpath)
                if abs_path not in seen:
                    seen.add(abs_path)
                    label = os.path.relpath(dirpath, base_directory)
                    results.append((label, abs_path))
    except Exception:
        pass
    
    # Sort results for deterministic ordering
    results.sort()
    return results
