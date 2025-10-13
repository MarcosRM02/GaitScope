"""
Utility functions for loading heatmap data.

Provides functions to load sensor coordinates and pressure sequences
from JSON and CSV files for heatmap visualization.
"""

import os
import json
from typing import List, Tuple, Optional


def load_heatmap_coordinates(json_path: str) -> List[Tuple[float, float]]:
    """
    Load sensor coordinates from JSON file.
    
    Args:
        json_path: Path to JSON file containing sensor coordinates
        
    Returns:
        List of (x, y) coordinate tuples
    """
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Handle different JSON formats
        if isinstance(data, list):
            # Direct list of coordinates
            return [(float(pt[0]), float(pt[1])) for pt in data]
        elif isinstance(data, dict):
            # Dictionary with 'coordinates' or 'points' key
            coords = data.get('coordinates') or data.get('points') or []
            return [(float(pt[0]), float(pt[1])) for pt in coords]
        else:
            return []
    except Exception as e:
        print(f"[HeatmapUtils] Error loading coordinates from {json_path}: {e}", flush=True)
        return []


def load_heatmap_sequence(csv_path: str) -> List[List[int]]:
    """
    Load pressure sequence from CSV file.
    
    Args:
        csv_path: Path to CSV file containing pressure values
        
    Returns:
        List of frames, where each frame is a list of pressure values
    """
    try:
        import pandas as pd
        
        # Read CSV
        df = pd.read_csv(csv_path, header=None)
        
        # Convert to list of lists
        sequence = []
        for _, row in df.iterrows():
            # Convert row to list of integers
            frame = [int(val) for val in row.values if pd.notna(val)]
            sequence.append(frame)
        
        return sequence
    except Exception as e:
        print(f"[HeatmapUtils] Error loading sequence from {csv_path}: {e}", flush=True)
        return []


def find_heatmap_data(base_dir: str) -> Optional[dict]:
    """
    Find heatmap data files in a directory.
    
    Looks for:
    - leftPoints.json / L.json / left.json (left sensor coordinates)
    - rightPoints.json / R.json / right.json (right sensor coordinates)
    - L.csv (left pressure sequence)
    - R.csv (right pressure sequence)
    
    Args:
        base_dir: Base directory to search in
        
    Returns:
        Dictionary with paths to found files, or None if insufficient data
    """
    result = {
        'left_coords': None,
        'right_coords': None,
        'left_seq': None,
        'right_seq': None
    }
    
    # Look for coordinate files
    left_coord_candidates = ['leftPoints.json', 'L.json', 'left.json']
    right_coord_candidates = ['rightPoints.json', 'R.json', 'right.json']
    
    for fname in left_coord_candidates:
        path = os.path.join(base_dir, fname)
        if os.path.exists(path):
            result['left_coords'] = path
            break
    
    for fname in right_coord_candidates:
        path = os.path.join(base_dir, fname)
        if os.path.exists(path):
            result['right_coords'] = path
            break
    
    # Look for sequence CSV files
    left_csv = os.path.join(base_dir, 'L.csv')
    right_csv = os.path.join(base_dir, 'R.csv')
    
    if os.path.exists(left_csv):
        result['left_seq'] = left_csv
    
    if os.path.exists(right_csv):
        result['right_seq'] = right_csv
    
    # Check if we have minimum required data
    has_data = (result['left_coords'] or result['right_coords']) and \
               (result['left_seq'] or result['right_seq'])
    
    return result if has_data else None


def load_heatmap_data_from_directory(base_dir: str) -> Optional[dict]:
    """
    Load all heatmap data from a directory.
    
    Args:
        base_dir: Directory containing heatmap data files
        
    Returns:
        Dictionary with loaded data:
        {
            'left_coords': List[Tuple[float, float]],
            'right_coords': List[Tuple[float, float]],
            'left_seq': List[List[int]],
            'right_seq': List[List[int]]
        }
        Returns None if data cannot be loaded.
    """
    # Find files
    files = find_heatmap_data(base_dir)
    if not files:
        print(f"[HeatmapUtils] No heatmap data found in {base_dir}", flush=True)
        return None
    
    # Load data
    data = {
        'left_coords': [],
        'right_coords': [],
        'left_seq': [],
        'right_seq': []
    }
    
    if files['left_coords']:
        data['left_coords'] = load_heatmap_coordinates(files['left_coords'])
        print(f"[HeatmapUtils] Loaded {len(data['left_coords'])} left coordinates", flush=True)
    
    if files['right_coords']:
        data['right_coords'] = load_heatmap_coordinates(files['right_coords'])
        print(f"[HeatmapUtils] Loaded {len(data['right_coords'])} right coordinates", flush=True)
    
    if files['left_seq']:
        data['left_seq'] = load_heatmap_sequence(files['left_seq'])
        print(f"[HeatmapUtils] Loaded {len(data['left_seq'])} left frames", flush=True)
    
    if files['right_seq']:
        data['right_seq'] = load_heatmap_sequence(files['right_seq'])
        print(f"[HeatmapUtils] Loaded {len(data['right_seq'])} right frames", flush=True)
    
    return data
