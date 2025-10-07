"""
Video controller module.

Handles all video playback operations including:
- Loading and releasing video files
- Play/pause/stop controls
- Frame navigation (next/previous)
- Seeking to specific frames
- Playback speed control
"""

import time
from typing import Optional
import cv2
from PyQt5 import QtCore


class VideoController:
    """
    Controller for video playback operations.
    
    This class encapsulates all video-related operations using OpenCV,
    providing a clean interface for the main application.
    """
    
    def __init__(self):
        """Initialize the video controller with default values."""
        self.video_cap: Optional[cv2.VideoCapture] = None
        self.video_path: Optional[str] = None
        self.current_frame: int = 0
        self.total_frames: int = 0
        self.fps: float = 30.0
        self.is_playing: bool = False
        self.playback_rate: float = 1.0
        
        # Seeking state flags
        self._seeking: bool = False
        self._fast_seek_lock: bool = False
        
        # Drag seek throttling
        self._last_drag_seek_time: float = 0.0
        self._drag_seek_interval: float = 1.0 / 10.0  # Max 10 seeks/sec during drag
        
        # Timer for playback
        self.timer = QtCore.QTimer()
        self._last_timer_time: float = 0.0
        
    def load_video(self, path: str) -> bool:
        """
        Load a video file for playback.
        
        Args:
            path: Absolute path to video file
            
        Returns:
            True if video loaded successfully, False otherwise
        """
        # Release previous video if any
        if self.video_cap:
            self.video_cap.release()
        
        self.video_path = path
        self.video_cap = cv2.VideoCapture(path)
        
        if not self.video_cap.isOpened():
            print(f"[VideoController] Failed to open video: {path}", flush=True)
            return False
        
        self.total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = float(self.video_cap.get(cv2.CAP_PROP_FPS)) or 30.0
        self.current_frame = 0
        
        print(f"[VideoController] Loaded video: {path}, frames={self.total_frames}, fps={self.fps}", flush=True)
        return True
    
    def release(self):
        """Release video resources."""
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
    
    def read_frame(self) -> tuple:
        """
        Read the current frame from video.
        
        Returns:
            Tuple of (success, frame_data)
        """
        if not self.video_cap:
            return False, None
        return self.video_cap.read()
    
    def seek_to_frame(self, frame_number: int) -> tuple:
        """
        Seek to a specific frame and read it.
        
        Args:
            frame_number: Frame index to seek to
            
        Returns:
            Tuple of (success, frame_data)
        """
        if not self.video_cap or not self.video_cap.isOpened():
            return False, None
        
        # Clamp frame number to valid range
        frame_number = max(0, min(int(frame_number), max(0, self.total_frames - 1)))
        self.current_frame = frame_number
        
        try:
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.video_cap.read()
        except Exception as e:
            print(f"[VideoController] Seek error: {e}", flush=True)
            return False, None
        
        return ret, frame
    
    def seek_to_frame_safe(self, frame_number: int) -> tuple:
        """
        Seek to a frame with re-entrancy protection.
        
        Args:
            frame_number: Frame index to seek to
            
        Returns:
            Tuple of (success, frame_data)
        """
        if self._seeking:
            return False, None
        
        self._seeking = True
        try:
            result = self.seek_to_frame(frame_number)
        finally:
            self._seeking = False
        
        return result
    
    def seek_to_frame_fast(self, frame_number: int) -> tuple:
        """
        Lightweight seek for drag operations (throttled).
        
        Args:
            frame_number: Frame index to seek to
            
        Returns:
            Tuple of (success, frame_data)
        """
        if self._fast_seek_lock:
            return False, None
        
        self._fast_seek_lock = True
        try:
            result = self.seek_to_frame(frame_number)
        finally:
            self._fast_seek_lock = False
        
        return result
    
    def advance_frame(self) -> tuple:
        """
        Advance to next frame.
        
        Returns:
            Tuple of (success, frame_data)
        """
        if not self.video_cap:
            return False, None
        
        ret, frame = self.video_cap.read()
        if ret:
            self.current_frame += 1
        
        return ret, frame
    
    def next_frame(self) -> int:
        """
        Calculate next frame number.
        
        Returns:
            Next frame index (clamped to valid range)
        """
        return min(self.current_frame + 1, self.total_frames - 1)
    
    def prev_frame(self) -> int:
        """
        Calculate previous frame number.
        
        Returns:
            Previous frame index (clamped to valid range)
        """
        return max(self.current_frame - 1, 0)
    
    def get_timer_interval(self) -> int:
        """
        Calculate timer interval for current playback rate.
        
        Returns:
            Timer interval in milliseconds
        """
        if self.fps > 0 and self.playback_rate > 0:
            return int(max(1, 1000.0 / (self.fps * self.playback_rate)))
        return 33  # Default ~30 fps
    
    def set_playback_rate(self, rate: float):
        """
        Set playback speed multiplier.
        
        Args:
            rate: Playback rate (0.5 = half speed, 2.0 = double speed, etc.)
        """
        if rate > 0:
            self.playback_rate = rate
    
    def reset(self):
        """Reset playback to beginning."""
        self.current_frame = 0
        self.is_playing = False
        if self.video_cap:
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    def get_duration_seconds(self) -> float:
        """
        Get total video duration in seconds.
        
        Returns:
            Duration in seconds
        """
        if self.fps > 0:
            return self.total_frames / self.fps
        return 0.0
    
    def get_current_time_seconds(self) -> float:
        """
        Get current playback position in seconds.
        
        Returns:
            Current time in seconds
        """
        if self.fps > 0:
            return self.current_frame / self.fps
        return 0.0
