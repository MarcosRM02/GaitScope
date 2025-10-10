import sys
import time
from PySide6 import QtCore, QtGui, QtWidgets
import numpy as np
import cv2
from animator import Animator
from worker import Worker
from prerenderer import PreRenderer


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, animator: Animator):
        super().__init__()
        self.animator = animator
        self.setWindowTitle("Heatmap Viewer")
        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.setCentralWidget(self.image_label)
        # Fix the image area to the final composition size so the window doesn't
        # re-layout while the first frames/warm-up are rendered.
        try:
            w = int(self.animator.params.get('wFinal', 175))
            h = int(self.animator.params.get('hFinal', 520))
            margin = int(self.animator.params.get('margin', 50))
            legendW = int(self.animator.params.get('legendWidth', 80))
            final_w = w * 2 + margin * 3 + legendW
            final_h = h + margin * 2
            # fix the QLabel pixel area to avoid size changes
            self.image_label.setFixedSize(final_w, final_h)
            self.image_label.setScaledContents(False)
            # prevent the main window from shrinking smaller than content
            self.setMinimumSize(self.sizeHint())
        except Exception:
            pass
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
        # playback speed control
        self.speed_label = QtWidgets.QLabel(f"{int(self.animator.params.get('fps',64))} FPS")
        self.speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(120)
        self.speed_slider.setValue(int(self.animator.params.get('fps',64)))
        self.speed_slider.setFixedWidth(140)
        self.speed_slider.valueChanged.connect(self.set_playback_speed)
        hbox.addWidget(self.speed_label)
        hbox.addWidget(self.speed_slider)
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

    def set_playback_speed(self, v: int):
        # Called in GUI thread; update worker.fps (safe simple assignment) and animator params
        try:
            val = int(v)
        except Exception:
            return
        self.worker.fps = val
        self.animator.params['fps'] = val
        self.speed_label.setText(f"{val} FPS")

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
