"""
Core application modules.

This package contains the main application components:
- VideoPlayer: Main application window
- VideoController: Video playback control logic
- DataManager: CSV and GaitRite data management
- PlotManager: Plot visualization management
"""

from .video_player import VideoPlayer
from .video_controller import VideoController
from .data_manager import DataManager
from .plot_manager import PlotManager

__all__ = ["VideoPlayer", "VideoController", "DataManager", "PlotManager"]
