"""
Main application entry point.

This module now exposes small, testable helpers:
- detect_qt_binding()
- import_qt_widgets(binding)
- import_video_player()
- run_gui(QtWidgets, VideoPlayer)
- main()

The runtime behavior is unchanged; main() orchestrates detection, imports
and runs the GUI.
"""

import os
import sys
import importlib
from typing import Optional, Tuple


def detect_qt_binding() -> Optional[str]:
    """Return the name of an available Qt binding or None.

    Checks for PyQt5, PyQt6, PySide2, PySide6 (in that order of preference).
    """
    for name in ("PyQt5", "PyQt6", "PySide2", "PySide6"):
        try:
            if importlib.util.find_spec(name) is not None:
                return name
        except Exception:
            continue
    return None


def import_qt_widgets(binding: str):
    """Import and return the QtWidgets module for the given binding.

    Raises ImportError on failure.
    """
    if binding == "PyQt5":
        from PyQt5 import QtWidgets  # type: ignore
        return QtWidgets
    if binding == "PyQt6":
        from PyQt6 import QtWidgets  # type: ignore
        return QtWidgets
    if binding == "PySide2":
        from PySide2 import QtWidgets  # type: ignore
        return QtWidgets
    if binding == "PySide6":
        from PySide6 import QtWidgets  # type: ignore
        return QtWidgets

    # Fallback: try common imports
    try:
        from PyQt5 import QtWidgets  # type: ignore
        return QtWidgets
    except Exception:
        pass
    try:
        from PySide6 import QtWidgets  # type: ignore
        return QtWidgets
    except Exception:
        pass

    raise ImportError("Could not import QtWidgets for binding: %s" % binding)


def import_video_player():
    """Import and return the VideoPlayer class from the UI module.

    Raises ImportError on failure.
    """
    from .core.video_player import VideoPlayer

    return VideoPlayer


def run_gui(QtWidgets, VideoPlayer) -> int:
    """Create QApplication, show the VideoPlayer and run the event loop.

    Returns the QApplication exit code.
    """
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    app.aboutToQuit.connect(lambda: print("[VideoGaitAnalyzer] Application quitting", flush=True))

    player = VideoPlayer()
    print("[VideoGaitAnalyzer] Showing main window", flush=True)
    player.show()

    print("[VideoGaitAnalyzer] Entering event loop", flush=True)
    rc = app.exec_()
    print(f"[VideoGaitAnalyzer] Application exited with code {rc}", flush=True)
    return rc


def main() -> None:
    """Main entry point: detect bindings, import modules and run the GUI."""
    try:
        print("[VideoGaitAnalyzer] Starting application", flush=True)

        qt_binding = detect_qt_binding()
        if qt_binding is None:
            print(
                "[VideoGaitAnalyzer] No Qt bindings found (PyQt5/PyQt6/PySide2/PySide6).\n"
                "Install the GUI extras to run the application, e.g.:\n"
                "    pip install .[gui]\n"
                "or install a binding directly, e.g.:\n"
                "    pip install PyQt5\n",
                flush=True,
            )
            sys.exit(2)

        # Import QtWidgets for the detected binding
        try:
            QtWidgets = import_qt_widgets(qt_binding)
        except Exception as e:
            print(f"[VideoGaitAnalyzer] Failed to import QtWidgets: {e}", flush=True)
            sys.exit(3)

        # Import UI components
        try:
            VideoPlayer = import_video_player()
        except Exception as e:
            print(f"[VideoGaitAnalyzer] Failed importing UI components: {e}", flush=True)
            sys.exit(4)

        # Run GUI loop
        rc = run_gui(QtWidgets, VideoPlayer)
        sys.exit(rc)

    except Exception as e:
        import traceback
        print(f"[VideoGaitAnalyzer] ERROR: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
