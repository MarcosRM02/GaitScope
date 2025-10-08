"""
Plot manager module.

Handles all plotting and visualization operations including:
- CSV data plots with multiple groups
- GaitRite footprint visualization
- Cursor synchronization with video
- Plot updates and animations
"""

import time
import numpy as np
import pandas as pd
from typing import Optional, List, Tuple
from PyQt5 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

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
    GAITRITE_CONVERSION_FACTOR,
    SENSOR_GROUP_LABELS,
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
        self.cursor_qline: Optional[QtWidgets.QGraphicsLineItem] = None  # QGraphicsLineItem for Z-control
        self.scatter_L: Optional[pg.ScatterPlotItem] = None
        self.scatter_R: Optional[pg.ScatterPlotItem] = None
        
        # GaitRite elements
        self.gaitrite_trajectory_item: Optional[pg.PlotDataItem] = None
        self.gaitrite_footprint_items: List = []
        
        # Configuration
        self.r_offset: float = DEFAULT_R_OFFSET
        self.marker_group_index_L: int = 0
        self.marker_group_index_R: int = 0
        
        # Fixed line height for cursor (constant vertical span)
        self.fixed_line_height: float = 20000.0  # Fixed height in data units
        
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
        # Set white background for plot widget and disable interactive features and grid
        try:
            self.plot_widget.setBackground('w')
            # Remove grid if present
            try:
                self.plot_widget.showGrid(x=False, y=False)
            except Exception:
                pass

            # Disable mouse interactions (pan/zoom)
            try:
                vb = self.plot_widget.getViewBox()
                vb.setMouseEnabled(x=False, y=False)
            except Exception:
                pass

            # Disable context menu to prevent plot-level actions
            try:
                self.plot_widget.setMenuEnabled(False)
            except Exception:
                pass

            # Hide Y axis scale and labels
            try:
                axis_left = self.plot_widget.getAxis('left')
                if axis_left is not None and hasattr(axis_left, 'setStyle'):
                    axis_left.setStyle(showValues=False)
                else:
                    # Fallback: hide text pen to make labels invisible
                    try:
                        axis_left.setTextPen(pg.mkPen(None))
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass
        
        self.plot_items_L = []
        self.plot_items_R = []
        
        # Determine legend labels: use SENSOR_GROUP_LABELS when we have exactly 3 groups
        try:
            if len(sums_L) == 3:
                group_labels = SENSOR_GROUP_LABELS
            else:
                group_labels = [f'Group {i+1}' for i in range(len(sums_L))]
        except Exception:
            group_labels = [f'Group {i+1}' for i in range(len(sums_L))]

        # Plot each group
        for group_idx in range(len(sums_L)):
            # Left side
            y_L = sums_L[group_idx]
            pen_L = pg.mkPen(PLOT_COLORS[group_idx % len(PLOT_COLORS)], width=2)
            label_L = f'L {group_labels[group_idx]}'
            plot_item_L = self.plot_widget.plot(
                x_data, y_L, pen=pen_L, 
                name=label_L
            )
            # Set low Z-value for data lines so cursor stays on top
            try:
                plot_item_L.setZValue(0)
            except Exception:
                pass
            self.plot_items_L.append(plot_item_L)
            
            # Right side
            if group_idx < len(sums_R):
                y_R = sums_R[group_idx] - self.r_offset
                pen_R = pg.mkPen(
                    PLOT_COLORS[group_idx % len(PLOT_COLORS)], 
                    width=2, 
                    style=QtCore.Qt.DashLine
                )
                label_R = f'R {group_labels[group_idx]}'
                plot_item_R = self.plot_widget.plot(
                    x_data, y_R, pen=pen_R,
                    name=label_R
                )
                # Set low Z-value for data lines so cursor stays on top
                try:
                    plot_item_R.setZValue(0)
                except Exception:
                    pass
                self.plot_items_R.append(plot_item_R)
        
        # Create scatter items for markers
        self._create_scatter_items()
        
        # Create cursor segment
        self._create_cursor_segment()
        
        # Set Y range with zoom for better visibility
        self._set_optimal_y_range(sums_L, sums_R)
    
    def _create_scatter_items(self):
        """Create scatter plot items for position markers."""
        if self.scatter_L is None:
            self.scatter_L = pg.ScatterPlotItem(
                size=10,
                pen=pg.mkPen(None),
                brush=pg.mkBrush(*MARKER_LEFT_COLOR)
            )
            self.plot_widget.addItem(self.scatter_L)
        
        if self.scatter_R is None:
            self.scatter_R = pg.ScatterPlotItem(
                size=10,
                pen=pg.mkPen(None),
                brush=pg.mkBrush(*MARKER_RIGHT_COLOR)
            )
            self.plot_widget.addItem(self.scatter_R)
    
    def _create_cursor_segment(self):
        """
        Create cursor segment for highlighting current position.
        EXACTLY as original - creates PlotDataItem with very high Z-value.
        QGraphicsLineItem is created dynamically later if needed.
        """
        # Create PlotDataItem as primary method (exactly as original)
        if self.cursor_segment is None:
            try:
                # Thinner cursor segment for less visual weight
                seg_pen = pg.mkPen(color=(255, 200, 0), width=2)
                self.cursor_segment = pg.PlotDataItem(pen=seg_pen)
                # add after plotting so it renders on top; force very high Z
                self.plot_widget.addItem(self.cursor_segment)
                try:
                    self.cursor_segment.setZValue(10**6)
                except Exception:
                    pass
                self.cursor_segment.setData(x=[], y=[])
            except Exception:
                self.cursor_segment = None
        
        # Hide scatter markers as original does (segment replaces them visually)
        try:
            if self.scatter_L is not None:
                self.scatter_L.setVisible(False)
            if self.scatter_R is not None:
                self.scatter_R.setVisible(False)
        except Exception:
            pass
    
    def create_cursor_line(self) -> pg.InfiniteLine:
        """
        Create vertical cursor line for time synchronization.
        
        Returns:
            InfiniteLine object representing the cursor
        """
        if self.cursor_line is None:
            self.cursor_line = pg.InfiniteLine(
                pos=0, 
                angle=90, 
                pen=pg.mkPen(CURSOR_COLOR, width=1)
            )
            self.plot_widget.addItem(self.cursor_line)
        
        return self.cursor_line
    
    def update_cursor_position(self, time_seconds: float, 
                              sums_L: Optional[List[np.ndarray]] = None,
                              sums_R: Optional[List[np.ndarray]] = None,
                              csv_idx: Optional[int] = None):
        """
        Update cursor line position based on video time.
        
        Args:
            time_seconds: Current video time in seconds
            sums_L: Left side data (optional, for backward compatibility)
            sums_R: Right side data (optional, for backward compatibility)
            csv_idx: CSV index (optional, for backward compatibility)
        """
        if self.cursor_line is not None:
            self.cursor_line.setPos(time_seconds)
    
    def set_plot_x_range(self, x_min: float, x_max: float):
        """
        Set the X-axis range of the main plot.
        
        Args:
            x_min: Minimum X value (time in seconds)
            x_max: Maximum X value (time in seconds)
        """
        self.plot_widget.setXRange(x_min, x_max, padding=0)
    
    def update_markers(self, csv_index: int, x_data: np.ndarray, 
                      sums_L: List[np.ndarray], sums_R: List[np.ndarray]):
        """
        Update position markers and connecting segment on the plot.
        EXACTLY replicates original ephy.py behavior.
        
        Args:
            csv_index: Current index in CSV data
            x_data: X-axis data array
            sums_L: Left side data groups
            sums_R: Right side data groups
        """
        current_time = time.time()
        do_update = (current_time - self._last_plot_update) >= self._plot_update_interval
        
        if not do_update:
            return
        
        self._last_plot_update = current_time
        
        if csv_index >= len(x_data):
            return
            
        x_val = x_data[csv_index]
        
        # Update left marker
        yL = 0.0
        if self.marker_group_index_L < len(sums_L):
            arrL = sums_L[self.marker_group_index_L]
            if csv_index < len(arrL):
                yL = float(arrL[csv_index])
                if self.scatter_L is not None:
                    self.scatter_L.setData([x_val], [yL])
        
        # Update right marker
        yR_shifted = 0.0 - self.r_offset
        if self.marker_group_index_R < len(sums_R):
            arrR = sums_R[self.marker_group_index_R]
            if csv_index < len(arrR):
                yR = float(arrR[csv_index])
                yR_shifted = yR - self.r_offset
                if self.scatter_R is not None:
                    self.scatter_R.setData([x_val], [yR_shifted])
        
        # Draw vertical line that moves in X axis with FIXED height
        # Line has fixed Y coordinates covering the full data range
        if self.cursor_segment is not None:
            try:
                # Prefer the current visible Y range so the cursor matches the plotted viewport
                try:
                    vb = self.plot_widget.getViewBox()
                    vr = vb.viewRange()  # returns [xRange, yRange]
                    y_min, y_max = float(vr[1][0]), float(vr[1][1])
                except Exception:
                    y_min, y_max = None, None

                if y_min is None or y_max is None or y_min == y_max:
                    # Fallback: compute a span that covers left (near 0) and right (shifted by -r_offset)
                    half_h = self.fixed_line_height / 2.0
                    y_top = half_h
                    y_bottom = -self.r_offset - half_h
                else:
                    y_bottom, y_top = y_min, y_max

                # Line moves only in X direction, Y coordinates stay constant
                self.cursor_segment.setData(x=[x_val, x_val], y=[y_bottom, y_top])
            except Exception:
                pass
    
    
    def draw_gaitrite_footprints(self, footprints_left: Optional[pd.DataFrame],
                                 footprints_right: Optional[pd.DataFrame],
                                 gaitrite_df: Optional[pd.DataFrame] = None):
        """
        Draw GaitRite footprints and trajectory on the plot.
        EXACTLY replicates original ephy.py behavior.
        
        Args:
            footprints_left: Left footprint data
            footprints_right: Right footprint data
            gaitrite_df: Main GaitRite data for trajectory (optional)
        """
        self.gaitrite_plot.clear()
        self.gaitrite_footprint_items = []
        
        # Draw carpet background first
        self._draw_carpet_background()
        
        # Draw trajectory if GaitRite data is available
        if gaitrite_df is not None:
            self._draw_gaitrite_trajectory(gaitrite_df)
        
        # Draw footprints
        if footprints_left is not None:
            self._plot_footprint_group(footprints_left, FOOTPRINT_LEFT_COLOR, 'Left')
        
        if footprints_right is not None:
            self._plot_footprint_group(footprints_right, FOOTPRINT_RIGHT_COLOR, 'Right')
        
        # Auto-adjust view range based on all drawn data (exactly as original)
        self._auto_adjust_gaitrite_view()
    
    def _draw_carpet_background(self):
        """
        Draw the GaitRite carpet background rectangle.
        EXACTLY as original ephy.py - from (0,0) to (CARPET_WIDTH, CARPET_LENGTH).
        """
        # Draw carpet outline with coordinates from 0 to dimensions (NOT centered)
        bg_x = [0, CARPET_WIDTH_CM, CARPET_WIDTH_CM, 0, 0]
        bg_y = [0, 0, CARPET_LENGTH_CM, CARPET_LENGTH_CM, 0]
        
        self.gaitrite_plot.plot(
            bg_x, bg_y,
            pen=pg.mkPen(CARPET_BORDER_COLOR, width=2),
            fillLevel=0,
            brush=pg.mkBrush(*CARPET_BACKGROUND_COLOR)
        )
    
    def _draw_gaitrite_trajectory(self, gaitrite_df: pd.DataFrame):
        """
        Draw the trajectory path from GaitRite data.
        EXACTLY replicates original ephy.py behavior.
        
        Args:
            gaitrite_df: DataFrame with columns Ybottom, Ytop, Xback, Xfront
        """
        try:
            traj_x = []
            traj_y = []
            
            # Check for required columns (exactly as in original)
            if all(c in gaitrite_df.columns for c in ('Ybottom', 'Ytop', 'Xback', 'Xfront')):
                # Compute centers using midpoints (EXACT formula from original)
                ctr_x = (((gaitrite_df['Ybottom'].astype(float) + gaitrite_df['Ytop'].astype(float)) / 2.0) 
                         * GAITRITE_CONVERSION_FACTOR).values
                ctr_y = (((gaitrite_df['Xback'].astype(float) + gaitrite_df['Xfront'].astype(float)) / 2.0) 
                         * GAITRITE_CONVERSION_FACTOR).values
                traj_x = list(ctr_x)
                traj_y = list(ctr_y)
            else:
                print(f"[PlotManager] Missing required columns for trajectory")
                return
            
            # Draw trajectory if we have at least 2 points (exactly as in original)
            if len(traj_x) > 1:
                # Draw BLACK line (NOT blue) - exactly as original
                self.gaitrite_trajectory_item = self.gaitrite_plot.plot(
                    traj_x, traj_y,
                    pen=pg.mkPen('black', width=2)  # BLACK, not blue!
                )
                # Set Z-value high so trajectory is above footprints
                try:
                    self.gaitrite_trajectory_item.setZValue(1000)
                except Exception:
                    pass
                
                # Mark start (green) and end (red) points - BIGGER SIZE
                try:
                    # Start point - GREEN (BIGGER)
                    start_marker = pg.ScatterPlotItem(
                        size=12,  # Increased from 8 to 12
                        brush=pg.mkBrush(0, 200, 0),  # Green
                        pen=pg.mkPen('k', width=2)
                    )
                    start_marker.setData(x=[traj_x[0]], y=[traj_y[0]])
                    # Set Z-value even higher for markers
                    try:
                        start_marker.setZValue(2000)
                    except Exception:
                        pass
                    self.gaitrite_plot.addItem(start_marker)
                    
                    # End point - RED (BIGGER)
                    end_marker = pg.ScatterPlotItem(
                        size=12,  # Increased from 8 to 12
                        brush=pg.mkBrush(200, 0, 0),  # Red
                        pen=pg.mkPen('k', width=2)
                    )
                    end_marker.setData(x=[traj_x[-1]], y=[traj_y[-1]])
                    # Set Z-value even higher for markers
                    try:
                        end_marker.setZValue(2000)
                    except Exception:
                        pass
                    self.gaitrite_plot.addItem(end_marker)
                except Exception:
                    pass
                
                print(f"[PlotManager] Drew trajectory with {len(traj_x)} points", flush=True)
            
        except Exception as e:
            print(f"[PlotManager] Error drawing trajectory: {e}", flush=True)
    
    def _plot_footprint_group(self, footprints: pd.DataFrame, color: str, side: str):
        """
        Plot footprint contours (EXACTLY as original ephy.py).
        
        Args:
            footprints: DataFrame with columns: x_cm, y_cm, gait_id, event, sample_idx
            color: Color for the footprints
            side: 'Left' or 'Right' for labeling
        """
        try:
            if footprints is None or footprints.empty:
                return
            
            drew_count = 0
            
            # Check if we have gait_id column for grouping
            if 'gait_id' in footprints.columns:
                group_col = 'gait_id'
            elif 'Gait_Id' in footprints.columns:
                group_col = 'Gait_Id'
            else:
                group_col = None
            
            if group_col is not None:
                # Draw polygons grouped by gait_id and event
                for gait_val, gait_group in footprints.groupby(group_col):
                    # Check if we have event column
                    if 'event' in gait_group.columns:
                        event_groups = gait_group.groupby('event')
                    else:
                        event_groups = [(None, gait_group)]
                    
                    for event_val, event_group in event_groups:
                        # Sort by sample_idx if available
                        if 'sample_idx' in event_group.columns:
                            grp_sorted = event_group.sort_values('sample_idx')
                        else:
                            grp_sorted = event_group
                        
                        # Draw contour if we have x_cm and y_cm
                        if 'x_cm' in grp_sorted.columns and 'y_cm' in grp_sorted.columns:
                            x_vals = grp_sorted['x_cm'].values
                            y_vals = grp_sorted['y_cm'].values
                            
                            # Draw the contour line (exactly as original)
                            footprint_item = self.gaitrite_plot.plot(
                                x_vals, y_vals,
                                pen=pg.mkPen(color=color, width=2)
                            )
                            self.gaitrite_footprint_items.append(footprint_item)
                            drew_count += 1
            else:
                # No grouping column - draw all points as single contour
                if 'x_cm' in footprints.columns and 'y_cm' in footprints.columns:
                    x_vals = footprints['x_cm'].values
                    y_vals = footprints['y_cm'].values;
                    
                    footprint_item = self.gaitrite_plot.plot(
                        x_vals, y_vals,
                        pen=pg.mkPen(color=color, width=2)
                    )
                    self.gaitrite_footprint_items.append(footprint_item)
                    drew_count = 1
            
            if drew_count > 0:
                print(f"[PlotManager] Drew {drew_count} {side} footprint contours", flush=True)
            
        except Exception as e:
            print(f"[PlotManager] Error plotting {side} footprints: {e}", flush=True)
    
    def _auto_adjust_gaitrite_view(self):
        """
        Auto-adjust GaitRite plot view to fit all data.
        EXACTLY replicates original ephy.py behavior.
        """
        try:
            self.gaitrite_plot.disableAutoRange()
            
            # Collect all x,y data from all items
            all_x = []
            all_y = []
            
            for item in self.gaitrite_plot.listDataItems():
                try:
                    d = item.getData()
                    if d is None:
                        continue
                    xs, ys = d
                    all_x.extend(list(xs))
                    all_y.extend(list(ys))
                except Exception:
                    continue
            
            # Set range based on actual data or fallback to carpet size
            if len(all_x) > 0 and len(all_y) > 0:
                minx, maxx = min(all_x), max(all_x)
                miny, maxy = min(all_y), max(all_y)
                padding_x = max(1.0, (maxx - minx) * 0.10)
                padding_y = max(1.0, (maxy - miny) * 0.08)
                self.gaitrite_plot.setXRange(minx - padding_x, maxx + padding_x, padding=0)
                self.gaitrite_plot.setYRange(miny - padding_y, maxy + padding_y, padding=0)
            else:
                # Fallback to carpet dimensions
                padding_x = CARPET_WIDTH_CM * 0.10
                padding_y = CARPET_LENGTH_CM * 0.08
                self.gaitrite_plot.setXRange(-padding_x, CARPET_WIDTH_CM + padding_x, padding=0)
                self.gaitrite_plot.setYRange(-padding_y, CARPET_LENGTH_CM + padding_y, padding=0)
                
        except Exception as e:
            print(f"[PlotManager] Error adjusting view: {e}", flush=True)
    
    def set_marker_group_L(self, group_index: int):
        """Set the group index for left marker."""
        self.marker_group_index_L = group_index
    
    def set_marker_group_R(self, group_index: int):
        """Set the group index for right marker."""
        self.marker_group_index_R = group_index
    
    def _set_optimal_y_range(self, sums_L: List[np.ndarray], sums_R: List[np.ndarray]):
        """
        Set optimal Y range for the plot with zoom for better visibility.
        
        Args:
            sums_L: Left side data groups
            sums_R: Right side data groups
        """
        try:
            # Collect all Y values to determine the range
            all_y_values = []
            
            # Add all L values
            for arr in sums_L:
                all_y_values.extend(arr.flatten())
            
            # Add all R values (with offset)
            for arr in sums_R:
                all_y_values.extend((arr - self.r_offset).flatten())
            
            if len(all_y_values) > 0:
                y_min = np.min(all_y_values)
                y_max = np.max(all_y_values)
                
                # Add 8% padding for better visibility with more zoom
                y_range = y_max - y_min
                padding = y_range * 0.08
                
                self.plot_widget.setYRange(y_min - padding, y_max + padding, padding=0)
                print(f"[PlotManager] Set Y range: {y_min - padding:.1f} to {y_max + padding:.1f}", flush=True)
        except Exception as e:
            print(f"[PlotManager] Error setting Y range: {e}", flush=True)