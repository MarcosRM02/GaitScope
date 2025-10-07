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

from ..widgets import ClickableSlider, TimeAxis
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
        
        # UI state
        self.embedded_video_path: str = ''
        self.csv_paths: list = []
        
        # Setup window
        self.setWindowTitle("Video Gait Analyzer")
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        
        # Build UI
        self._build_ui()
        
        # Initialize plot manager after UI is built
        self.plot_manager = PlotManager(self.plot_widget, self.gaitrite_plot)
        
        # Connect video timer
        self.video_controller.timer.timeout.connect(self._on_timer)
        
        print("[VideoPlayer] Initialized", flush=True)
    
    def _build_ui(self):
        """Build the user interface."""
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        
        # Main horizontal layout: video | plots
        main_layout = QtWidgets.QHBoxLayout(central)
        
        # Left side: video and controls
        left_layout = self._build_video_section()
        main_layout.addLayout(left_layout, 2)
        
        # Right side: plots
        right_layout = self._build_plot_section()
        main_layout.addLayout(right_layout, 3)
        
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
        
        # Previous frame button
        self.btn_prev_frame = QtWidgets.QPushButton('◀ Frame')
        self.btn_prev_frame.clicked.connect(self.prev_frame)
        layout.addWidget(self.btn_prev_frame)
        
        # Play/Pause button
        self.btn_play = QtWidgets.QPushButton('▶ Play')
        self.btn_play.clicked.connect(self.toggle_play_pause)
        layout.addWidget(self.btn_play)
        
        # Next frame button
        self.btn_next_frame = QtWidgets.QPushButton('Frame ▶')
        self.btn_next_frame.clicked.connect(self.next_frame)
        layout.addWidget(self.btn_next_frame)
        
        # Reset button
        self.btn_stop = QtWidgets.QPushButton('⏹ Reset')
        self.btn_stop.clicked.connect(self.stop)
        layout.addWidget(self.btn_stop)
        
        # Speed control
        self._add_speed_control(layout)
        
        # Dataset selector
        self._add_dataset_selector(layout)
        
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
        Build the plot visualization section.
        
        Returns:
            Layout containing plots
        """
        layout = QtWidgets.QVBoxLayout()
        
        # GaitRite plot
        self.gaitrite_plot = pg.PlotWidget(title='GaitRite - Footprints and Trajectory')
        self._configure_gaitrite_plot()
        layout.addWidget(self.gaitrite_plot, 2)
        
        # CSV index label
        self.csv_index_label = QtWidgets.QLabel('CSV: - / -')
        layout.addWidget(self.csv_index_label, 0)
        
        # CSV data plot
        self.time_axis = TimeAxis(orientation='bottom')
        self.plot_widget = pg.PlotWidget(
            axisItems={'bottom': self.time_axis}, 
            title='Pressure Sensor Data (4 groups)'
        )
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.addLegend(offset=(10, 10))
        layout.addWidget(self.plot_widget, 1)
        
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
            self.video_controller.is_playing = False
            self.video_controller.timer.stop()
            self.btn_play.setText('▶ Play')
        else:
            self.video_controller.is_playing = True
            interval = self.video_controller.get_timer_interval()
            self.video_controller.timer.start(interval)
            self.btn_play.setText('⏸ Pause')
    
    def stop(self):
        """Stop playback and reset to beginning."""
        self.video_controller.reset()
        self.video_controller.timer.stop()
        self.btn_play.setText('▶ Play')
        self.progress_slider.setValue(0)
        self.update_time_label()
        if self.video_controller.video_cap:
            self.show_frame()
    
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
        Set playback speed.
        
        Args:
            rate: Playback rate multiplier
        """
        self.video_controller.set_playback_rate(rate)
        if self.video_controller.is_playing:
            interval = self.video_controller.get_timer_interval()
            self.video_controller.timer.start(interval)
    
    def _on_timer(self):
        """Handle timer tick for video playback."""
        ret, frame = self.video_controller.advance_frame()
        
        if not ret:
            self.video_controller.is_playing = False
            self.video_controller.timer.stop()
            self.btn_play.setText('▶ Play')
            return
        
        self._display_frame(frame)
        self._update_csv_cursor_from_video()
        self.progress_slider.setValue(self.video_controller.current_frame)
        self.update_time_label()
        
        if self.video_controller.current_frame >= self.video_controller.total_frames - 1:
            self.video_controller.is_playing = False
            self.video_controller.timer.stop()
            self.btn_play.setText('▶ Play')
    
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
            
            # Calculate scale to maintain aspect ratio
            scale = min(target_w / float(w0), target_h / float(h0))
            new_w = max(1, int(round(w0 * scale)))
            new_h = max(1, int(round(h0 * scale)))
            
            if new_w != w0 or new_h != h0:
                resized = cv2.resize(frame_bgr, (new_w, new_h), 
                                    interpolation=cv2.INTER_LINEAR)
            else:
                resized = frame_bgr
            
            frame_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            h, w = frame_rgb.shape[:2]
            bytes_per_line = 3 * w
            image = QtGui.QImage(frame_rgb.data, w, h, bytes_per_line, 
                                QtGui.QImage.Format_RGB888)
            pix = QtGui.QPixmap.fromImage(image)
            self.video_label.setPixmap(pix)
        except Exception:
            # Fallback
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            h, w = frame_rgb.shape[:2]
            bytes_per_line = 3 * w
            image = QtGui.QImage(frame_rgb.data, w, h, bytes_per_line, 
                                QtGui.QImage.Format_RGB888)
            pix = QtGui.QPixmap.fromImage(image).scaled(
                self.video_label.width(), 
                self.video_label.height(), 
                QtCore.Qt.KeepAspectRatio
            )
            self.video_label.setPixmap(pix)
    
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
        
        # Find L.csv
        csv_L = None
        for p in self.csv_paths:
            if os.path.exists(p):
                csv_L = p
                break
        
        if not csv_L:
            self.plot_widget.clear()
            self.plot_widget.plot([0], [0], pen=pg.mkPen('k'))
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
        )
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
    
    # ==================== CSV Cursor Synchronization ====================
    
    def _update_csv_cursor_from_video(self):
        """Update CSV plot cursor based on current video frame."""
        if self.data_manager.sums_L is None:
            return
        
        csv_idx = self.data_manager.video_frame_to_csv_index(
            self.video_controller.current_frame,
            self.video_controller.fps
        )
        
        csv_time = float(csv_idx) / float(self.data_manager.csv_sampling_rate) \
            if self.data_manager.csv_sampling_rate > 0 else float(csv_idx)
        
        # Update cursor position (vertical yellow line)
        self.plot_manager.update_cursor_position(
            csv_time,
            self.data_manager.sums_L,
            self.data_manager.sums_R,
            csv_idx
        )
        
        # Update markers and connecting segment (CRITICAL - was missing!)
        x_data = self.data_manager.get_time_axis()
        self.plot_manager.update_markers(
            csv_idx,
            x_data,
            self.data_manager.sums_L,
            self.data_manager.sums_R
        )
        
        # Update label
        total_idx = self.data_manager.csv_len - 1 if self.data_manager.csv_len > 0 else 0
        time_str = format_time_mmss(csv_time)
        self.csv_index_label.setText(
            f'CSV idx: {csv_idx} / {total_idx}   t={time_str}'
        )
    
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
        """Populate session combo box for selected category."""
        try:
            self.combo_session.clear()
            self.combo_session.setEnabled(False)
            
            if not group_path or not os.path.isdir(group_path):
                return
            
            subs = [d for d in os.listdir(group_path) 
                   if os.path.isdir(os.path.join(group_path, d))]

            # Sort sessions numerically when possible (e.g., '1', '2', '10')
            def _sess_key(name: str):
                # exact numeric name
                m = re.match(r'^0*([0-9]+)$', name)
                if m:
                    try:
                        return (int(m.group(1)), name)
                    except Exception:
                        pass
                # fallback: first number found inside name
                m2 = re.search(r'(\d+)', name)
                if m2:
                    try:
                        return (int(m2.group(1)), name)
                    except Exception:
                        pass
                return (10**9, name)

            subs.sort(key=_sess_key)
            
            self.combo_session.addItem('Select session...', userData=None)
            
            if subs:
                for s in subs:
                    self.combo_session.addItem(s, userData=os.path.join(group_path, s))
            else:
                self.combo_session.addItem(os.path.basename(group_path), userData=group_path)
            
            self.combo_session.setCurrentIndex(0)
            self.combo_session.setEnabled(True)
        except Exception:
            pass
    
    def on_load_dataset_clicked(self):
        """Handle Load Dataset button click."""
        try:
            subj_idx = self.combo_subject.currentIndex()
            if subj_idx < 0:
                QtWidgets.QMessageBox.information(self, 'Info', 
                                                 'Please select a subject first')
                return
            
            sess_idx = self.combo_session.currentIndex()
            sess_path = self.combo_session.itemData(sess_idx) if sess_idx >= 0 else None
            
            grp_idx = self.combo_group.currentIndex()
            grp_path = self.combo_group.itemData(grp_idx) if grp_idx >= 0 else None
            
            subj_path = self.combo_subject.itemData(subj_idx)
            
            # Determine target path
            target = sess_path or grp_path or subj_path
            
            if not target or not os.path.isdir(target):
                QtWidgets.QMessageBox.warning(self, 'Warning', 
                                             f'Invalid path: {target}')
                return
            
            # Load dataset
            self.configure_dataset_from_path(target)
            
            # Reset playback
            self.stop()
            
            self.statusBar().showMessage(f'Loaded dataset: {target}', 5000)
        except Exception as e:
            print(f"[VideoPlayer] Error loading dataset: {e}", flush=True)
    
    def configure_dataset_from_path(self, path: str):
        """
        Configure and load dataset from a directory.
        
        Args:
            path: Path to dataset directory
        """
        print(f"[VideoPlayer] Configuring dataset from: {path}", flush=True)
        
        # Find video file
        video_found = find_video_file(path)
        if video_found:
            self.embedded_video_path = video_found
            self.load_video(video_found)
        else:
            print(f"[VideoPlayer] No video found in {path}", flush=True)
            self.statusBar().showMessage('No video found in selected dataset', 5000)
        
        # Find CSV files
        csv_L = find_csv_file(path, 'L.csv')
        if csv_L:
            self.csv_paths = [csv_L]
        else:
            self.csv_paths = []
        
        # Load data
        if self.csv_paths:
            self.load_csvs()
        
        self.load_gaitrite_data()
    
    # ==================== Event Handlers ====================
    
    def closeEvent(self, event):
        """Handle window close event."""
        print("[VideoPlayer] Closing", flush=True)
        self.stop()
        self.video_controller.release()
        event.accept()
