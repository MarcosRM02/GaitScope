"""
Custom Qt widgets for the Video Gait Analyzer.

This package contains custom PyQt5 widgets including:
- ClickableSlider: Slider with click-to-seek functionality
- TimeAxis: Custom axis for displaying time in MM:SS format
"""

from .clickable_slider import ClickableSlider
from .time_axis import TimeAxis

__all__ = ["ClickableSlider", "TimeAxis"]
