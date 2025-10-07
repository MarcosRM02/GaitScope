"""
Plot manager module.

Handles all plotting and visualization operations including:
- CSV data plots with multiple groups
- GaitRite footprint visualization
- Cursor synchronization with video
- Plot updates and animations
"""

from typing import Optional, List
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets

from ..constants import (
    PLOT_COLORS,
    DEFAULT_R_OFFSET,
    CURSOR_COLOR,
    MARKER_LEFT_COLOR,
    MARKER_RIGHT_COLOR,
    FOOTPRINT_LEFT_COLOR,
    FOOTPRINT_RIGHT_COLOR,
    CARPET_WIDTH_CM,
    CARPET_LENGTH_CM,
    CARPET_BACKGROUND_COLOR,
    CARPET_BORDER_COLOR,
    PLOT_UPDATE_INTERVAL,
)


class PlotManager:
    """
    Manager for all plot visualization operations.
    
    This class handles creating and updating all plots including
    CSV data visualization and GaitRite footprint displays.
    """
    
    def __init__(self, plot_widget: pg.PlotWidget, gaitrite_plot: pg.PlotWidget):
        """
        Initialize the plot manager.
        
        Args:
            plot_widget: Main plot widget for CSV data
            gaitrite_plot: Plot widget for GaitRite visualization
        """
        self.plot_widget = plot_widget
        self.gaitrite_plot = gaitrite_plot
        
        # Plot items
        self.plot_items_L: List = []
        self.plot_items_R: List = []
        
        # Cursor elements
        self.cursor_line: Optional[pg.InfiniteLine] = None
        self.cursor_segment: Optional[pg.PlotDataItem] = None
        self.scatter_L: Optional[pg.ScatterPlotItem] = None
        self.scatter_R: Optional[pg.ScatterPlotItem] = None
        
        # Configuration
        self.r_offset: float = DEFAULT_R_OFFSET
        self.marker_group_index_L: int = 0
        self.marker_group_index_R: int = 0
        
        # Update throttling
        self._last_plot_update: float = 0.0
        self._plot_update_interval: float = PLOT_UPDATE_INTERVAL
        
    def create_csv_plots(self, x_data: np.ndarray, sums_L: List[np.ndarray], 
                         sums_R: List[np.ndarray], r_offset: float = None):
        """
        Create plots for CSV data (both left and right sides).
        
        Args:
            x_data: X-axis data (time in seconds)
            sums_L: List of summed arrays for left side groups
            sums_R: List of summed arrays for right side groups
            r_offset: Vertical offset for right side data (optional)
        """
        if r_offset is not None:
            self.r_offset = r_offset
        
        self.plot_widget.clear()
        self.plot_items_L = []
        self.plot_items_R = []
        
        # Plot each group
        for group_idx in range(len(sums_L)):
            # Left side
            y_L = sums_L[group_idx]
            pen_L = pg.mkPen(PLOT_COLORS[group_idx % len(PLOT_COLORS)], width=2)
            plot_item_L = self.plot_widget.plot(
                x_data, y_L, pen=pen_L, 
                name=f'L Group {group_idx+1}'
            )
            self.plot_items_L.append(plot_item_L)
            
            # Right side
            if group_idx < len(sums_R):
                y_R = sums_R[group_idx] - self.r_offset
                pen_R = pg.mkPen(
                    PLOT_COLORS[group_idx % len(PLOT_COLORS)], 
                    width=2, 
                    style=QtCore.Qt.DashLine
                )
                plot_item_R = self.plot_widget.plot(
                    x_data, y_R, pen=pen_R, 
                    name=f'R Group {group_idx+1}'
                )
                self.plot_items_R.append(plot_item_R)
        
        # Create scatter items for markers
        self._create_scatter_items()
        
        # Create cursor segment
        self._create_cursor_segment()
    
    def _create_scatter_items(self):
        """Create scatter plot items for position markers."""
        if self.scatter_L is None:
            self.scatter_L = pg.ScatterPlotItem(
                size=10, 
                brush=pg.mkBrush(*MARKER_LEFT_COLOR), 
                pen=pg.mkPen('k')
            )
            self.plot_widget.addItem(self.scatter_L)
            self.scatter_L.setData(x=[], y=[])
            self.scatter_L.setVisible(False)
        
        if self.scatter_R is None:
            self.scatter_R = pg.ScatterPlotItem(
                size=10, 
                brush=pg.mkBrush(*MARKER_RIGHT_COLOR), 
                pen=pg.mkPen('k')
            )
            self.plot_widget.addItem(self.scatter_R)
            self.scatter_R.setData(x=[], y=[])
            self.scatter_R.setVisible(False)
    
    def _create_cursor_segment(self):
        """Create cursor segment connecting L and R positions."""
        if self.cursor_segment is None:
            try:
                seg_pen = pg.mkPen(color=CURSOR_COLOR, width=4)
                self.cursor_segment = pg.PlotDataItem(pen=seg_pen)
                self.plot_widget.addItem(self.cursor_segment)
                try:
                    self.cursor_segment.setZValue(10**6)
                except Exception:
                    pass
                self.cursor_segment.setData(x=[], y=[])
            except Exception:
                self.cursor_segment = None
    
    def update_cursor_position(self, csv_time: float, sums_L: List[np.ndarray], 
                               sums_R: List[np.ndarray], csv_idx: int):
        """
        Update cursor position on plot.
        
        Args:
            csv_time: Current time in seconds
            sums_L: Left side data arrays
            sums_R: Right side data arrays
            csv_idx: Current CSV sample index
        """
        import time
        
        # Update or create vertical cursor line
        if self.cursor_line is None:
            try:
                pen_line = pg.mkPen(color=CURSOR_COLOR, width=2)
            except Exception:
                pen_line = pg.mkPen('y', width=2)
            
            self.cursor_line = pg.InfiniteLine(pos=csv_time, angle=90, pen=pen_line)
            try:
                vb = self.plot_widget.getViewBox()
                vb.addItem(self.cursor_line)
            except Exception:
                self.plot_widget.addItem(self.cursor_line)
            try:
                self.cursor_line.setZValue(10**6)
            except Exception:
                pass
        else:
            try:
                self.cursor_line.setPos(csv_time)
            except Exception:
                pass
        
        # Calculate Y positions for L and R
        try:
            gi_L = max(0, min(int(self.marker_group_index_L), len(sums_L) - 1))
            arr_L = sums_L[gi_L]
            y_L = float(arr_L[csv_idx]) if csv_idx < arr_L.shape[0] else float(arr_L[-1])
        except Exception:
            y_L = 0.0
        
        try:
            if sums_R and len(sums_R) > 0:
                gi_R = max(0, min(int(self.marker_group_index_R), len(sums_R) - 1))
                arr_R = sums_R[gi_R]
                y_R = float(arr_R[csv_idx]) if csv_idx < arr_R.shape[0] else float(arr_R[-1])
                y_R_shifted = y_R - float(self.r_offset)
            else:
                y_R_shifted = 0.0 - float(self.r_offset)
        except Exception:
            y_R_shifted = 0.0 - float(self.r_offset)
        
        # Update cursor segment connecting L and R
        if self.cursor_segment is not None:
            try:
                self.cursor_segment.setData(x=[csv_time, csv_time], y=[y_R_shifted, y_L])
            except Exception:
                pass
    
    def set_plot_x_range(self, x_min: float, x_max: float):
        """
        Set X-axis range for main plot.
        
        Args:
            x_min: Minimum X value
            x_max: Maximum X value
        """
        try:
            self.plot_widget.setXRange(x_min, x_max, padding=0)
        except Exception:
            pass
    
    def draw_gaitrite_carpet(self, show_text: bool = True):
        """
        Draw GaitRite carpet background.
        
        Args:
            show_text: Whether to show placeholder text
        """
        try:
            self.gaitrite_plot.clear()
            carpet_w = float(CARPET_WIDTH_CM)
            carpet_h = float(CARPET_LENGTH_CM)
            
            bg_x = [0, carpet_w, carpet_w, 0, 0]
            bg_y = [0, 0, carpet_h, carpet_h, 0]
            
            self.gaitrite_plot.plot(
                bg_x, bg_y, 
                pen=pg.mkPen(CARPET_BORDER_COLOR, width=2), 
                fillLevel=0,
                brush=pg.mkBrush(*CARPET_BACKGROUND_COLOR)
            )
            
            if show_text:
                txt = pg.TextItem(
                    "GaitRite Carpet\n(placeholder)", 
                    anchor=(0.5, 0.5), 
                    color='#7F8C8D'
                )
                txt.setPos(carpet_w / 2.0, carpet_h / 2.0)
                self.gaitrite_plot.addItem(txt)
            
            # Set view limits
            try:
                self.gaitrite_plot.disableAutoRange()
                padding_x = max(1.0, carpet_w * 0.05)
                padding_y = max(1.0, carpet_h * 0.05)
                self.gaitrite_plot.setXRange(-padding_x, carpet_w + padding_x, padding=0)
                self.gaitrite_plot.setYRange(-padding_y, carpet_h + padding_y, padding=0)
            except Exception:
                pass
        except Exception:
            pass
    
    def draw_gaitrite_footprints(self, footprints_left_df, footprints_right_df, 
                                  gaitrite_df=None):
        """
        Draw GaitRite footprint contours and trajectory.
        
        Args:
            footprints_left_df: DataFrame with left footprint data
            footprints_right_df: DataFrame with right footprint data
            gaitrite_df: DataFrame with gaitrite_test.csv data for trajectory (optional)
        """
        self.gaitrite_plot.clear()
        self.draw_gaitrite_carpet(show_text=False)
        
        # Draw footprints
        for df, color in [(footprints_left_df, FOOTPRINT_LEFT_COLOR), 
                          (footprints_right_df, FOOTPRINT_RIGHT_COLOR)]:
            if df is None or df.empty:
                continue
            
            try:
                # Determine grouping column
                if 'gait_id' in df.columns:
                    group_col = 'gait_id'
                elif 'Gait_Id' in df.columns:
                    group_col = 'Gait_Id'
                else:
                    group_col = None
                
                if group_col is not None:
                    for gv, grp in df.groupby(group_col):
                        if 'event' in grp.columns:
                            for ev, g2 in grp.groupby('event'):
                                self._plot_footprint_group(g2, color)
                        else:
                            self._plot_footprint_group(grp, color)
                else:
                    self._plot_footprint_group(df, color)
            except Exception:
                continue
        
        # Draw trajectory from gaitrite_test.csv
        self._draw_gaitrite_trajectory(gaitrite_df)
    
    def _draw_gaitrite_trajectory(self, gaitrite_df):
        """
        Draw trajectory line from gaitrite_test.csv data.
        
        Args:
            gaitrite_df: DataFrame with gaitrite_test.csv data
        """
        if gaitrite_df is None or gaitrite_df.empty:
            return
        
        traj_x = []
        traj_y = []
        
        try:
            # Use gaitrite_test.csv to compute trajectory centers
            from ..constants import GAITRITE_CONVERSION_FACTOR
            
            # Compute centers using midpoints from expected columns
            if all(c in gaitrite_df.columns for c in ('Ybottom', 'Ytop', 'Xback', 'Xfront')):
                ctr_x = (((gaitrite_df['Ybottom'].astype(float) + 
                          gaitrite_df['Ytop'].astype(float)) / 2.0) * 
                         GAITRITE_CONVERSION_FACTOR).values
                ctr_y = (((gaitrite_df['Xback'].astype(float) + 
                          gaitrite_df['Xfront'].astype(float)) / 2.0) * 
                         GAITRITE_CONVERSION_FACTOR).values
                traj_x = list(ctr_x)
                traj_y = list(ctr_y)
            else:
                # Try alternative column names if present
                import pandas as pd
                alt_x = next((c for c in gaitrite_df.columns if c.lower().startswith('y')), None)
                alt_y = next((c for c in gaitrite_df.columns if c.lower().startswith('x')), None)
                if alt_x is not None and alt_y is not None:
                    try:
                        traj_x = list(pd.to_numeric(
                            gaitrite_df[alt_x], errors='coerce'
                        ).dropna().astype(float).values)
                        traj_y = list(pd.to_numeric(
                            gaitrite_df[alt_y], errors='coerce'
                        ).dropna().astype(float).values)
                    except Exception:
                        traj_x = []
                        traj_y = []
        except Exception:
            pass
        
        # Draw trajectory if we have valid data
        if len(traj_x) > 1:
            try:
                # Draw trajectory line in black
                self.gaitrite_plot.plot(
                    traj_x, traj_y, 
                    pen=pg.mkPen('black', width=2)
                )
                
                # Mark start point (green) and end point (red)
                try:
                    start_point = pg.ScatterPlotItem(
                        size=8, 
                        brush=pg.mkBrush(0, 200, 0),  # Green
                        pen=pg.mkPen('k')
                    )
                    end_point = pg.ScatterPlotItem(
                        size=8, 
                        brush=pg.mkBrush(200, 0, 0),  # Red
                        pen=pg.mkPen('k')
                    )
                    start_point.setData(x=[traj_x[0]], y=[traj_y[0]])
                    end_point.setData(x=[traj_x[-1]], y=[traj_y[-1]])
                    self.gaitrite_plot.addItem(start_point)
                    self.gaitrite_plot.addItem(end_point)
                except Exception:
                    pass
            except Exception:
                pass
    
    def _plot_footprint_group(self, df, color):
        """
        Plot a single footprint group.
        
        Args:
            df: DataFrame with footprint coordinates
            color: Color for the footprint
        """
        try:
            if 'sample_idx' in df.columns:
                df_sorted = df.sort_values('sample_idx')
            else:
                df_sorted = df
            
            if 'x_cm' in df_sorted.columns and 'y_cm' in df_sorted.columns:
                self.gaitrite_plot.plot(
                    df_sorted['x_cm'].values, 
                    df_sorted['y_cm'].values,
                    pen=pg.mkPen(color=color, width=2)
                )
        except Exception:
            pass
    
    def clear_plots(self):
        """Clear all plot items."""
        self.plot_widget.clear()
        self.gaitrite_plot.clear()
        self.plot_items_L = []
        self.plot_items_R = []
        self.cursor_line = None
        self.cursor_segment = None
