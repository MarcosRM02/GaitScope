import sys
import time
from PySide6 import QtCore, QtGui, QtWidgets
import numpy as np
import cv2
from animator import Animator


class Worker(QtCore.QObject):
    tick = QtCore.Signal()
    fpsReport = QtCore.Signal(float)

    def __init__(self, fps=64):
        super().__init__()
        self._running = True
        self._playing = False
        self.fps = fps

    @QtCore.Slot()
    def run(self):
        # fixed-period loop to maintain precise frame rate and correct drift
        period = 1.0 / float(self.fps)
        next_time = time.perf_counter()
        last_report = next_time
        frames = 0
        while self._running:
            now = time.perf_counter()
            if self._playing:
                # emit tick exactly on schedule
                self.tick.emit()
                frames += 1
            # schedule next wake
            next_time += period
            # compute remaining time until next_time
            sleep_time = next_time - time.perf_counter()
            if sleep_time > 0:
                # sleep most of the interval
                time.sleep(sleep_time)
            else:
                # we're behind schedule; catch up by resetting next_time
                next_time = time.perf_counter()
            # report fps every 1 second
            if (time.perf_counter() - last_report) >= 1.0:
                elapsed = time.perf_counter() - last_report
                report_fps = frames / elapsed if elapsed > 0 else 0.0
                self.fpsReport.emit(report_fps)
                last_report = time.perf_counter()
                frames = 0

    def stop(self):
        self._running = False

    def play(self, p: bool):
        self._playing = p


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, animator: Animator):
        super().__init__()
        self.animator = animator
        self.setWindowTitle("Heatmap Viewer")
        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.setCentralWidget(self.image_label)
        # controls
        w = QtWidgets.QWidget()
        hbox = QtWidgets.QHBoxLayout()
        self.play_btn = QtWidgets.QPushButton("Play")
        self.reset_btn = QtWidgets.QPushButton("Reset")
        self.prev_btn = QtWidgets.QPushButton("Prev")
        self.next_btn = QtWidgets.QPushButton("Next")
        self.frame_label = QtWidgets.QLabel("0/0")
        hbox.addWidget(self.play_btn)
        hbox.addWidget(self.reset_btn)
        hbox.addWidget(self.prev_btn)
        hbox.addWidget(self.next_btn)
        hbox.addWidget(self.frame_label)
        w.setLayout(hbox)
        toolbar = QtWidgets.QToolBar()
        self.addToolBar(QtCore.Qt.BottomToolBarArea, toolbar)
        toolbar.addWidget(w)
        # worker thread
        self.thread = QtCore.QThread()
        self.worker = Worker(fps=animator.params['fps'])
        self.worker.moveToThread(self.thread)
        self.worker.tick.connect(self.on_tick)
        self.worker.fpsReport.connect(self.on_fps)
        self.thread.started.connect(self.worker.run)
        self.thread.start()
        # connect buttons
        self.play_btn.clicked.connect(self.toggle_play)
        self.reset_btn.clicked.connect(self.on_reset)
        self.prev_btn.clicked.connect(self.on_prev)
        self.next_btn.clicked.connect(self.on_next)
        # keyboard shortcuts
        # Use QAction shortcuts (robust across PySide6 variations)
        a_space = QtGui.QAction(self)
        a_space.setShortcut(QtGui.QKeySequence("Space"))
        a_space.triggered.connect(self.toggle_play)
        self.addAction(a_space)

        a_r = QtGui.QAction(self)
        a_r.setShortcut(QtGui.QKeySequence("R"))
        a_r.triggered.connect(self.on_reset)
        self.addAction(a_r)

        a_right = QtGui.QAction(self)
        a_right.setShortcut(QtGui.QKeySequence("Right"))
        a_right.triggered.connect(self.on_next)
        self.addAction(a_right)

        a_left = QtGui.QAction(self)
        a_left.setShortcut(QtGui.QKeySequence("Left"))
        a_left.triggered.connect(self.on_prev)
        self.addAction(a_left)

        self.update_image()

    @QtCore.Slot()
    def on_tick(self):
        self.animator.step(1)
        self.update_image()

    @QtCore.Slot(float)
    def on_fps(self, v):
        self.setWindowTitle(f"Heatmap Viewer - {v:.1f} FPS")

    def update_image(self):
        img = self.animator.get_frame()
        h, w, ch = img.shape
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        qimg = QtGui.QImage(rgb.data, w, h, 3*w, QtGui.QImage.Format_RGB888)
        pix = QtGui.QPixmap.fromImage(qimg)
        self.image_label.setPixmap(pix)
        self.frame_label.setText(f"{self.animator.frame_idx+1}/{self.animator.n_frames()}")

    def toggle_play(self):
        playing = not self.worker._playing
        self.worker.play(playing)
        self.play_btn.setText("Pause" if playing else "Play")

    def on_reset(self):
        self.worker.play(False)
        self.play_btn.setText("Play")
        self.animator.reset()
        self.update_image()

    def on_prev(self):
        self.worker.play(False)
        self.play_btn.setText("Play")
        self.animator.step(-1)
        self.update_image()

    def on_next(self):
        self.worker.play(False)
        self.play_btn.setText("Play")
        self.animator.step(1)
        self.update_image()

    def closeEvent(self, event):
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()
        event.accept()
