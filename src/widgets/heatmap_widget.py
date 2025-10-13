"""
HeatmapWidget - Qt widget for displaying heatmap animation

This widget provides a QLabel-based display for heatmap frames,
with automatic aspect-ratio preserving scaling and efficient
frame updates via Qt signals.
"""

import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
import cv2


class HeatmapWidget(QtWidgets.QWidget):
    """
    Widget for displaying heatmap animation frames.
    
    Displays numpy arrays as QPixmap with automatic scaling to fit
    the widget size while preserving aspect ratio.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create label for displaying frames
        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #f0f0f0;")
        self.image_label.setScaledContents(False)
        
        layout.addWidget(self.image_label)
        
        # Current frame
        self._current_frame = None
        self._original_pixmap = None
        
        # Set minimum size
        self.setMinimumSize(300, 400)
    
    @QtCore.pyqtSlot(np.ndarray)
    def update_frame(self, frame: np.ndarray):
        """
        Update the displayed frame.
        
        Args:
            frame: BGR numpy array (as returned by Heatmap animator)
        """
        if frame is None or frame.size == 0:
            return
        
        try:
            # Store current frame
            self._current_frame = frame
            
            # Convert BGR to RGB
            h, w = frame.shape[:2]
            if frame.dtype == np.float32 or frame.dtype == np.float64:
                # Convert to uint8 if needed
                frame_rgb = cv2.cvtColor((frame * 255).astype(np.uint8), cv2.COLOR_BGR2RGB)
            else:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Create QImage
            bytes_per_line = 3 * w
            qimg = QtGui.QImage(
                frame_rgb.data, 
                w, 
                h, 
                bytes_per_line, 
                QtGui.QImage.Format_RGB888
            )
            
            # Create pixmap
            self._original_pixmap = QtGui.QPixmap.fromImage(qimg)
            
            # Scale to fit label while preserving aspect ratio
            self._scale_and_display()
            
        except Exception as e:
            print(f"[HeatmapWidget] Error updating frame: {e}", flush=True)
    
    def _scale_and_display(self):
        """Scale the original pixmap to fit the label."""
        if self._original_pixmap is None:
            return
        
        # Get label size
        label_size = self.image_label.size()
        
        # Scale pixmap to fit label while preserving aspect ratio
        scaled_pixmap = self._original_pixmap.scaled(
            label_size,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        
        # Display scaled pixmap
        self.image_label.setPixmap(scaled_pixmap)
    
    def resizeEvent(self, event):
        """Handle widget resize by rescaling the current frame."""
        super().resizeEvent(event)
        self._scale_and_display()
    
    def clear(self):
        """Clear the displayed frame."""
        self.image_label.clear()
        self._current_frame = None
        self._original_pixmap = None
