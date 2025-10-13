"""
Qt configuration utilities.

This module handles Qt plugin path configuration to avoid conflicts
between PyQt5 and OpenCV Qt plugins.
"""

import os
import sys


def configure_qt_plugins():
    """
    Configure Qt plugin paths to use PyQt5 plugins and avoid conflicts with OpenCV.
    
    This function should be called before importing OpenCV to ensure
    the correct Qt platform plugins are used.
    """
    # Disable OpenCV's Qt plugins to avoid conflicts with PyQt5
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ''
    os.environ.pop('QT_QPA_PLATFORM_PLUGIN_PATH', None)
    
    # Configure OpenCV to not use Qt
    os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'
    
    try:
        import PyQt5
        pyqt_plugins = os.path.join(
            os.path.dirname(PyQt5.__file__), 'Qt5', 'plugins'
        )
        
        # Try both Qt5 and Qt directory structures
        if not os.path.isdir(pyqt_plugins):
            pyqt_plugins = os.path.join(
                os.path.dirname(PyQt5.__file__), 'Qt', 'plugins'
            )
        
        if os.path.isdir(pyqt_plugins):
            os.environ['QT_PLUGIN_PATH'] = pyqt_plugins
            platforms_dir = os.path.join(pyqt_plugins, 'platforms')
            if os.path.isdir(platforms_dir):
                os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = platforms_dir
    except Exception:
        pass  # Silently fail if PyQt5 is not available or path doesn't exist
