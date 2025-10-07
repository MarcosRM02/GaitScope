"""
Data manager module.

Handles loading and processing of CSV data files and GaitRite data.
Manages all data-related operations separate from UI logic.
"""

import os
from typing import Optional, List, Tuple
import numpy as np
import pandas as pd

from ..constants import (
    DEFAULT_COLUMNS_PER_GROUP,
    DEFAULT_NUMBER_OF_GROUPS,
    DEFAULT_MAX_COLUMNS,
    DEFAULT_CSV_SAMPLING_RATE,
    GAITRITE_FILE_NAME,
    FOOTPRINT_FILE_NAMES,
)


class DataManager:
    """
    Manager for CSV data and GaitRite analysis data.
    
    This class handles loading, processing, and managing all data files
    including pressure sensor CSV files and GaitRite footprint data.
    """
    
    def __init__(self):
        """Initialize the data manager with default values."""
        self.csv_sampling_rate: float = DEFAULT_CSV_SAMPLING_RATE
        self.csv_len: int = 0
        
        # Processed data arrays for left and right sides
        self.sums_L: Optional[List[np.ndarray]] = None
        self.sums_R: Optional[List[np.ndarray]] = None
        
        # GaitRite data
        self.gaitrite_df: Optional[pd.DataFrame] = None
        self.footprints_left_df: Optional[pd.DataFrame] = None
        self.footprints_right_df: Optional[pd.DataFrame] = None
        
    def load_csv_data(self, csv_path_L: str, csv_path_R: Optional[str] = None) -> bool:
        """
        Load and process CSV data files.
        
        Args:
            csv_path_L: Path to left side CSV file
            csv_path_R: Optional path to right side CSV file
            
        Returns:
            True if data loaded successfully, False otherwise
        """
        try:
            df_L = pd.read_csv(csv_path_L, header=0)
        except Exception as e:
            print(f"[DataManager] Error reading L.csv: {e}", flush=True)
            return False
        
        # Limit columns to maximum
        max_col_L = min(DEFAULT_MAX_COLUMNS, df_L.shape[1])
        if max_col_L < 1:
            return False
        dfL_sel = df_L.iloc[:, 0:max_col_L]
        
        # Try to load right side CSV
        df_R = None
        if csv_path_R and os.path.exists(csv_path_R):
            try:
                df_R = pd.read_csv(csv_path_R, header=0)
            except Exception:
                df_R = None
        
        if df_R is not None:
            max_col_R = min(DEFAULT_MAX_COLUMNS, df_R.shape[1])
            dfR_sel = df_R.iloc[:, 0:max_col_R] if max_col_R >= 1 else pd.DataFrame()
        else:
            dfR_sel = pd.DataFrame()
        
        # Calculate dimensions
        len_L = dfL_sel.shape[0]
        len_R = dfR_sel.shape[0] if not dfR_sel.empty else 0
        self.csv_len = max(len_L, len_R, 1)
        
        # Process left side data
        self.sums_L = self._compute_group_sums(dfL_sel, self.csv_len)
        
        # Process right side data
        if not dfR_sel.empty:
            self.sums_R = self._compute_group_sums(dfR_sel, self.csv_len)
        else:
            # Create empty arrays for right side if no data
            self.sums_R = [
                np.zeros(self.csv_len, dtype=float) 
                for _ in range(DEFAULT_NUMBER_OF_GROUPS)
            ]
        
        print(f"[DataManager] Loaded CSV data: L={len_L} samples, R={len_R} samples", flush=True)
        return True
    
    def _compute_group_sums(self, df: pd.DataFrame, target_length: int) -> List[np.ndarray]:
        """
        Compute summed values for each group of columns.
        
        Args:
            df: DataFrame containing sensor data
            target_length: Target length for output arrays (for padding)
            
        Returns:
            List of numpy arrays, one per group
        """
        sums = []
        n_cols = df.shape[1]
        
        for group_idx in range(DEFAULT_NUMBER_OF_GROUPS):
            start = group_idx * DEFAULT_COLUMNS_PER_GROUP
            end = min(start + DEFAULT_COLUMNS_PER_GROUP, n_cols)
            
            if start >= n_cols:
                # No data for this group, create zeros
                y_sum = np.zeros(target_length, dtype=float)
            else:
                # Extract group columns and sum
                group_df = df.iloc[:, start:end].fillna(0).astype(float)
                arr = group_df.to_numpy()
                
                # Pad if necessary
                if arr.shape[0] < target_length:
                    pad = np.zeros((target_length - arr.shape[0], arr.shape[1]), dtype=float)
                    arr = np.vstack([arr, pad])
                
                y_sum = arr.sum(axis=1)
            
            sums.append(y_sum)
        
        return sums
    
    def load_gaitrite_data(self, base_directory: str) -> bool:
        """
        Load GaitRite data files.
        
        Args:
            base_directory: Directory containing gaitrite data files
            
        Returns:
            True if any data loaded successfully, False otherwise
        """
        gait_file = os.path.join(base_directory, GAITRITE_FILE_NAME)
        
        # Load main gaitrite file
        if os.path.exists(gait_file):
            try:
                try:
                    self.gaitrite_df = pd.read_csv(gait_file, delimiter=';')
                except Exception:
                    self.gaitrite_df = pd.read_csv(gait_file)
                print(f"[DataManager] Loaded GaitRite data: {gait_file}", flush=True)
            except Exception as e:
                print(f"[DataManager] Error loading GaitRite data: {e}", flush=True)
                self.gaitrite_df = None
        
        # Load footprint contours
        left_fp_paths = [os.path.join(base_directory, name) for name in FOOTPRINT_FILE_NAMES['left']]
        right_fp_paths = [os.path.join(base_directory, name) for name in FOOTPRINT_FILE_NAMES['right']]
        
        # Try to find left footprints
        for path in left_fp_paths:
            if os.path.exists(path):
                try:
                    self.footprints_left_df = pd.read_csv(path)
                    print(f"[DataManager] Loaded left footprints: {path}", flush=True)
                    break
                except Exception:
                    pass
        
        # Try to find right footprints
        for path in right_fp_paths:
            if os.path.exists(path):
                try:
                    self.footprints_right_df = pd.read_csv(path)
                    print(f"[DataManager] Loaded right footprints: {path}", flush=True)
                    break
                except Exception:
                    pass
        
        return (self.gaitrite_df is not None or 
                self.footprints_left_df is not None or 
                self.footprints_right_df is not None)
    
    def get_time_axis(self) -> np.ndarray:
        """
        Get time axis array in seconds.
        
        Returns:
            Numpy array of time values in seconds
        """
        if self.csv_sampling_rate > 0:
            return np.arange(self.csv_len) / float(self.csv_sampling_rate)
        return np.arange(self.csv_len)
    
    def video_frame_to_csv_index(self, video_frame: int, video_fps: float) -> int:
        """
        Map video frame number to CSV sample index.
        
        Args:
            video_frame: Video frame number
            video_fps: Video frames per second
            
        Returns:
            Corresponding CSV sample index
        """
        if video_fps <= 0 or self.csv_sampling_rate <= 0:
            return 0
        
        t = float(video_frame) / float(video_fps)
        idx = int(round(t * float(self.csv_sampling_rate)))
        
        if self.csv_len:
            idx = max(0, min(idx, self.csv_len - 1))
        else:
            idx = max(0, idx)
        
        return idx
    
    def clear_data(self):
        """Clear all loaded data."""
        self.sums_L = None
        self.sums_R = None
        self.csv_len = 0
        self.gaitrite_df = None
        self.footprints_left_df = None
        self.footprints_right_df = None
