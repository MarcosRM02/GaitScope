"""
Video player main window.

This is the main application window that integrates all components:
video playback, data visualization, and user interface.
"""

import os
import sys
import re
from typing import Optional
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import cv2

from ..widgets import ClickableSlider, TimeAxis, HeatmapWidget
from ..constants import (
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_VIDEO_BACKGROUND,
    PLAYBACK_SPEED_OPTIONS,
    DEFAULT_PLOT_WINDOW_SECONDS,
)
from ..utils import format_time_mmss, find_video_file, find_csv_file
from .video_controller import VideoController
from .data_manager import DataManager
from .plot_manager import PlotManager
from .heatmap_adapter import HeatmapAdapter


class VideoPlayer(QtWidgets.QMainWindow):
    """
    Main video player window with integrated gait analysis visualization.
    
    This class serves as the main application window, coordinating:
    - Video playback via VideoController
    - Data management via DataManager  
    - Plot visualization via PlotManager
    - User interface and event handling
    """
    
    def __init__(self):
        """Initialize the video player application."""
        super().__init__()
        
        # Initialize controllers and managers
        self.video_controller = VideoController()
        self.data_manager = DataManager()
        
        # Initialize heatmap adapter
        self.heatmap_adapter = HeatmapAdapter()
        
        # UI state
        self.embedded_video_path: str = ''
        self.csv_paths: list = []
        self.heatmap_sync_enabled: bool = True  # Sync heatmap with video (enabled by default)
        self.base_heatmap_fps: float = 64.0  # Base FPS for heatmap (1.0x speed)
        
        # Setup window
        self.setWindowTitle("GaitScope")
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        
        # Build UI
        self._build_ui()
        
        # Initialize plot manager after UI is built
        # Provide optional horizontal legend container to PlotManager
        self.plot_manager = PlotManager(self.plot_widget, self.gaitrite_plot, getattr(self, 'plot_legend_container', None))
        
        # Connect video timer
        self.video_controller.timer.timeout.connect(self._on_timer)
        
        # Connect heatmap signals
        if self.heatmap_adapter.is_available():
            self.heatmap_adapter.frame_ready.connect(self.heatmap_widget.update_frame)
        
        print("[VideoPlayer] Initialized", flush=True)
    
    def _build_ui(self):
        """Build the user interface."""
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        # Main horizontal layout: left (video + plots stacked) and right (gaitrite full height)
        main_layout = QtWidgets.QHBoxLayout(central)

        # Left column: video+heatmap (top), CSV plots (bottom)
        left_column = QtWidgets.QVBoxLayout()
        
        # Top section: video (left) + heatmap (right)
        top_section = QtWidgets.QHBoxLayout()
        
        # Video section
        video_layout = self._build_video_section()
        top_section.addLayout(video_layout, 1)
        
        # Heatmap section
        heatmap_layout = self._build_heatmap_section()
        top_section.addLayout(heatmap_layout, 1)
        
        left_column.addLayout(top_section, 3)
        
        # CSV plots section (bottom)
        plot_layout = self._build_plot_section()
        left_column.addLayout(plot_layout, 2)

        main_layout.addLayout(left_column, 3)

        # Right column: gaitrite plot occupying full height as a margin
        self.gaitrite_plot = pg.PlotWidget(title='GaitRite Data')
        self._configure_gaitrite_plot()

        # Make gaitrite a narrow sidebar so main (video+plots) fills the rest
        try:
            self.gaitrite_plot.setMinimumWidth(260)
            self.gaitrite_plot.setMaximumWidth(360)
            self.gaitrite_plot.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        except Exception:
            pass

        main_layout.addWidget(self.gaitrite_plot, 1)

        # Ensure left column expands to fill remaining horizontal space
        try:
            main_layout.setStretch(0, 10)
            main_layout.setStretch(1, 1)
        except Exception:
            pass

        # Setup keyboard shortcuts
        self._setup_shortcuts()

        print("[VideoPlayer] UI constructed", flush=True)
    
    def _build_video_section(self) -> QtWidgets.QVBoxLayout:
        """
        Build the video display and controls section.
        
        Returns:
            Layout containing video and controls
        """
        layout = QtWidgets.QVBoxLayout()
        
        # Video display label
        self.video_label = QtWidgets.QLabel()
        self.video_label.setStyleSheet(f"background-color: {DEFAULT_VIDEO_BACKGROUND};")
        self.video_label.setAlignment(QtCore.Qt.AlignCenter)
        # Make the label expand/shrink with the window and avoid automatic pixmap stretching
        try:
            self.video_label.setScaledContents(False)
            self.video_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        except Exception:
            pass
        layout.addWidget(self.video_label, 8)
        
        # Control buttons
        controls_layout = self._build_controls()
        layout.addLayout(controls_layout)
        
        # Progress slider and labels
        progress_layout = self._build_progress_section()
        layout.addLayout(progress_layout)
        
        return layout
    
    def _build_controls(self) -> QtWidgets.QHBoxLayout:
        """
        Build the playback control buttons.
        
        Returns:
            Layout containing control buttons
        """
        layout = QtWidgets.QHBoxLayout()

        # Dataset selector
        self._add_dataset_selector(layout)
        
        # Play/Pause button
        self.btn_play = QtWidgets.QPushButton('▶ Play')
        self.btn_play.clicked.connect(self.toggle_play_pause)
        layout.addWidget(self.btn_play)

        # Reset button
        self.btn_stop = QtWidgets.QPushButton('⏹ Reset')
        self.btn_stop.clicked.connect(self.stop)
        layout.addWidget(self.btn_stop)
        
         # Previous frame button
        self.btn_prev_frame = QtWidgets.QPushButton('◀ Frame')
        self.btn_prev_frame.clicked.connect(self.prev_frame)
        layout.addWidget(self.btn_prev_frame)

        # Next frame button
        self.btn_next_frame = QtWidgets.QPushButton('Frame ▶')
        self.btn_next_frame.clicked.connect(self.next_frame)
        layout.addWidget(self.btn_next_frame)

        # Speed control
        self._add_speed_control(layout)
        
        return layout
    
    def _add_speed_control(self, layout: QtWidgets.QHBoxLayout):
        """
        Add playback speed control to layout.
        
        Args:
            layout: Layout to add control to
        """
        try:
            self.speed_label = QtWidgets.QLabel('Speed:')
            layout.addWidget(self.speed_label)
            
            self.cmb_speed = QtWidgets.QComboBox()
            labels = [f'{rate:.2f}x' for rate in PLAYBACK_SPEED_OPTIONS]
            for lbl in labels:
                self.cmb_speed.addItem(lbl)
            
            # Set default to 1.0x
            try:
                default_idx = PLAYBACK_SPEED_OPTIONS.index(1.0)
            except ValueError:
                default_idx = 0
            self.cmb_speed.setCurrentIndex(default_idx)
            
            self.cmb_speed.currentIndexChanged.connect(
                lambda i: self.set_playback_rate(PLAYBACK_SPEED_OPTIONS[int(i)])
            )
            layout.addWidget(self.cmb_speed)
        except Exception:
            pass
    
    def _add_dataset_selector(self, layout: QtWidgets.QHBoxLayout):
        """
        Add cascading dataset selector controls.
        
        Args:
            layout: Layout to add selectors to
        """
        try:
            # Subject selector
            layout.addWidget(QtWidgets.QLabel('Subject:'))
            self.combo_subject = QtWidgets.QComboBox()
            self.combo_subject.setToolTip('Select participant folder (e.g., P1, P2)')
            layout.addWidget(self.combo_subject)
            
            # Category selector
            layout.addWidget(QtWidgets.QLabel('Category:'))
            self.combo_group = QtWidgets.QComboBox()
            self.combo_group.setToolTip('Select category (FP, NP, SP, etc.)')
            self.combo_group.setEnabled(False)
            layout.addWidget(self.combo_group)
            
            # Session selector
            layout.addWidget(QtWidgets.QLabel('Session:'))
            self.combo_session = QtWidgets.QComboBox()
            self.combo_session.setToolTip('Select session (e.g., 1, 2, ...)')
            self.combo_session.setEnabled(False)
            layout.addWidget(self.combo_session)
            
            # Load button
            self.btn_load_dataset = QtWidgets.QPushButton('Load Dataset')
            self.btn_load_dataset.clicked.connect(self.on_load_dataset_clicked)
            self.btn_load_dataset.setEnabled(False)
            layout.addWidget(self.btn_load_dataset)
            
            # Populate subjects and connect signals
            self.populate_subjects()
            self.combo_subject.currentIndexChanged.connect(self.on_subject_changed)
            self.combo_group.currentIndexChanged.connect(self.on_group_changed)
        except Exception:
            pass
    
    def _build_progress_section(self) -> QtWidgets.QHBoxLayout:
        """
        Build the progress slider and time labels section.
        
        Returns:
            Layout containing progress controls
        """
        layout = QtWidgets.QHBoxLayout()
        
        # Progress slider
        self.progress_slider = ClickableSlider(QtCore.Qt.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(0)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        self.progress_slider.sliderMoved.connect(self.on_slider_moved)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        layout.addWidget(self.progress_slider, 8)
        
        # Time label
        self.time_label = QtWidgets.QLabel('00:00 / 00:00')
        layout.addWidget(self.time_label, 1)
        
        # Frame label
        self.frame_label = QtWidgets.QLabel('Frame: 0 / 0')
        layout.addWidget(self.frame_label, 1)
        
        return layout
    
    def _build_plot_section(self) -> QtWidgets.QVBoxLayout:
        """
        Build the plot visualization section (CSV plots only).
        Returns:
            Layout containing the CSV plot widget and labels
        """
        layout = QtWidgets.QVBoxLayout()

        # CSV index label
        self.csv_index_label = QtWidgets.QLabel('CSV: - / -')
        layout.addWidget(self.csv_index_label, 0)

        # Horizontal legend container to be populated by PlotManager (placed above plot)
        self.plot_legend_container = QtWidgets.QWidget()
        try:
            self.plot_legend_container.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
            hl = QtWidgets.QHBoxLayout(self.plot_legend_container)
            hl.setContentsMargins(4, 2, 4, 2)
            hl.setSpacing(12)
        except Exception:
            # ensure we at least have a layout
            try:
                self.plot_legend_container.setLayout(QtWidgets.QHBoxLayout())
            except Exception:
                pass
        layout.addWidget(self.plot_legend_container, 0)

        # CSV data plot
        self.time_axis = TimeAxis(orientation='bottom')
        self.plot_widget = pg.PlotWidget(
            axisItems={'bottom': self.time_axis}, 
            title='Pressure Sensor Data'
        )
        # Ensure plot widget has a clean default appearance; specific visuals handled in PlotManager
        try:
            self.plot_widget.showGrid(x=False, y=False)
            self.plot_widget.addLegend(offset=(10, 10))
        except Exception:
            pass
        layout.addWidget(self.plot_widget, 1)

        return layout
    
    def _build_heatmap_section(self) -> QtWidgets.QVBoxLayout:
        """
        Build the heatmap visualization section.
        Returns:
            Layout containing the heatmap widget and controls
        """
        layout = QtWidgets.QVBoxLayout()
        
        # Heatmap controls and info
        heatmap_header = QtWidgets.QHBoxLayout()
        self.heatmap_label = QtWidgets.QLabel('Heatmap: Ready')
        heatmap_header.addWidget(self.heatmap_label)
        heatmap_header.addStretch()
        
        layout.addLayout(heatmap_header, 0)
        
        # Heatmap display widget
        self.heatmap_widget = HeatmapWidget()
        layout.addWidget(self.heatmap_widget, 1)
        
        # Heatmap controls
        heatmap_controls = self._build_heatmap_controls()
        layout.addLayout(heatmap_controls, 0)

        return layout
    
    def _build_heatmap_controls(self) -> QtWidgets.QHBoxLayout:
        """
        Build the heatmap control buttons and settings.

        Returns:
            Layout containing heatmap controls
        """
        layout = QtWidgets.QHBoxLayout()

        # Play/Pause button for heatmap (hidden - controlled by main video play button)
        self.btn_heatmap_play = QtWidgets.QPushButton('▶ Play')
        self.btn_heatmap_play.clicked.connect(self._toggle_heatmap_play)
        self.btn_heatmap_play.setEnabled(False)
        self.btn_heatmap_play.setVisible(False)  # Hide - unified control via video play button
        layout.addWidget(self.btn_heatmap_play)

        # NOTE: FPS spinbox and "Sync with video" checkbox removed because heatmap will
        # always be synchronized with the video. Keeping UI minimal.

        layout.addStretch()

        return layout
    
    def _configure_gaitrite_plot(self):
        """Configure the GaitRite plot widget."""
        try:
            self.gaitrite_plot.setBackground('white')
            self.gaitrite_plot.setMouseEnabled(x=False, y=False)
            self.gaitrite_plot.setMenuEnabled(False)
            try:
                self.gaitrite_plot.hideButtons()
            except Exception:
                pass
            self.gaitrite_plot.setMinimumSize(400, 300)
            
            plot_item = self.gaitrite_plot.getPlotItem()
            try:
                plot_item.setLabel('left', 'Length (cm)', 
                                  **{'color': '#2c3e50', 'font-size': '10pt'})
                plot_item.setLabel('bottom', 'Width (cm)', 
                                   **{'color': '#2c3e50', 'font-size': '10pt'})
            except Exception:
                pass
            plot_item.showGrid(True, True, alpha=0.3)

            # Reduce margins so the carpet drawing is closer to the Y axis
            try:
                left_axis = plot_item.getAxis('left')
                bottom_axis = plot_item.getAxis('bottom')

                try:
                    # Reduce reserved width for left axis (was 40)
                    left_axis.setWidth(18)
                except Exception:
                    pass

                try:
                    # Reduce reserved height for bottom axis (was 28)
                    bottom_axis.setHeight(18)
                except Exception:
                    pass

                try:
                    # Reduce tick label offsets to bring ticks closer to the plot
                    left_axis.setStyle(tickTextOffset=2)
                    bottom_axis.setStyle(tickTextOffset=2)
                except Exception:
                    pass
            except Exception:
                pass

            try:
                # Remove extra widget margins and reduce spacing inside plot so drawing sits closer to axes
                self.gaitrite_plot.setContentsMargins(0, 0, 0, 0)
                try:
                    # Also try to reduce any internal ViewBox padding by setting a tighter range later (view ranges use padding=0)
                    vb = plot_item.getViewBox()
                    try:
                        # Some versions expose an attribute to control padding; disable unnecessary padding if available
                        vb.setPadding(0)
                    except Exception:
                        pass
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        QtWidgets.QShortcut(QtGui.QKeySequence('Space'), self, 
                           activated=self.toggle_play_pause)
        QtWidgets.QShortcut(QtGui.QKeySequence('Left'), self, 
                           activated=self.prev_frame)
        QtWidgets.QShortcut(QtGui.QKeySequence('Right'), self, 
                           activated=self.next_frame)
    
    # ==================== Video Control Methods ====================
    
    def toggle_play_pause(self):
        """Toggle between play and pause states."""
        if not self.video_controller.video_cap:
            return

        if self.video_controller.is_playing:
            # Pause video
            self.video_controller.is_playing = False
            self.video_controller.timer.stop()
            self.btn_play.setText('▶ Play')

            # Pause heatmap (always synced)
            if self.heatmap_adapter.is_available():
                if self.heatmap_adapter.worker and self.heatmap_adapter.worker._playing:
                    self.heatmap_adapter.pause()
                    self.btn_heatmap_play.setText('▶ Play')
        else:
            # Play video
            self.video_controller.is_playing = True
            interval = self.video_controller.get_timer_interval()
            self.video_controller.timer.start(interval)
            self.btn_play.setText('⏸ Pause')

            # Start/resume heatmap (always synced)
            if self.heatmap_adapter.is_available():
                if self.heatmap_adapter.worker is None:
                    # Start the heatmap worker
                    self.heatmap_adapter.start()
                    self.heatmap_adapter.resume()
                    self.btn_heatmap_play.setText('⏸ Pause')
                    # Ensure heatmap is aligned with current video frame
                    self._sync_heatmap_to_video()
                elif not self.heatmap_adapter.worker._playing:
                    # Resume heatmap
                    self.heatmap_adapter.resume()
                    self.btn_heatmap_play.setText('⏸ Pause')
                    # Ensure heatmap is aligned with current video frame
                    self._sync_heatmap_to_video()
    
    def stop(self):
        """Stop playback and reset to beginning."""
        self.video_controller.reset()
        self.video_controller.timer.stop()
        self.btn_play.setText('▶ Play')
        self.progress_slider.setValue(0)
        self.update_time_label()
        if self.video_controller.video_cap:
            self.show_frame()

        # Stop and reset heatmap
        if self.heatmap_adapter.is_available():
            if self.heatmap_adapter.worker:
                self.heatmap_adapter.pause()
                self.heatmap_adapter.seek(0)  # Reset to first frame
                self.btn_heatmap_play.setText('▶ Play')
    
    def next_frame(self):
        """Advance to next frame."""
        if not self.video_controller.video_cap:
            return
        if self.video_controller.is_playing:
            self.toggle_play_pause()
        new_frame = self.video_controller.next_frame()
        self.seek_to_frame(new_frame)
    
    def prev_frame(self):
        """Go to previous frame."""
        if not self.video_controller.video_cap:
            return
        if self.video_controller.is_playing:
            self.toggle_play_pause()
        new_frame = self.video_controller.prev_frame()
        self.seek_to_frame(new_frame)
    
    def seek_to_frame(self, frame_number: int):
        """
        Seek to a specific frame with safety checks.
        
        Args:
            frame_number: Target frame number
        """
        ret, frame = self.video_controller.seek_to_frame_safe(frame_number)
        if ret and frame is not None:
            self._display_frame(frame)
        self.progress_slider.setValue(self.video_controller.current_frame)
        self.update_time_label()
        self._update_csv_cursor_from_video()
    
    def set_playback_rate(self, rate: float):
        """
        Set playback speed for both video and heatmap.
        
        Args:
            rate: Playback rate multiplier (e.g., 0.5x, 1.0x, 2.0x)
        """
        # Update video playback rate
        self.video_controller.set_playback_rate(rate)
        if self.video_controller.is_playing:
            interval = self.video_controller.get_timer_interval()
            self.video_controller.timer.start(interval)

        # Update heatmap FPS proportionally
        new_heatmap_fps = int(self.base_heatmap_fps * rate)
        if self.heatmap_adapter.is_available():
            self.heatmap_adapter.set_rate(float(new_heatmap_fps))
    
    def _on_timer(self):
        """Handle timer tick for video playback."""
        ret, frame = self.video_controller.advance_frame()

        if not ret:
            self.video_controller.is_playing = False
            self.video_controller.timer.stop()
            self.btn_play.setText('▶ Play')
            # Pause heatmap as well
            if self.heatmap_adapter.is_available():
                if self.heatmap_adapter.worker and self.heatmap_adapter.worker._playing:
                    self.heatmap_adapter.pause()
                    self.btn_heatmap_play.setText('▶ Play')
            return

        self._display_frame(frame)
        self._update_csv_cursor_from_video()
        self.progress_slider.setValue(self.video_controller.current_frame)
        self.update_time_label()

        if self.video_controller.current_frame >= self.video_controller.total_frames - 1:
            self.video_controller.is_playing = False
            self.video_controller.timer.stop()
            self.btn_play.setText('▶ Play')
            # Pause heatmap as well
            if self.heatmap_adapter.is_available():
                if self.heatmap_adapter.worker and self.heatmap_adapter.worker._playing:
                    self.heatmap_adapter.pause()
                    self.btn_heatmap_play.setText('▶ Play')
    
    # ==================== Heatmap Control Methods ====================
    
    def _toggle_heatmap_play(self):
        """Toggle heatmap animation play/pause."""
        print("[VideoPlayer] _toggle_heatmap_play called", flush=True)

        if not self.heatmap_adapter.is_available():
            print("[VideoPlayer] Heatmap adapter not available", flush=True)
            return

        # Check if we have worker running
        if self.heatmap_adapter.worker is None:
            print("[VideoPlayer] Starting heatmap adapter (no worker)...", flush=True)
            # Start the adapter
            self.heatmap_adapter.start()
            self.heatmap_adapter.resume()
            self.btn_heatmap_play.setText('⏸ Pause')
            # Keep heatmap synced with video when starting via this control
            self._sync_heatmap_to_video()
        elif self.heatmap_adapter.worker._playing:
            print("[VideoPlayer] Pausing heatmap...", flush=True)
            # Pause
            self.heatmap_adapter.pause()
            self.btn_heatmap_play.setText('▶ Play')
        else:
            print("[VideoPlayer] Resuming heatmap...", flush=True)
            # Resume
            self.heatmap_adapter.resume()
            self.btn_heatmap_play.setText('⏸ Pause')
            # Keep heatmap synced with video when resuming via this control
            self._sync_heatmap_to_video()
    
    # ==================== Display Methods ====================
    
    def show_frame(self):
        """Display the current frame."""
        ret, frame = self.video_controller.seek_to_frame(
            self.video_controller.current_frame
        )
        if ret and frame is not None:
            self._display_frame(frame)
            self._update_csv_cursor_from_video()
    
    def _display_frame(self, frame_bgr):
        """
        Display a frame in the video label.
        
        Args:
            frame_bgr: Frame in BGR format (OpenCV)
        """
        try:
            h0, w0 = frame_bgr.shape[:2]
            target_w = max(1, self.video_label.width())
            target_h = max(1, self.video_label.height())

            # Convert BGR -> RGB and create QImage
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            bytes_per_line = 3 * w0
            image = QtGui.QImage(frame_rgb.data, w0, h0, bytes_per_line, QtGui.QImage.Format_RGB888)
            pix = QtGui.QPixmap.fromImage(image)

            # Scale to fit inside label while preserving aspect ratio (no cropping)
            pix = pix.scaled(target_w, target_h, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.video_label.setPixmap(pix)
        except Exception:
            try:
                # Fallback: basic conversion and keep aspect ratio
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                h, w = frame_rgb.shape[:2]
                bytes_per_line = 3 * w
                image = QtGui.QImage(frame_rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
                pix = QtGui.QPixmap.fromImage(image).scaled(
                    max(1, self.video_label.width()),
                    max(1, self.video_label.height()),
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation
                )
                self.video_label.setPixmap(pix)
            except Exception:
                pass
    
    def update_time_label(self):
        """Update time and frame labels."""
        if not self.video_controller.video_cap or self.video_controller.fps == 0:
            self.time_label.setText('00:00 / 00:00')
            self.frame_label.setText('Frame: 0 / 0')
            return
        
        current_time = self.video_controller.get_current_time_seconds()
        total_time = self.video_controller.get_duration_seconds()
        
        self.time_label.setText(
            f"{format_time_mmss(current_time)} / {format_time_mmss(total_time)}"
        )
        self.frame_label.setText(
            f"Frame: {self.video_controller.current_frame} / "
            f"{max(0, self.video_controller.total_frames - 1)}"
        )
    
    # ==================== Slider Event Handlers ====================
    
    def on_slider_pressed(self):
        """Mark start of slider drag."""
        pass  # Placeholder for drag state if needed
    
    def on_slider_moved(self, val: int):
        """
        Handle slider movement during drag.
        
        Args:
            val: New slider value
        """
        # Perform lightweight seek during drag
        ret, frame = self.video_controller.seek_to_frame_fast(val)
        if ret and frame is not None:
            self._display_frame(frame)
        self.update_time_label()
        self._update_csv_cursor_from_video()
    
    def on_slider_released(self):
        """Handle slider release after drag."""
        val = self.progress_slider.value()
        self.seek_to_frame(val)
    
    # ==================== Data Loading Methods ====================
    
    def load_video(self, path: str):
        """
        Load a video file.
        
        Args:
            path: Path to video file
        """
        print(f"[VideoPlayer] Loading video: {path}", flush=True)
        if self.video_controller.is_playing:
            self.stop()
        
        if not self.video_controller.load_video(path):
            QtWidgets.QMessageBox.critical(self, 'Error', 'Could not open video file')
            return
        
        self.progress_slider.setMaximum(
            max(0, self.video_controller.total_frames - 1)
        )
        self.update_time_label()
        self.show_frame()
    
    def load_csvs(self):
        """Load and plot CSV data files."""
        print("[VideoPlayer] Loading CSV data", flush=True)
        # DEBUG: show current csv_paths
        print(f"[VideoPlayer] csv_paths: {getattr(self, 'csv_paths', None)}", flush=True)

        # Find L.csv
        csv_L = None
        for p in self.csv_paths:
            if p and os.path.exists(p):
                csv_L = p
                break

        if not csv_L:
            self.plot_widget.clear()
            try:
                self.plot_widget.plot([0], [0], pen=pg.mkPen('k'))
            except Exception:
                pass
            print("[VideoPlayer] No CSV found", flush=True)
            return

        # Try to find R.csv in same directory
        csv_dir = os.path.dirname(csv_L)
        csv_R = os.path.join(csv_dir, 'R.csv')

        # Load data
        if not self.data_manager.load_csv_data(csv_L, csv_R if os.path.exists(csv_R) else None):
            QtWidgets.QMessageBox.warning(self, 'Warning', 'Error loading CSV data')
            return

        # Create plots
        x_data = self.data_manager.get_time_axis()
        self.plot_manager.create_csv_plots(
            x_data,
            self.data_manager.sums_L,
            self.data_manager.sums_R
        )

        # Set initial X range to full CSV duration so all data is visible
        total_seconds = float(self.data_manager.csv_len) / float(
            self.data_manager.csv_sampling_rate
        ) if self.data_manager.csv_sampling_rate > 0 else float(self.data_manager.csv_len)
        self.plot_manager.set_plot_x_range(0, total_seconds)

        # Update cursor
        self._update_csv_cursor_from_video()
        print("[VideoPlayer] CSV data loaded", flush=True)
    
    def load_gaitrite_data(self):
        """Load and display GaitRite data."""
        # Find base directory from CSV paths
        base_dir = None
        for p in self.csv_paths:
            if os.path.exists(p):
                base_dir = os.path.dirname(p)
                break
        
        if not base_dir:
            return
        
        # Load data
        if self.data_manager.load_gaitrite_data(base_dir):
            # Draw footprints if available
            if (self.data_manager.footprints_left_df is not None or 
                self.data_manager.footprints_right_df is not None):
                self.plot_manager.draw_gaitrite_footprints(
                    self.data_manager.footprints_left_df,
                    self.data_manager.footprints_right_df,
                    self.data_manager.gaitrite_df
                )
            else:
                self.plot_manager.draw_gaitrite_carpet()
        else:
            self.plot_manager.draw_gaitrite_carpet()
    
    def load_heatmap_data(self):
        """Load and configure heatmap data from already loaded CSV data."""
        if not self.heatmap_adapter.is_available():
            print("[VideoPlayer] Heatmap adapter not available", flush=True)
            return
        
        # Get heatmap data from DataManager (reuses already loaded CSV data)
        heatmap_data = self.data_manager.get_heatmap_data()
        
        if heatmap_data and (heatmap_data['left_seq'] or heatmap_data['right_seq']):
            # Set data in adapter
            self.heatmap_adapter.set_data(
                heatmap_data['left_coords'],
                heatmap_data['right_coords'],
                heatmap_data['left_seq'],
                heatmap_data['right_seq']
            )
            
            # Enable heatmap controls
            self.btn_heatmap_play.setEnabled(True)
            
            # Update label
            total_frames = self.heatmap_adapter.get_total_frames()
            self.heatmap_label.setText(f'Heatmap: {total_frames} frames loaded')
            
            # Show initial frame immediately
            self.heatmap_adapter.show_initial_frame()
            
            # If sync is enabled (default), sync to current video position
            if self.heatmap_sync_enabled:
                self._sync_heatmap_to_video()
            
            print(f"[VideoPlayer] Heatmap data loaded: {total_frames} frames", flush=True)
        else:
            print("[VideoPlayer] No heatmap data available", flush=True)
            self.btn_heatmap_play.setEnabled(False)
            self.heatmap_label.setText('Heatmap: No data')
    
    # ==================== CSV Cursor Synchronization ====================
    
    def _update_csv_cursor_from_video(self):
        """Update CSV plot cursor based on current video frame."""
        if self.data_manager.sums_L is None:
            return

        # Translate current video frame into a CSV index, then clamp to valid range.
        csv_idx = self.data_manager.video_frame_to_csv_index(
            self.video_controller.current_frame,
            self.video_controller.fps
        )

        # Ensure csv_idx is within [0, csv_len-1] to avoid out-of-range times
        if hasattr(self.data_manager, 'csv_len') and self.data_manager.csv_len > 0:
            csv_idx = max(0, min(int(csv_idx), int(self.data_manager.csv_len) - 1))
        else:
            try:
                csv_idx = int(csv_idx)
            except Exception:
                csv_idx = 0

        # Compute CSV time from clamped index
        csv_time = float(csv_idx) / float(self.data_manager.csv_sampling_rate) \
            if getattr(self.data_manager, 'csv_sampling_rate', 0) > 0 else float(csv_idx)

        # Update cursor position (vertical yellow line)
        self.plot_manager.update_cursor_position(
            csv_time,
            self.data_manager.sums_L,
            self.data_manager.sums_R,
            csv_idx
        )
        
        # Sync heatmap if enabled
        if self.heatmap_sync_enabled:
            self._sync_heatmap_to_video()

        # Update markers and connecting segment
        x_data = self.data_manager.get_time_axis()
        self.plot_manager.update_markers(
            csv_idx,
            x_data,
            self.data_manager.sums_L,
            self.data_manager.sums_R
        )

        # Update label
        total_idx = self.data_manager.csv_len - 1 if getattr(self.data_manager, 'csv_len', 0) > 0 else 0
        time_str = format_time_mmss(csv_time)
        self.csv_index_label.setText(
            f'CSV idx: {csv_idx} / {total_idx}   t={time_str}'
        )

    def _sync_heatmap_to_video(self):
        """Synchronize heatmap frame with video frame.

        Maps current video frame proportionally into the heatmap frame index and
        seeks the heatmap adapter to that frame. This method was accidentally
        removed earlier; restore it so other code can call it safely.
        """
        if not self.heatmap_adapter.is_available():
            return

        try:
            video_frame = int(self.video_controller.current_frame)
            video_total = int(self.video_controller.total_frames) if getattr(self.video_controller, 'total_frames', 0) is not None else 0
            heatmap_total = int(self.heatmap_adapter.get_total_frames());

            if video_total > 0 and heatmap_total > 0:
                heatmap_frame = int((video_frame / max(1, video_total)) * heatmap_total)
                # clamp
                heatmap_frame = max(0, min(heatmap_frame, heatmap_total - 1))
                self.heatmap_adapter.seek(heatmap_frame)
        except Exception:
            # be silent on sync errors to avoid interrupting UI
            pass

    # ==================== Dataset Selector Methods ====================
    
    def populate_subjects(self):
        """Populate subject combo box with available subjects."""
        try:
            base_dir = os.path.abspath(os.path.dirname(__file__))
            # Go up to package root
            base_dir = os.path.dirname(os.path.dirname(base_dir))
            data_dir = os.path.join(base_dir, 'data')
            
            self.combo_subject.clear()
            self.combo_group.clear()
            self.combo_session.clear()
            self.combo_group.setEnabled(False)
            self.combo_session.setEnabled(False)
            self.btn_load_dataset.setEnabled(False)
            
            if not os.path.isdir(data_dir):
                self.combo_subject.setEnabled(False)
                return
            
            subjects = [d for d in os.listdir(data_dir) 
                       if os.path.isdir(os.path.join(data_dir, d)) 
                       and d.upper().startswith('P')]

            # Sort participants numerically by the number after 'P' (P1, P2, P10)
            def _subj_key(name: str):
                m = re.match(r'^P0*([0-9]+)', name.upper())
                if m:
                    try:
                        return (int(m.group(1)), name.upper())
                    except Exception:
                        pass
                return (10**9, name.upper())

            subjects.sort(key=_subj_key)
            
            self.combo_subject.addItem('Select subject...', userData=None)
            for s in subjects:
                self.combo_subject.addItem(s, userData=os.path.join(data_dir, s))
            
            self.combo_subject.setCurrentIndex(0)
            self.combo_subject.setEnabled(True)
        except Exception:
            pass
    
    def on_subject_changed(self, index: int):
        """Handle subject selection change."""
        if index < 0:
            return
        subject_path = self.combo_subject.itemData(index)
        if not subject_path:
            self.combo_group.clear()
            self.combo_session.clear()
            self.combo_group.setEnabled(False)
            self.combo_session.setEnabled(False)
            self.btn_load_dataset.setEnabled(False)
            return
        self.populate_groups(subject_path)
        self.btn_load_dataset.setEnabled(True)
    
    def populate_groups(self, subject_path: str):
        """Populate category combo box for selected subject."""
        try:
            self.combo_group.clear()
            self.combo_session.clear()
            self.combo_group.setEnabled(False)
            self.combo_session.setEnabled(False)
            
            if not subject_path or not os.path.isdir(subject_path):
                return
            
            groups = [d for d in os.listdir(subject_path) 
                     if os.path.isdir(os.path.join(subject_path, d))
                     and d.lower() not in ('sitdown', 'stand')]
            groups.sort()
            
            self.combo_group.addItem('Select category...', userData=None)
            for g in groups:
                self.combo_group.addItem(g, userData=os.path.join(subject_path, g))
            
            self.combo_group.setCurrentIndex(0)
            self.combo_group.setEnabled(True)
        except Exception:
            pass
    
    def on_group_changed(self, index: int):
        """Handle category selection change."""
        if index < 0:
            return
        group_path = self.combo_group.itemData(index)
        if not group_path:
            self.combo_session.clear()
            self.combo_session.setEnabled(False)
            return
        self.populate_sessions(group_path)

    def populate_sessions(self, group_path: str):
        """Populate session combo box for selected group."""
        try:
            self.combo_session.clear()
            self.combo_session.setEnabled(False)

            if not group_path or not os.path.isdir(group_path):
                return

            # Sessions are stored as subdirectories under the group folder
            sessions = [d for d in os.listdir(group_path)
                        if os.path.isdir(os.path.join(group_path, d))]

            # Numeric sort where possible (e.g., 1,2,10)
            def _sess_key(name: str):
                m = re.match(r'^0*([0-9]+)', name)
                if m:
                    try:
                        return (int(m.group(1)), name)
                    except Exception:
                        pass
                return (10**9, name)

            sessions.sort(key=_sess_key)

            self.combo_session.addItem('Select session...', userData=None)
            for s in sessions:
                self.combo_session.addItem(s, userData=os.path.join(group_path, s))

            self.combo_session.setCurrentIndex(0)
            self.combo_session.setEnabled(True)

            # Connect session change handler (safe to call multiple times)
            try:
                self.combo_session.currentIndexChanged.connect(self.on_session_changed)
            except Exception:
                pass
        except Exception:
            pass

    def on_session_changed(self, index: int):
        """Handle session selection change and locate CSV/video paths."""
        if index < 0:
            return
        session_path = self.combo_session.itemData(index)
        if not session_path:
            self.csv_paths = []
            self.btn_load_dataset.setEnabled(False)
            return

        # Try to find L.csv (case-insensitive) inside session folder
        csv_L = None
        try:
            for fname in ('L.csv', 'l.csv'):
                p = os.path.join(session_path, fname)
                if os.path.exists(p):
                    csv_L = p
                    break

            if not csv_L:
                for f in os.listdir(session_path):
                    if f.lower().startswith('l') and f.lower().endswith('.csv'):
                        csv_L = os.path.join(session_path, f)
                        break
        except Exception:
            csv_L = None

        self.csv_paths = [csv_L] if csv_L else []

        # Try to find an anonymized video inside the session folder
        try:
            video = find_video_file(session_path)
            if video:
                self.embedded_video_path = video
        except Exception:
            pass

        print(f"[VideoPlayer] on_session_changed: session_path={session_path}, csv_paths={self.csv_paths}, video={getattr(self, 'embedded_video_path', None)}", flush=True)
        self.btn_load_dataset.setEnabled(True)

    def on_load_dataset_clicked(self):
        """Handle Load Dataset button click: load CSVs, gaitrite data and embedded video if present."""
        print("[VideoPlayer] on_load_dataset_clicked called", flush=True)
        print(f"[VideoPlayer] current csv_paths={getattr(self, 'csv_paths', None)}", flush=True)

        if not getattr(self, 'csv_paths', None):
            QtWidgets.QMessageBox.warning(self, 'Warning', 'No CSV selected')
            return

        # Load CSVs and plots
        self.load_csvs()

        # Load gaitrite footprints/carpet
        self.load_gaitrite_data()

        # Load heatmap data
        self.load_heatmap_data()

        # Load embedded video if available
        if getattr(self, 'embedded_video_path', None):
            self.load_video(self.embedded_video_path)
    
    def closeEvent(self, event):
        """Handle window close event - cleanup resources."""
        print("[VideoPlayer] Closing window, stopping heatmap adapter...", flush=True)
        
        # Stop heatmap adapter
        if hasattr(self, 'heatmap_adapter') and self.heatmap_adapter:
            self.heatmap_adapter.stop()
        
        # Accept the close event
        event.accept()
