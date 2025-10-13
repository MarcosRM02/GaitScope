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
    GAITRITE_CONVERSION_FACTOR,
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
        
        # Raw CSV data for heatmap (NEW)
        self.raw_data_L: Optional[pd.DataFrame] = None
        self.raw_data_R: Optional[pd.DataFrame] = None
        
        # Sensor coordinates for heatmap (loaded once at startup)
        self.sensor_coords_L: Optional[List[Tuple[float, float]]] = None
        self.sensor_coords_R: Optional[List[Tuple[float, float]]] = None
        
        # GaitRite data
        self.gaitrite_df: Optional[pd.DataFrame] = None
        self.footprints_left_df: Optional[pd.DataFrame] = None
        self.footprints_right_df: Optional[pd.DataFrame] = None
        
        # Load sensor coordinates once at initialization
        self._load_global_sensor_coordinates()
        
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
        
        # Store raw data for heatmap (NEW)
        self.raw_data_L = dfL_sel.copy()
        
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
            # Store raw data for heatmap (NEW)
            self.raw_data_R = dfR_sel.copy()
        else:
            dfR_sel = pd.DataFrame()
            self.raw_data_R = None
        
        # Calculate dimensions
        len_L = dfL_sel.shape[0]
        len_R = dfR_sel.shape[0] if not dfR_sel.empty else 0
        self.csv_len = max(len_L, len_R, 1)
        
        # Process left side data
        # If we have a full 32-column layout, use the custom grouping (forefoot/midfoot/hindfoot)
        from ..constants import (
            LEFT_FOREFOOT_INDICES,
            LEFT_MIDFOOT_INDICES,
            LEFT_HINDFOOT_INDICES,
            RIGHT_FOREFOOT_INDICES,
            RIGHT_MIDFOOT_INDICES,
            RIGHT_HINDFOOT_INDICES,
        )

        if dfL_sel.shape[1] >= 32:
            self.sums_L = self._compute_group_sums_from_indices(dfL_sel, [LEFT_FOREFOOT_INDICES, LEFT_MIDFOOT_INDICES, LEFT_HINDFOOT_INDICES], self.csv_len)
        else:
            self.sums_L = self._compute_group_sums(dfL_sel, self.csv_len)
         
        # Process right side data
        if not dfR_sel.empty:
            if dfR_sel.shape[1] >= 32:
                self.sums_R = self._compute_group_sums_from_indices(dfR_sel, [RIGHT_FOREFOOT_INDICES, RIGHT_MIDFOOT_INDICES, RIGHT_HINDFOOT_INDICES], self.csv_len)
            else:
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
    
    def _compute_group_sums_from_indices(self, df: pd.DataFrame, groups: List[list], target_length: int) -> List[np.ndarray]:
        """
        Compute summed values for custom groups defined by explicit column indices.

        Args:
            df: DataFrame containing sensor data
            groups: List of lists, each inner list contains 0-based column indices for that group
            target_length: Target length for output arrays (for padding)

        Returns:
            List of numpy arrays, one per group
        """
        sums = []
        n_cols = df.shape[1]
        for grp in groups:
            # Filter indices that are in range
            valid_idx = [i for i in grp if 0 <= i < n_cols]
            if not valid_idx:
                y_sum = np.zeros(target_length, dtype=float)
            else:
                try:
                    arr = df.iloc[:, valid_idx].fillna(0).astype(float).to_numpy()
                    # Pad if necessary
                    if arr.shape[0] < target_length:
                        pad = np.zeros((target_length - arr.shape[0], arr.shape[1]), dtype=float)
                        arr = np.vstack([arr, pad])
                    y_sum = arr.sum(axis=1)
                except Exception:
                    y_sum = np.zeros(target_length, dtype=float)
            sums.append(y_sum)
        return sums
    
    def load_gaitrite_data(self, base_directory: str) -> bool:
        """
        Load GaitRite data files. If footprints don't exist, generate them from Yarray.
        
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
        
        # Check if footprint files exist
        left_fp_paths = [os.path.join(base_directory, name) for name in FOOTPRINT_FILE_NAMES['left']]
        right_fp_paths = [os.path.join(base_directory, name) for name in FOOTPRINT_FILE_NAMES['right']]
        
        left_exists = any(os.path.exists(p) for p in left_fp_paths)
        right_exists = any(os.path.exists(p) for p in right_fp_paths)
        
        # Generate footprints if they don't exist (EXACTLY as original)
        if (not left_exists or not right_exists) and os.path.exists(gait_file):
            self._generate_footprints_from_yarray(base_directory, gait_file, left_exists, right_exists)
        
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
    
    def _generate_footprints_from_yarray(self, base_directory: str, gait_file: str,
                                          left_exists: bool, right_exists: bool):
        """
        Generate footprint contours from Yarray column in gaitrite_test.csv.
        EXACTLY replicates original ephy.py behavior.
        
        Args:
            base_directory: Directory where to save generated files
            gait_file: Path to gaitrite_test.csv
            left_exists: Whether left footprints already exist
            right_exists: Whether right footprints already exist
        """
        try:
            # Read gaitrite_test.csv
            try:
                df_g = pd.read_csv(gait_file, delimiter=';')
            except Exception:
                df_g = pd.read_csv(gait_file)
            
            if df_g is None or df_g.empty:
                return
            
            # Check for required columns
            required = {'Gait_Id', 'Event', 'Foot', 'Xback', 'Xfront', 'Ybottom', 'Ytop', 'Yarray'}
            if not required.issubset(set(df_g.columns)):
                print(f"[DataManager] gaitrite_test.csv missing required columns: {required}", flush=True)
                return
            
            # Try to import decoder function
            try:
                from export_yarray_footprints import decode_yarray_to_xy
            except Exception:
                decode_yarray_to_xy = None
            
            # Accumulate footprints by foot (0=left, 1=right)
            accum = {0: [], 1: []}
            
            for _, r in df_g.iterrows():
                try:
                    foot = int(r['Foot']) if pd.notna(r['Foot']) else None
                except Exception:
                    foot = None
                
                if foot not in (0, 1):
                    continue
                
                try:
                    Xback_cm = float(r['Xback']) * GAITRITE_CONVERSION_FACTOR
                    Xfront_cm = float(r['Xfront']) * GAITRITE_CONVERSION_FACTOR
                    Ybottom_cm = float(r['Ybottom']) * GAITRITE_CONVERSION_FACTOR
                    Ytop_cm = float(r['Ytop']) * GAITRITE_CONVERSION_FACTOR
                except Exception:
                    continue
                
                yarray_raw = str(r['Yarray']) if pd.notna(r['Yarray']) else ''
                
                # Decode Yarray to xy points
                if decode_yarray_to_xy is not None:
                    df_xy = decode_yarray_to_xy(yarray_raw, Xback_cm, Xfront_cm, Ybottom_cm, Ytop_cm)
                else:
                    # Fallback implementation (exactly as original)
                    try:
                        vals = np.fromiter((ord(c) for c in yarray_raw), dtype=float, count=len(yarray_raw))
                        if vals.size == 0 or not np.isfinite(vals).all():
                            df_xy = None
                        else:
                            lo = np.percentile(vals, 1)
                            hi = np.percentile(vals, 99)
                            if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
                                lo, hi = float(np.min(vals)), float(np.max(vals))
                            if hi == lo:
                                hi = lo + 1e-9
                            vals_norm = (vals - lo) / (hi - lo)
                            N = vals.shape[0]
                            x_cm = Ybottom_cm + vals_norm * (Ytop_cm - Ybottom_cm)
                            y_cm = np.linspace(Xback_cm, Xfront_cm, N)
                            df_xy = pd.DataFrame({
                                'sample_idx': np.arange(N, dtype=int),
                                'x_cm': x_cm.astype(float),
                                'y_cm': y_cm.astype(float),
                            })
                    except Exception:
                        df_xy = None
                
                if df_xy is None or df_xy.empty:
                    continue
                
                # Add metadata columns
                df_xy = df_xy.copy()
                df_xy['participant'] = os.path.basename(base_directory)
                df_xy['source_file'] = os.path.basename(gait_file)
                df_xy['gait_id'] = int(r['Gait_Id']) if pd.notna(r['Gait_Id']) else None
                df_xy['event'] = int(r['Event']) if pd.notna(r['Event']) else None
                df_xy['foot'] = foot
                df_xy['xback_cm'] = Xback_cm
                df_xy['xfront_cm'] = Xfront_cm
                df_xy['ybottom_cm'] = Ybottom_cm
                df_xy['ytop_cm'] = Ytop_cm
                df_xy['n_samples'] = int(df_xy.shape[0])
                
                accum[foot].append(df_xy)
            
            # Write output files
            generated_any = False
            target_left = os.path.join(base_directory, 'generated_footprints_left.csv')
            target_right = os.path.join(base_directory, 'generated_footprints_right.csv')
            
            if not left_exists and accum[0]:
                out_left = pd.concat(accum[0], ignore_index=True).sort_values(
                    ['gait_id', 'event', 'sample_idx']
                ).reset_index(drop=True)
                out_left.to_csv(target_left, index=False)
                print(f"[DataManager] Generated left footprints: {target_left}", flush=True)
                generated_any = True
            
            if not right_exists and accum[1]:
                out_right = pd.concat(accum[1], ignore_index=True).sort_values(
                    ['gait_id', 'event', 'sample_idx']
                ).reset_index(drop=True)
                out_right.to_csv(target_right, index=False)
                print(f"[DataManager] Generated right footprints: {target_right}", flush=True)
                generated_any = True
            
            if generated_any:
                print(f"[DataManager] Generated footprints from Yarray in gaitrite_test.csv", flush=True)
                
        except Exception as e:
            print(f"[DataManager] Error generating footprints from Yarray: {e}", flush=True)
    
    def _load_global_sensor_coordinates(self):
        """
        Load global sensor coordinate files from the package's `in/` directory.
        
        These coordinates are the same for all participants, so we load them once
        at initialization to improve performance.
        """
        import json
        
        # Get the path to the 'in' directory inside the package root
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        in_dir = os.path.join(current_dir, 'in')
        
        if not os.path.exists(in_dir):
            print(f"[DataManager] Warning: 'in' directory not found at {in_dir}", flush=True)
            return
        
        # Try to load left sensor coordinates
        left_coord_candidates = ['leftPoints.json', 'L.json', 'left.json']
        for fname in left_coord_candidates:
            path = os.path.join(in_dir, fname)
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Handle different JSON formats
                    if isinstance(data, list):
                        # Array of {"x": ..., "y": ...} or [[x, y], ...]
                        coords = []
                        for item in data:
                            if isinstance(item, dict):
                                x = float(item.get('x', 0.0))
                                y = float(item.get('y', 0.0))
                                coords.append((x, y))
                            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                                coords.append((float(item[0]), float(item[1])))
                        self.sensor_coords_L = coords
                    elif isinstance(data, dict):
                        # Dictionary with 'coordinates' or 'points' key
                        coords_data = data.get('coordinates') or data.get('points') or []
                        coords = [(float(pt[0]), float(pt[1])) for pt in coords_data]
                        self.sensor_coords_L = coords
                    
                    print(f"[DataManager] Loaded {len(self.sensor_coords_L)} left sensor coordinates", flush=True)
                    break
                except Exception as e:
                    print(f"[DataManager] Error loading {fname}: {e}", flush=True)
        
        # Try to load right sensor coordinates
        right_coord_candidates = ['rightPoints.json', 'R.json', 'right.json']
        for fname in right_coord_candidates:
            path = os.path.join(in_dir, fname)
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Handle different JSON formats
                    if isinstance(data, list):
                        coords = []
                        for item in data:
                            if isinstance(item, dict):
                                x = float(item.get('x', 0.0))
                                y = float(item.get('y', 0.0))
                                coords.append((x, y))
                            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                                coords.append((float(item[0]), float(item[1])))
                        self.sensor_coords_R = coords
                    elif isinstance(data, dict):
                        coords_data = data.get('coordinates') or data.get('points') or []
                        coords = [(float(pt[0]), float(pt[1])) for pt in coords_data]
                        self.sensor_coords_R = coords
                    
                    print(f"[DataManager] Loaded {len(self.sensor_coords_R)} right sensor coordinates", flush=True)
                    break
                except Exception as e:
                    print(f"[DataManager] Error loading {fname}: {e}", flush=True)
    
    def get_heatmap_data(self) -> Optional[dict]:
        """
        Get raw CSV data and sensor coordinates for heatmap visualization.
        
        Returns:
            Dictionary with heatmap data or None if not available:
            {
                'left_coords': List[Tuple[float, float]],
                'right_coords': List[Tuple[float, float]],
                'left_seq': List[List[int]],
                'right_seq': List[List[int]]
            }
        """
        if self.raw_data_L is None and self.raw_data_R is None:
            return None
        
        # Convert pandas DataFrames to list of lists for heatmap
        left_seq = []
        if self.raw_data_L is not None:
            left_seq = self.raw_data_L.fillna(0).astype(int).values.tolist()
        
        right_seq = []
        if self.raw_data_R is not None:
            right_seq = self.raw_data_R.fillna(0).astype(int).values.tolist()
        
        return {
            'left_coords': self.sensor_coords_L or [],
            'right_coords': self.sensor_coords_R or [],
            'left_seq': left_seq,
            'right_seq': right_seq
        }
    
    def get_time_axis(self) -> np.ndarray:
        """
        Generate time axis array for CSV data based on sampling rate.
        
        Returns:
            Numpy array of time values in seconds
        """
        if self.csv_len <= 0 or self.csv_sampling_rate <= 0:
            return np.array([0.0])
        
        return np.arange(self.csv_len) / self.csv_sampling_rate
    
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
