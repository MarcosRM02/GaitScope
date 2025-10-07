"""
Custom time axis for PyQtGraph plots.

Provides an axis that displays time values in MM:SS format
instead of raw seconds.
"""

import numpy as np
import pyqtgraph as pg


class TimeAxis(pg.AxisItem):
    """
    Custom PyQtGraph axis that displays time in MM:SS format.
    
    This axis converts numeric time values (in seconds) to
    human-readable MM:SS format for better user experience.
    
    Example:
        >>> time_axis = TimeAxis(orientation='bottom')
        >>> plot = pg.PlotWidget(axisItems={'bottom': time_axis})
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize the TimeAxis.
        
        Args:
            *args: Positional arguments passed to pg.AxisItem
            **kwargs: Keyword arguments passed to pg.AxisItem
        """
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        """
        Convert tick values to MM:SS formatted strings.
        
        Args:
            values: List of tick positions in seconds
            scale: Scale factor for the axis
            spacing: Spacing between ticks
            
        Returns:
            List of formatted time strings
        """
        out = []
        for v in values:
            try:
                if v is None or not np.isfinite(v):
                    out.append('')
                    continue
                secs = float(v)
                mins = int(secs // 60)
                s = int(secs % 60)
                out.append(f"{mins:02d}:{s:02d}")
            except Exception:
                out.append('')
        return out
