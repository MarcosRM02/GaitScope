"""PreRenderer for Heatmap_Project

Provides a small ring-buffer pre-renderer that renders composed frames in background
using Animator.render_frame_at(index). The implementation is lightweight and uses a
background Python thread with a condition variable. Intended to be imported from
`gui.py` as `from prerenderer import PreRenderer`.

API:
- PreRenderer(animator, capacity=8)
- start(), stop()
- request(idx)  # ask to fill buffer around idx
- get(idx) -> np.ndarray | None

The class purposely keeps a small memory footprint and evicts frames outside
of the requested window.
"""
from typing import Optional
import threading
import time
import numpy as np

class PreRenderer:
    def __init__(self, animator, capacity: int = 8):
        self.animator = animator
        self.capacity = max(1, int(capacity))
        self.buffer = {}  # idx -> np.ndarray
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.target = None
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def stop(self):
        with self.cond:
            self.running = False
            self.cond.notify_all()
        if self.thread is not None:
            self.thread.join()
            self.thread = None

    def request(self, idx: int):
        with self.cond:
            self.target = int(idx)
            self.cond.notify()

    def get(self, idx: int) -> Optional[np.ndarray]:
        with self.lock:
            v = self.buffer.get(int(idx), None)
            # return a view/reference (caller must not modify)
            return v

    def _worker(self):
        while True:
            with self.cond:
                while self.running and self.target is None:
                    self.cond.wait()
                if not self.running:
                    break
                target = int(self.target)
            # determine desired window
            n = self.animator.n_frames()
            if n <= 0:
                time.sleep(0.05)
                continue
            # center window slightly ahead to prioritize upcoming frames
            half = max(1, self.capacity // 2)
            start = max(0, target - half // 2)
            end = min(n, start + self.capacity)
            desired = list(range(start, end))
            # render missing frames
            for i in desired:
                with self.lock:
                    need = i not in self.buffer
                if need:
                    try:
                        frm = self.animator.render_frame_at(i)
                    except Exception:
                        # on error, skip
                        continue
                    with self.lock:
                        self.buffer[i] = frm
                # small yield
            # evict keys outside desired window
            with self.lock:
                keys = list(self.buffer.keys())
                for k in keys:
                    if k < start or k >= end:
                        del self.buffer[k]
            # wait shortly or until new target
            with self.cond:
                cur_target = self.target
                if cur_target == target:
                    self.cond.wait(timeout=0.02)
