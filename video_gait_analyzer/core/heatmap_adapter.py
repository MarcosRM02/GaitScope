"""
HeatmapAdapter - Bridge between Heatmap_Project and video_gait_analyzer

This module provides a Qt-compatible adapter that encapsulates the Heatmap_Project
animation logic (Animator, Worker, PreRenderer) and exposes it via Qt signals/slots
for seamless integration into the VideoPlayer UI.

The adapter runs the heatmap animation in a separate QThread at an independent
frame rate (Hz) without blocking the main UI or video playback.

API:
- start(): Begin animation thread
- stop(): Stop animation thread and cleanup
- pause(): Pause animation (keeps thread alive)
- resume(): Resume animation
- set_rate(hz): Change animation frame rate
- set_data(left_coords, right_coords, left_seq, right_seq): Load heatmap data
- set_size(width, height): Update render dimensions
- update_params(**kwargs): Update heatmap rendering parameters
- seek(frame_idx): Jump to specific frame
- get_current_frame_index(): Get current frame index

Signals:
- frame_ready(np.ndarray): Emitted when a new frame is rendered (BGR format)
- fps_report(float): Emitted ~once per second with measured FPS
"""

import sys
import os
from typing import List, Tuple, Optional
import numpy as np
from PyQt5 import QtCore

# Import Heatmap_Project modules
# Add Heatmap_Project to path if not already there
heatmap_project_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'Heatmap_Project'
)
if heatmap_project_path not in sys.path:
    sys.path.insert(0, heatmap_project_path)

try:
    from animator import Animator
    from prerenderer import PreRenderer
except ImportError as e:
    print(f"[HeatmapAdapter] Warning: Could not import Heatmap_Project modules: {e}", flush=True)
    Animator = None
    PreRenderer = None


class HeatmapWorker(QtCore.QObject):
    """
    Background worker that drives heatmap frame updates.
    
    Runs in a QThread and emits signals at the configured frame rate.
    Uses PreRenderer for optimized frame buffering.
    """
    
    # Signals
    frame_ready = QtCore.pyqtSignal(np.ndarray)  # Emits BGR frame as numpy array
    fps_report = QtCore.pyqtSignal(float)  # Emits measured FPS
    
    def __init__(self, animator, fps: float = 64.0):
        super().__init__()
        self.animator = animator
        self.prerenderer = PreRenderer(animator, capacity=8) if PreRenderer else None
        self.fps = fps
        self._running = False
        self._playing = False
        self._timer = None
        
    @QtCore.pyqtSlot()
    def start(self):
        """Initialize and start the animation loop."""
        if self._running:
            return
            
        self._running = True
        if self.prerenderer:
            self.prerenderer.start()
        
        # Use QTimer for frame updates (more Qt-friendly than time.sleep loop)
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self._on_tick)
        self._update_timer_interval()
        self._timer.start()
        
        print("[HeatmapWorker] Started", flush=True)
    
    @QtCore.pyqtSlot()
    def stop(self):
        """Stop the animation loop and cleanup."""
        if not self._running:
            return
            
        self._running = False
        self._playing = False
        
        if self._timer:
            self._timer.stop()
            self._timer = None
        
        if self.prerenderer:
            self.prerenderer.stop()
            
        print("[HeatmapWorker] Stopped", flush=True)
    
    @QtCore.pyqtSlot(bool)
    def set_playing(self, playing: bool):
        """Enable/disable frame emission."""
        self._playing = playing
        if self._playing and self.prerenderer:
            # Request prerender around current frame
            self.prerenderer.request(self.animator.frame_idx)
    
    @QtCore.pyqtSlot(float)
    def set_fps(self, fps: float):
        """Update animation frame rate."""
        self.fps = max(1.0, float(fps))
        self._update_timer_interval()
        
    @QtCore.pyqtSlot(int)
    def seek(self, frame_idx: int):
        """Jump to specific frame."""
        self.animator.set_frame(frame_idx)
        if self.prerenderer:
            self.prerenderer.request(frame_idx)
        # Emit frame immediately
        self._emit_current_frame()
    
    def _update_timer_interval(self):
        """Update timer interval based on current FPS."""
        if self._timer and self._timer.isActive():
            interval_ms = int(1000.0 / self.fps)
            self._timer.setInterval(interval_ms)
    
    @QtCore.pyqtSlot()
    def _on_tick(self):
        """Called by timer to advance and emit frame."""
        if not self._playing:
            return
            
        # Advance to next frame
        self.animator.step(1)
        
        # Request prerender around current position
        if self.prerenderer:
            self.prerenderer.request(self.animator.frame_idx)
        
        # Emit current frame
        self._emit_current_frame()
    
    def _emit_current_frame(self):
        """Render and emit the current frame."""
        try:
            # Try to get from prerenderer cache first
            frame = None
            if self.prerenderer:
                frame = self.prerenderer.get(self.animator.frame_idx)
            
            # If not in cache, render directly
            if frame is None:
                frame = self.animator.get_frame()
            
            # Emit frame (BGR format, as returned by animator)
            self.frame_ready.emit(frame)
            
        except Exception as e:
            print(f"[HeatmapWorker] Error rendering frame: {e}", flush=True)


class HeatmapAdapter(QtCore.QObject):
    """
    Qt-compatible adapter for Heatmap_Project.
    
    Provides a high-level API for integrating heatmap animation into
    the VideoPlayer UI. Manages the animation thread, data loading,
    and parameter updates.
    """
    
    # Signals
    frame_ready = QtCore.pyqtSignal(np.ndarray)  # Propagate from worker
    fps_report = QtCore.pyqtSignal(float)  # Propagate from worker
    
    def __init__(self):
        super().__init__()
        
        # Check if Heatmap_Project modules are available
        if Animator is None:
            print("[HeatmapAdapter] Warning: Heatmap_Project not available", flush=True)
            self._available = False
            return
        
        self._available = True
        
        # Default parameters (matching Heatmap_Project defaults)
        self.params = {
            'wFinal': 175,
            'hFinal': 520,
            'gridW': 20,
            'gridH': 69,
            'radius': 70.0,
            'smoothness': 2.0,
            'margin': 50,
            'legendWidth': 80,
            'trailLength': 10,
            'fps': 64
        }
        
        # Initialize animator with empty data
        self.animator = Animator(self.params, [], [])
        
        # Worker thread
        self.thread = None
        self.worker = None
        
        print("[HeatmapAdapter] Initialized", flush=True)
    
    def is_available(self) -> bool:
        """Check if Heatmap_Project modules are available."""
        return self._available
    
    def start(self):
        """Start the animation thread."""
        if not self._available or self.thread is not None:
            return
        
        if self.animator is None:
            print("[HeatmapAdapter] ERROR: No animator - call set_data() first!", flush=True)
            return
        
        # Store current frame position before creating worker
        current_frame_idx = self.animator.frame_idx
        
        # Create worker and thread
        self.worker = HeatmapWorker(self.animator, fps=self.params['fps'])
        self.thread = QtCore.QThread()
        
        # Move worker to thread
        self.worker.moveToThread(self.thread)
        
        # Connect signals
        self.worker.frame_ready.connect(self.frame_ready.emit)
        self.worker.fps_report.connect(self.fps_report.emit)
        self.thread.started.connect(self.worker.start)
        
        # Start thread
        self.thread.start()
        
        # Seek to current position to emit initial frame
        if current_frame_idx > 0:
            QtCore.QMetaObject.invokeMethod(
                self.worker, 'seek', QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(int, current_frame_idx)
            )
        
        print("[HeatmapAdapter] Thread started", flush=True)
    
    def stop(self):
        """Stop the animation thread and cleanup."""
        if not self._available or self.thread is None:
            return
        
        # Stop worker
        if self.worker:
            QtCore.QMetaObject.invokeMethod(
                self.worker, 'stop', QtCore.Qt.QueuedConnection
            )
        
        # Wait for thread to finish
        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
        
        self.worker = None
        
        print("[HeatmapAdapter] Thread stopped", flush=True)
    
    def pause(self):
        """Pause animation (keeps thread alive)."""
        if self.worker:
            QtCore.QMetaObject.invokeMethod(
                self.worker, 'set_playing', QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(bool, False)
            )
    
    def resume(self):
        """Resume animation."""
        if self.worker:
            QtCore.QMetaObject.invokeMethod(
                self.worker, 'set_playing', QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(bool, True)
            )
    
    def set_rate(self, hz: float):
        """Change animation frame rate."""
        self.params['fps'] = hz
        if self.worker:
            QtCore.QMetaObject.invokeMethod(
                self.worker, 'set_fps', QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(float, hz)
            )
    
    def set_data(self, 
                 left_coords: List[Tuple[float, float]], 
                 right_coords: List[Tuple[float, float]],
                 left_seq: List[List[int]], 
                 right_seq: List[List[int]]):
        """
        Load heatmap data.
        
        Args:
            left_coords: List of (x, y) sensor coordinates for left foot
            right_coords: List of (x, y) sensor coordinates for right foot
            left_seq: List of frames, each frame is a list of pressure values
            right_seq: List of frames, each frame is a list of pressure values
        """
        if not self._available:
            return
        
        # Recreate animator with new coordinates
        self.animator = Animator(self.params, left_coords, right_coords)
        self.animator.load_sequences(left_seq, right_seq)
        
        # Update worker's animator reference
        if self.worker:
            self.worker.animator = self.animator
            if self.worker.prerenderer:
                self.worker.prerenderer.animator = self.animator
        
        print(f"[HeatmapAdapter] Data loaded: {len(left_seq)} frames", flush=True)
    
    def set_size(self, width: int, height: int):
        """
        Update render dimensions.
        
        Note: This recreates the animator with new dimensions.
        """
        if not self._available:
            return
        
        # Update parameters
        self.params['wFinal'] = width
        self.params['hFinal'] = height
        
        # Recreate animator with new size
        old_left_coords = self.animator.coords_left
        old_right_coords = self.animator.coords_right
        old_left_seq = self.animator.left_seq
        old_right_seq = self.animator.right_seq
        old_frame_idx = self.animator.frame_idx
        
        self.animator = Animator(self.params, old_left_coords, old_right_coords)
        self.animator.load_sequences(old_left_seq, old_right_seq)
        self.animator.set_frame(old_frame_idx)
        
        # Update worker's animator reference
        if self.worker:
            self.worker.animator = self.animator
            if self.worker.prerenderer:
                self.worker.prerenderer.animator = self.animator
        
        print(f"[HeatmapAdapter] Size updated: {width}x{height}", flush=True)
    
    def update_params(self, **kwargs):
        """
        Update heatmap rendering parameters.
        
        Supported parameters:
        - radius: Gaussian kernel radius
        - smoothness: Gaussian kernel smoothness
        - trailLength: Number of COP trail points
        - margin: Image margin
        - legendWidth: Colorbar width
        """
        if not self._available:
            return
        
        # Update parameters
        for key, value in kwargs.items():
            if key in self.params:
                self.params[key] = value
        
        # Recreate animator with new parameters
        old_left_coords = self.animator.coords_left
        old_right_coords = self.animator.coords_right
        old_left_seq = self.animator.left_seq
        old_right_seq = self.animator.right_seq
        old_frame_idx = self.animator.frame_idx
        
        self.animator = Animator(self.params, old_left_coords, old_right_coords)
        self.animator.load_sequences(old_left_seq, old_right_seq)
        self.animator.set_frame(old_frame_idx)
        
        # Update worker's animator reference
        if self.worker:
            self.worker.animator = self.animator
            if self.worker.prerenderer:
                self.worker.prerenderer.animator = self.animator
        
        print(f"[HeatmapAdapter] Parameters updated: {kwargs}", flush=True)
    
    def seek(self, frame_idx: int):
        """Jump to specific frame."""
        if not self._available:
            return
        
        if self.worker:
            QtCore.QMetaObject.invokeMethod(
                self.worker, 'seek', QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(int, frame_idx)
            )
        else:
            # If worker not running, update animator directly
            self.animator.set_frame(frame_idx)
    
    def get_current_frame_index(self) -> int:
        """Get current frame index."""
        if not self._available:
            return 0
        return self.animator.frame_idx
    
    def get_total_frames(self) -> int:
        """Get total number of frames."""
        if not self._available:
            return 0
        return self.animator.n_frames()
    
    def show_initial_frame(self):
        """Render and emit the first frame immediately (without starting playback)."""
        if not self._available or self.animator is None:
            print("[HeatmapAdapter] Cannot show initial frame - not available or no animator", flush=True)
            return
        
        try:
            # Set to first frame
            self.animator.set_frame(0)
            
            # Render the frame
            frame = self.animator.get_frame()
            
            # Emit the frame directly
            self.frame_ready.emit(frame)
            
            print("[HeatmapAdapter] Initial frame displayed", flush=True)
            
        except Exception as e:
            print(f"[HeatmapAdapter] Error showing initial frame: {e}", flush=True)
