import threading
import time
from typing import Optional

import numpy as np


class Worker:
    """Simple background worker used by the standalone GUI (not the adapter).

    Kept for completeness; the adapter uses HeatmapProject's Animator and PreRenderer
    directly and manages threading via QThread.
    """
    def __init__(self, fps: float = 64.0):
        self.fps = float(fps)
        self._running = False
        self._playing = False
        self._tick_listeners = []

    def run(self):
        self._running = True
        while self._running:
            if self._playing:
                # notify listeners
                for cb in list(self._tick_listeners):
                    try:
                        cb()
                    except Exception:
                        pass
            time.sleep(max(0.001, 1.0 / max(1.0, self.fps)))

    def stop(self):
        self._running = False
        self._playing = False

    def play(self, playing: bool):
        self._playing = bool(playing)

    def tick_connect(self, cb):
        self._tick_listeners.append(cb)

    def tick_disconnect(self, cb):
        try:
            self._tick_listeners.remove(cb)
        except Exception:
            pass
