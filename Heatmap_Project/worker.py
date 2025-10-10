import time
from typing import Optional
from PySide6 import QtCore

"""Worker object that emits ticks at a fixed framerate.

This module contains a single class `Worker` (one-class-per-file requirement).
It runs in a QThread and emits `tick` signals at approximately `fps` Hz when
`play(True)` has been called.
"""

class Worker(QtCore.QObject):
    """Background worker that drives frame ticks.

    Signals:
    - tick: emitted each frame when playing.
    - fpsReport(float): emitted approximately once per second with measured FPS.
    """
    tick = QtCore.Signal()
    fpsReport = QtCore.Signal(float)

    def __init__(self, fps: int = 64):
        super().__init__()
        self._running: bool = True
        self._playing: bool = False
        self.fps: float = float(fps)
        self._last_period: Optional[float] = None

    @QtCore.Slot()
    def run(self) -> None:
        """Main loop. Recomputes period each iteration so callers may update
        `self.fps` at runtime and have the change take effect immediately.
        """
        next_time = time.perf_counter()
        last_report = next_time
        frames = 0
        while self._running:
            try:
                period = 1.0 / float(self.fps)
            except Exception:
                period = 1.0 / 64.0
            now = time.perf_counter()
            if self._playing:
                self.tick.emit()
                frames += 1
            next_time += period
            sleep_time = next_time - time.perf_counter()
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                # we're behind schedule; reset next_time to avoid spiralling
                next_time = time.perf_counter()
            # emit fps report roughly once per second
            if (time.perf_counter() - last_report) >= 1.0:
                elapsed = time.perf_counter() - last_report
                report_fps = frames / elapsed if elapsed > 0 else 0.0
                self.fpsReport.emit(report_fps)
                last_report = time.perf_counter()
                frames = 0

    def stop(self) -> None:
        """Request the worker loop to stop."""
        self._running = False

    def play(self, p: bool) -> None:
        """Enable/disable playback ticks.

        Note: setting play(False) does not stop the thread; call `stop()` to exit.
        """
        self._playing = bool(p)
