"""
Main application entry point.

This module provides the main() function that initializes and runs
the Video Gait Analyzer application.
"""

import os
import sys

# CRITICAL: Configure Qt plugins BEFORE any other imports
# This prevents conflicts between PyQt5 and OpenCV Qt plugins
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ''
os.environ.pop('QT_QPA_PLATFORM_PLUGIN_PATH', None)

from PyQt5 import QtWidgets

# Configure Qt plugins before importing other modules
from .utils.qt_config import configure_qt_plugins
configure_qt_plugins()

from .core.video_player import VideoPlayer


def main():
    """
    Main entry point for the Video Gait Analyzer application.
    
    Initializes the Qt application, creates the main window,
    and starts the event loop.
    
    Returns:
        Exit code from Qt application
    """
    try:
        print("[VideoGaitAnalyzer] Starting application", flush=True)
        
        app = QtWidgets.QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(True)
        app.aboutToQuit.connect(
            lambda: print("[VideoGaitAnalyzer] Application quitting", flush=True)
        )
        
        player = VideoPlayer()
        print("[VideoGaitAnalyzer] Showing main window", flush=True)
        player.show()
        
        print("[VideoGaitAnalyzer] Entering event loop", flush=True)
        rc = app.exec_()
        print(f"[VideoGaitAnalyzer] Application exited with code {rc}", flush=True)
        sys.exit(rc)
        
    except Exception as e:
        import traceback
        print(f"[VideoGaitAnalyzer] ERROR: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
