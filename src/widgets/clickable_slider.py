"""
Clickable slider widget.

A custom QSlider that responds to clicks anywhere on the slider bar,
immediately jumping to the clicked position.
"""

from PyQt5 import QtWidgets, QtCore


class ClickableSlider(QtWidgets.QSlider):
    """
    Enhanced QSlider that allows clicking anywhere on the slider to seek.
    
    Standard QSlider requires dragging the handle. This widget allows users
    to click anywhere on the slider track to immediately jump to that position.
    
    Supports both horizontal and vertical orientations.
    """
    
    def mousePressEvent(self, event):
        """
        Handle mouse press events to implement click-to-seek functionality.
        
        Args:
            event: QMouseEvent containing click information
        """
        try:
            # Calculate value based on click position (supports Horizontal and Vertical)
            if self.orientation() == QtCore.Qt.Horizontal:
                x = event.pos().x()
                w = max(1, self.width())
                ratio = float(x) / float(w)
                ratio = max(0.0, min(1.0, ratio))
                mn = int(self.minimum())
                mx = int(self.maximum())
                val = int(round(mn + ratio * (mx - mn)))
                # Update value and emit sliderReleased signal to trigger seek
                self.setValue(val)
                try:
                    self.sliderReleased.emit()
                except Exception:
                    pass
            else:  # Vertical orientation
                y = event.pos().y()
                h = max(1, self.height())
                ratio = 1.0 - float(y) / float(h)
                ratio = max(0.0, min(1.0, ratio))
                mn = int(self.minimum())
                mx = int(self.maximum())
                val = int(round(mn + ratio * (mx - mn)))
                self.setValue(val)
                try:
                    self.sliderReleased.emit()
                except Exception:
                    pass
        except Exception:
            pass
        
        # Call default behavior to maintain normal interaction
        super().mousePressEvent(event)
