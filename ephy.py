#!/usr/bin/env python3
"""
Reproductor de Video Simple con Interfaz Gráfica
Usa PyQt5 para la interfaz, OpenCV para la reproducción y pyqtgraph para los plots
"""

import sys

import os
import time
import threading
# Intentar forzar la ruta de plugins Qt de PyQt5 antes de importar OpenCV para evitar conflictos con los plugins que trae cv2
try:
    import PyQt5
    _pyqt_plugins = os.path.join(os.path.dirname(PyQt5.__file__), 'Qt', 'plugins', 'platforms')
    if os.path.isdir(_pyqt_plugins):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = _pyqt_plugins
except Exception:
    pass

import cv2
import numpy as np
import pandas as pd

from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

# Slider que responde a clicks en la barra saltando inmediatamente a la posición clicada
class ClickableSlider(QtWidgets.QSlider):
    def mousePressEvent(self, ev):
        try:
            # calcular valor en función de la posición del click (soporta Horizontal y Vertical)
            if self.orientation() == QtCore.Qt.Horizontal:
                x = ev.pos().x()
                w = max(1, self.width())
                ratio = float(x) / float(w)
                ratio = max(0.0, min(1.0, ratio))
                mn = int(self.minimum())
                mx = int(self.maximum())
                val = int(round(mn + ratio * (mx - mn)))
                # actualizar valor y emitir señal de final de arrastre para disparar seek
                self.setValue(val)
                try:
                    self.sliderReleased.emit()
                except Exception:
                    pass
            else:
                y = ev.pos().y()
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
        # llamar al comportamiento por defecto para mantener interacción normal
        super().mousePressEvent(ev)

# GaitRite constants (cm)
CARPET_WIDTH_CM = 61
CARPET_LENGTH_CM = 488
CARPET_RATIO = CARPET_WIDTH_CM / float(CARPET_LENGTH_CM)  # ancho/alto

# Silence module prints (remove logging output from this module)
try:
    # override the module-level print symbol to a no-op so existing print(...) calls are silent
    print = lambda *a, **k: None
except Exception:
    pass

# Custom axis to format seconds as MM:SS
class TimeAxis(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        # values: list of tick positions in seconds
        out = []
        for v in values:
            try:
                if v is None or not np.isfinite(v):
                    out.append('')
                    continue
                secs = float(v)
                mins = int(secs // 60)
                s = int(secs % 60)
                out.append(f"{mins:02d}:{s:02d}")
            except Exception:
                out.append('')
        return out


class VideoPlayer(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # tasa de muestreo de los datos (Hz)
        self.csv_sampling_rate = 64.0
        # almacenamiento de sums por grupo (se llenará en load_csvs)
        self.sums_L = None
        self.sums_R = None
        self.csv_len = 0
        # cursor vertical para sincronización en el plot
        self.cursor_line = None
        # segment connecting L and R marker positions at current time (drawn as a single line)
        #        self.cursor_segment = None
        # We'll draw the segment as a QGraphicsLineItem in scene coordinates so it stays above plot curves
        self.cursor_segment = None
        self.cursor_qline = None
        # etiqueta que muestra índice de CSV
        self.csv_index_label = None
        # plot items for live update
        self.plot_items_L = []
        self.plot_items_R = []
        # moving markers for current position (visible on plots)
        self.scatter_L = None
        self.scatter_R = None
        # which group to show markers for (one per CSV side) to minimize computation
        self.marker_group_index_L = 0
        self.marker_group_index_R = 0
        # stored R offset used when plotting R series
        self.r_offset = 30000.0
        # window (seconds) for live-scrolling view
        self.plot_window_seconds = 5.0
        # Desactivar autoscroll para evitar animación de seguimiento
        self.autoscroll = False
        self.setWindowTitle("Reproductor de Video - PyQt")
        self.resize(1100, 800)

        # Variables del reproductor
        self.video_cap = None
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30.0
        self.video_path = None
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._on_timer)
        self._last_frame_img = None

        # Variables para seeking durante arrastre
        self._dragging = False
        self._last_drag_seek_time = 0.0
        self._drag_seek_interval = 1.0 / 10.0  # máximo 10 seeks por segundo mientras se arrastra
        self._fast_seek_lock = False

        # Playback speed control (multiplier, 1.0 == real-time)
        self.playback_rate = 1.0
        # allow very slow playback speeds (down to 0.01x)
        self._speed_options = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 1.5, 2.0]
        self.speed_label = None
        self.cmb_speed = None

        # Throttle para actualizaciones pesadas de plot (evita 'lag' al reproducir)
        self._last_plot_update = 0.0
        self._plot_update_interval = 1.0 / 20.0  # actualizar marcadores a 20 Hz por defecto

        # Rutas embebidas
        base_dir = os.path.abspath(os.path.dirname(__file__))
        # No cargar recursos embebidos por defecto; se cargarán mediante selector
        self.embedded_video_path = ''
        self.csv_paths = []

        # Instrumentación diagnóstica (removed)
#         self._diag_enabled = True
#         self._diag_start_time = time.time()
#         self._diag_frame_count = 0
#         self._diag_total_proc_time = 0.0
#         self._diag_max_proc_time = 0.0
#         self._diag_slow_frames = 0
#         self._diag_last_print = self._diag_start_time
#         self._diag_log_path = os.path.join(base_dir, 'diagnostics.csv')
#         try:
#             with open(self._diag_log_path, 'w') as _f:
#                 _f.write('timestamp,frame,proc_ms,interval_ms,csv_idx\n')
#         except Exception:
#             pass
        # Crear UI
        self._build_ui()

        print("[ephy] UI built, no embedded resources loaded at start", flush=True)
        # no automatic load of embedded resources at init
        print("[ephy] VideoPlayer.__init__ end", flush=True)

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        # Layout principal horizontal: video | plots
        main_layout = QtWidgets.QHBoxLayout(central)

        # Columna izquierda: video + controles
        left_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(left_layout, 2)

        # Label para video
        self.video_label = QtWidgets.QLabel()
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setAlignment(QtCore.Qt.AlignCenter)
        left_layout.addWidget(self.video_label, 8)

        # Controles
        controls_layout = QtWidgets.QHBoxLayout()
        left_layout.addLayout(controls_layout)

        # Open video button removed (embedded video used)

        self.btn_prev_frame = QtWidgets.QPushButton('◀ Frame')
        self.btn_prev_frame.clicked.connect(self.prev_frame)
        controls_layout.addWidget(self.btn_prev_frame)

        self.btn_play = QtWidgets.QPushButton('▶ Play')
        self.btn_play.clicked.connect(self.toggle_play_pause)
        controls_layout.addWidget(self.btn_play)

        self.btn_next_frame = QtWidgets.QPushButton('Frame ▶')
        self.btn_next_frame.clicked.connect(self.next_frame)
        controls_layout.addWidget(self.btn_next_frame)

        self.btn_stop = QtWidgets.QPushButton(' Reset')
        self.btn_stop.clicked.connect(self.stop)
        controls_layout.addWidget(self.btn_stop)

        # Speed control (ComboBox)
        try:
            self.speed_label = QtWidgets.QLabel('Velocidad:')
            controls_layout.addWidget(self.speed_label)
            self.cmb_speed = QtWidgets.QComboBox()
            # labels must match self._speed_options order
            labels = ('0.01x', '0.05x', '0.10x', '0.25x', '0.50x', '1.00x', '1.50x', '2.00x')
            for lbl in labels:
                self.cmb_speed.addItem(lbl)
            # default to 1.0x (index where 1.0 appears)
            try:
                default_idx = self._speed_options.index(1.0)
            except ValueError:
                default_idx = 0
            self.cmb_speed.setCurrentIndex(default_idx)
            self.cmb_speed.currentIndexChanged.connect(lambda i: self.set_playback_rate(self._speed_options[int(i)]))
            controls_layout.addWidget(self.cmb_speed)
        except Exception:
            pass

        # Dataset selector (replaced): cascade de desplegables Subject -> Group -> Session + botón Load
        try:
            controls_layout.addWidget(QtWidgets.QLabel('Subject:'))
            self.combo_subject = QtWidgets.QComboBox()
            self.combo_subject.setToolTip('Selecciona carpeta P (ej. P1, P2) dentro de data/')
            controls_layout.addWidget(self.combo_subject)

            controls_layout.addWidget(QtWidgets.QLabel('Category:'))
            self.combo_group = QtWidgets.QComboBox()
            self.combo_group.setToolTip('Selecciona subcarpeta (FP, NP, SP, etc.)')
            self.combo_group.setEnabled(False)
            controls_layout.addWidget(self.combo_group)

            controls_layout.addWidget(QtWidgets.QLabel('Session:'))
            self.combo_session = QtWidgets.QComboBox()
            self.combo_session.setToolTip('Selecciona sesión (ej. 1, 2, ...)')
            self.combo_session.setEnabled(False)
            controls_layout.addWidget(self.combo_session)

            self.btn_load_dataset = QtWidgets.QPushButton('Load Dataset')
            self.btn_load_dataset.clicked.connect(self.on_load_dataset_clicked)
            self.btn_load_dataset.setEnabled(False)
            controls_layout.addWidget(self.btn_load_dataset)

            # poblar subjects desde data/
            try:
                self.populate_subjects()
            except Exception:
                pass

            # conectar señales para poblar siguientes niveles cuando cambie selección
            try:
                self.combo_subject.currentIndexChanged.connect(self.on_subject_changed)
                self.combo_group.currentIndexChanged.connect(self.on_group_changed)
            except Exception:
                pass
        except Exception:
            pass

        # Slider de progreso y etiquetas
        progress_layout = QtWidgets.QHBoxLayout()
        left_layout.addLayout(progress_layout)

        self.progress_slider = ClickableSlider(QtCore.Qt.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(0)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        # allow continuous seek while dragging
        try:
            self.progress_slider.sliderMoved.connect(self.on_slider_moved)
            self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        except Exception:
            pass
        progress_layout.addWidget(self.progress_slider, 8)

        self.time_label = QtWidgets.QLabel('00:00 / 00:00')
        progress_layout.addWidget(self.time_label, 1)

        self.frame_label = QtWidgets.QLabel('Frame: 0 / 0')
        progress_layout.addWidget(self.frame_label, 1)

        # Columna derecha: plots (pyqtgraph)
        right_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(right_layout, 3)

        # Un único plot que contendrá 4 líneas (una por grupo de 8 columnas)
        # use TimeAxis on bottom for visible mm:ss ticks
        self.time_axis = TimeAxis(orientation='bottom')
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': self.time_axis}, title='Sumatorio por grupos (4 líneas)')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.addLegend(offset=(10, 10))
        # etiqueta para índice csv (se añadirá entre vistas)
        self.csv_index_label = QtWidgets.QLabel('CSV: - / -')

        # --- Nuevo: GaitRite-style plot integrado; colocamos primero GaitRite arriba y luego las series ---
        try:
            self.gaitrite_plot = pg.PlotWidget(title='GaitRite - Huellas y Trayectoria')
            # keep gaitrite plot opaque and non-interactive in terms of mouse (but visible below)
            try:
                self.gaitrite_plot.setBackground('white')
            except Exception:
                pass
            try:
                self.gaitrite_plot.setMouseEnabled(x=False, y=False)
                self.gaitrite_plot.setMenuEnabled(False)
                try:
                    self.gaitrite_plot.hideButtons()
                except Exception:
                    pass
            except Exception:
                pass

            self.gaitrite_plot.setMinimumSize(400, 300)
            plot_item_gr = self.gaitrite_plot.getPlotItem()
            try:
                plot_item_gr.setLabel('left', 'Longitud (cm)', **{'color': '#2c3e50', 'font-size': '10pt'})
                plot_item_gr.setLabel('bottom', 'Ancho (cm)', **{'color': '#2c3e50', 'font-size': '10pt'})
            except Exception:
                pass
            plot_item_gr.showGrid(True, True, alpha=0.3)

            # Añadir gaitrite_plot primero (arriba)
            right_layout.addWidget(self.gaitrite_plot, 2)

            # añadir etiqueta CSV
            right_layout.addWidget(self.csv_index_label, 0)

            # Añadir el plot de series debajo
            right_layout.addWidget(self.plot_widget, 1)

            # inicializar vacío
            self.show_empty_gaitrite()
        except Exception:
            pass

        # Shortcuts
        QtWidgets.QShortcut(QtGui.QKeySequence('Space'), self, activated=self.toggle_play_pause)
        QtWidgets.QShortcut(QtGui.QKeySequence('Left'), self, activated=self.prev_frame)
        QtWidgets.QShortcut(QtGui.QKeySequence('Right'), self, activated=self.next_frame)
        # Ctrl+Left / Ctrl+Right shortcuts removed (no ±5s jump)
        print("[ephy] UI constructed", flush=True)

    # ------------------------- Video control ---------------------------------
    # open_file removed: app uses embedded video only

    def load_video(self, path):
        print(f"[ephy] load_video: {path}", flush=True)
        if self.is_playing:
            self.stop()

        if self.video_cap:
            self.video_cap.release()

        self.video_path = path
        self.video_cap = cv2.VideoCapture(path)
        if not self.video_cap.isOpened():
            QtWidgets.QMessageBox.critical(self, 'Error', 'No se pudo abrir el video')
            print(f"[ephy] load_video: failed to open {path}", flush=True)
            return

        self.total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = float(self.video_cap.get(cv2.CAP_PROP_FPS)) or 30.0
        self.current_frame = 0

        self.progress_slider.setMaximum(max(0, self.total_frames - 1))
        self.update_time_label()
        self.show_frame()
        print(f"[ephy] load_video: opened {path}, frames={self.total_frames}, fps={self.fps}", flush=True)

    def toggle_play_pause(self):
        if not self.video_cap:
            return
        if self.is_playing:
            self.is_playing = False
            self.timer.stop()
            self.btn_play.setText('▶ Play')
        else:
            self.is_playing = True
            # Compute timer interval according to file fps and playback rate multiplier
            try:
                if self.fps > 0 and self.playback_rate > 0:
                    interval = int(max(1, 1000.0 / (self.fps * float(self.playback_rate))))
                else:
                    interval = int(max(1, 33))
            except Exception:
                interval = int(1000.0 / self.fps) if self.fps > 0 else 33
            self.timer.start(interval)
            self.btn_play.setText('⏸ Pause')

    def _on_timer(self):
        # Avanzar un frame (con instrumentación de tiempos)
        if not self.video_cap:
            return

        now_timer = time.time()
        interval_ms = 0.0
        if hasattr(self, '_last_timer_time'):
            interval_ms = (now_timer - self._last_timer_time) * 1000.0
        self._last_timer_time = now_timer

        t0 = time.time()
        ret, frame = self.video_cap.read()
        t1 = time.time()
        proc_ms = (t1 - t0) * 1000.0

        if not ret:
            self.is_playing = False
            self.timer.stop()
            self.btn_play.setText('▶ Play')
            return

        # actualizar contadores diagnósticos
        # if self._diag_enabled:
        #     self._diag_frame_count += 1
        #     self._diag_total_proc_time += proc_ms
        #     if proc_ms > self._diag_max_proc_time:
        #         self._diag_max_proc_time = proc_ms
        #     expected_ms = (1000.0 / self.fps) if self.fps > 0 else 33.3
        #     if proc_ms > expected_ms:
        #         self._diag_slow_frames += 1

        # actualizar frame y UI
        self.current_frame += 1
        self._display_frame(frame)
        # actualizar cursor CSV sincronizado
        self._update_csv_cursor_from_video()
        self.progress_slider.setValue(self.current_frame)
        self.update_time_label()

        # imprimir / guardar resumen periódico cada 5 segundos
        # if self._diag_enabled:
        #     now = time.time()
        #     if (now - self._diag_last_print) >= 5.0:
        #         avg = (self._diag_total_proc_time / self._diag_frame_count) if self._diag_frame_count else 0.0
        #         msg = (f"[ephy][DIAG] frames={self._diag_frame_count} avg_proc_ms={avg:.2f} "
        #                f"max_proc_ms={self._diag_max_proc_time:.2f} slow_frames={self._diag_slow_frames}")
        #         print(msg, flush=True)
        #         # append summary to diagnostics.csv
        #         try:
        #             with open(self._diag_log_path, 'a') as f:
        #                 f.write(f"{now},{self._diag_frame_count},{avg:.3f},{self._diag_max_proc_time:.3f},{self._diag_slow_frames}\n")
        #         except Exception:
        #             pass
        #         # reset counters for next interval
        #         self._diag_frame_count = 0
        #         self._diag_total_proc_time = 0.0
        #         self._diag_max_proc_time = 0.0
        #         self._diag_slow_frames = 0
        #         self._diag_last_print = now

        if self.current_frame >= self.total_frames - 1:
            self.is_playing = False
            self.timer.stop()
            self.btn_play.setText('▶ Play')

    def show_frame(self):
        if not self.video_cap:
            return
        # Posicionar y leer
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.video_cap.read()
        if ret:
            self._display_frame(frame)
            # actualizar cursor CSV sincronizado cuando mostramos un frame manualmente
            self._update_csv_cursor_from_video()

    def _display_frame(self, frame_bgr):
        # Convertir a RGB y mostrar en QLabel
        # Redimensionar el frame con OpenCV al tamaño del QLabel manteniendo aspecto para reducir coste
        try:
            h0, w0 = frame_bgr.shape[:2]
            target_w = max(1, self.video_label.width())
            target_h = max(1, self.video_label.height())
            # calcular factor de escala manteniendo aspecto
            scale = min(target_w / float(w0), target_h / float(h0))
            new_w = max(1, int(round(w0 * scale)))
            new_h = max(1, int(round(h0 * scale)))
            if new_w != w0 or new_h != h0:
                resized = cv2.resize(frame_bgr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            else:
                resized = frame_bgr
            frame_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            h, w = frame_rgb.shape[:2]
            bytes_per_line = 3 * w
            image = QtGui.QImage(frame_rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
            pix = QtGui.QPixmap.fromImage(image)
            # No escalar con Qt (ya lo hacemos con OpenCV)
            self.video_label.setPixmap(pix)
        except Exception:
            # Fallback simple si algo sale mal
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            h, w = frame_rgb.shape[:2]
            bytes_per_line = 3 * w
            image = QtGui.QImage(frame_rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
            pix = QtGui.QPixmap.fromImage(image).scaled(self.video_label.width(), self.video_label.height(), QtCore.Qt.KeepAspectRatio)
            self.video_label.setPixmap(pix)

        # Guardar último frame BGR para export
        self._last_frame_img = frame_bgr.copy()
        # debug
        # print frame info occasionally
        # print(f"[ephy] displayed frame {self.current_frame}", flush=True)

    def stop(self):
        self.is_playing = False
        self.timer.stop()
        self.current_frame = 0
        if self.video_cap:
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.show_frame()
        self.btn_play.setText('▶ Play')
        self.progress_slider.setValue(0)
        self.update_time_label()

    def next_frame(self):
        if not self.video_cap:
            return
        if self.is_playing:
            self.toggle_play_pause()
        new_frame = min(self.current_frame + 1, self.total_frames - 1)
        self.seek_to_frame(new_frame)

    def prev_frame(self):
        if not self.video_cap:
            return
        if self.is_playing:
            self.toggle_play_pause()
        new_frame = max(self.current_frame - 1, 0)
        self.seek_to_frame(new_frame)

    def seek_to_frame(self, frame_number):
        """Seek safely to a frame without blocking the UI or allowing re-entrant seeks.
        This clamps the requested frame, sets a _seeking flag to ignore concurrent requests,
        protects VideoCapture calls, and briefly disables playback controls for UX stability.
        """
        if not self.video_cap or not getattr(self.video_cap, 'isOpened', lambda: False)():
            return
        # ignore re-entrant seeks
        if getattr(self, '_seeking', False):
            return
        self._seeking = True
        # optionally disable controls to avoid spamming seeks
        disabled_buttons = []
        try:
            try:
                for name in ('btn_play','btn_next_frame','btn_prev_frame','btn_forward','btn_backward','btn_stop','btn_open'):
                    btn = getattr(self, name, None)
                    if btn is not None:
                        btn.setEnabled(False)
                        disabled_buttons.append(btn)
            except Exception:
                pass

            # Clamp safely the requested frame index
            try:
                frame_number = max(0, min(int(frame_number), max(0, int(self.total_frames) - 1)))
            except Exception:
                frame_number = max(0, int(frame_number))

            self.current_frame = int(frame_number)

            # Seek and read protected by try/except because some containers/codecs may error on rapid seeks
            try:
                self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                ret, frame = self.video_cap.read()
            except Exception as e:
                print(f"[ephy] seek_to_frame: video read error: {e}", flush=True)
                ret = False
                frame = None

            if ret and frame is not None:
                try:
                    self._display_frame(frame)
                except Exception as e:
                    print(f"[ephy] seek_to_frame: display error: {e}", flush=True)
            else:
                # if read failed, log and continue (keep previous frame if any)
                print(f"[ephy] seek_to_frame: read returned False for frame {self.current_frame}", flush=True)
        finally:
            # always re-enable controls and update UI state
            try:
                for b in disabled_buttons:
                    try:
                        b.setEnabled(True)
                    except Exception:
                        pass
            except Exception:
                pass

            # Ensure UI reflects the (possibly unchanged) current_frame
            try:
                self.progress_slider.setValue(self.current_frame)
            except Exception:
                pass
            try:
                self.update_time_label()
            except Exception:
                pass
            # Update cursor to reflect new position (guarded)
            try:
                self._update_csv_cursor_from_video()
            except Exception:
                pass
            # clear seeking flag
            self._seeking = False

    def _video_frame_to_csv_index(self, video_frame: int) -> int:
        """Mapea un frame de video a un índice de muestra CSV según las tasas (tiempo absoluto)."""
        if self.fps <= 0 or self.csv_sampling_rate <= 0:
            return 0
        t = float(video_frame) / float(self.fps)
        idx = int(round(t * float(self.csv_sampling_rate)))
        if self.csv_len:
            idx = max(0, min(idx, self.csv_len - 1))
        else:
            idx = max(0, idx)
        return idx

    def _update_csv_cursor_from_video(self):
        """Actualiza la posición del cursor vertical en el plot según el frame de video actual."""
        if self.sums_L is None:
            return
        csv_idx = self._video_frame_to_csv_index(self.current_frame)
        # convert index to time (seconds)
        csv_time = float(csv_idx) / float(self.csv_sampling_rate) if self.csv_sampling_rate > 0 else float(csv_idx)

        # posicionar línea vertical en valor csv_time (eje X en segundos)
        if self.cursor_line is None:
            # use same bright color as connecting segment and make it thicker
            try:
                pen_line = pg.mkPen(color=(255, 200, 0), width=2)
            except Exception:
                pen_line = pg.mkPen('y', width=2)
            self.cursor_line = pg.InfiniteLine(pos=csv_time, angle=90, pen=pen_line)
            try:
                vb = self.plot_widget.getViewBox()
                vb.addItem(self.cursor_line)
            except Exception:
                self.plot_widget.addItem(self.cursor_line)
            try:
                self.cursor_line.setZValue(10**6)
            except Exception:
                pass
        else:
            try:
                self.cursor_line.setPos(csv_time)
            except Exception:
                pass

        # Autoscroll desactivado: no modificamos el rango X automáticamente para evitar "animación" en las gráficas.
        # Si se desea reactivar, habilitar self.autoscroll y restaurar la lógica anterior.

        # actualizar etiqueta con índice y tiempo (formato mm:ss)
        total_idx = self.csv_len - 1 if self.csv_len > 0 else 0
        # Mostrar tiempo en mm:ss para legibilidad
        time_str = self.format_time(csv_time)
        self.csv_index_label.setText(f'CSV idx: {csv_idx} / {total_idx}   t={time_str}')

        # Update moving markers (scatter points) so user clearly sees where the video is
        try:
            # Throttle expensive updates to avoid blocking la GUI. Mantener cursor_line actualizado siempre
            now = time.time()
            do_plot_update = (now - self._last_plot_update) >= float(self._plot_update_interval)

            idx = int(csv_idx)
            if self.sums_L is not None and len(self.sums_L) > 0:
                # Siempre calcular posicion simple para cursor label (rápido)
                if do_plot_update:
                    # Update just one marker per CSV side (configurable indices) to minimize per-frame compute
                    try:
                        # L side
                        giL = max(0, min(int(self.marker_group_index_L), len(self.sums_L) - 1))
                        arrL = self.sums_L[giL]
                        yL = float(arrL[idx]) if idx < arrL.shape[0] else float(arrL[-1])
                        self.scatter_L.setData(x=[csv_time], y=[yL])
                    except Exception:
                        pass

                    try:
                        # R side (apply stored offset so it lines up visually with plotted R shift)
                        if self.sums_R is not None and len(self.sums_R) > 0:
                            giR = max(0, min(int(self.marker_group_index_R), len(self.sums_R) - 1))
                            arrR = self.sums_R[giR]
                            yR = float(arrR[idx]) if idx < arrR.shape[0] else float(arrR[-1])
                            self.scatter_R.setData(x=[csv_time], y=[yR - float(self.r_offset)])
                    except Exception:
                        pass

                    # actualizar timestamp de última actualización pesada
                    self._last_plot_update = now
        except Exception:
            pass

        # Compute the two y positions (L and R) and draw a single vertical segment
        try:
            giL = max(0, min(int(self.marker_group_index_L), len(self.sums_L) - 1))
            arrL = self.sums_L[giL]
            yL = float(arrL[idx]) if idx < arrL.shape[0] else float(arrL[-1])
        except Exception:
            yL = 0.0

        try:
            if self.sums_R is not None and len(self.sums_R) > 0:
                giR = max(0, min(int(self.marker_group_index_R), len(self.sums_R) - 1))
                arrR = self.sums_R[giR]
                yR = float(arrR[idx]) if idx < arrR.shape[0] else float(arrR[-1])
                yR_shifted = yR - float(self.r_offset)
            else:
                yR_shifted = 0.0 - float(self.r_offset)
        except Exception:
            yR_shifted = 0.0 - float(self.r_offset)

        try:
            # update QGraphicsLineItem by mapping data coordinates to scene coordinates
            if self.cursor_qline is not None:
                try:
                    vb = self.plot_widget.getViewBox()
                    p1 = vb.mapViewToScene(QtCore.QPointF(csv_time, yR_shifted))
                    p2 = vb.mapViewToScene(QtCore.QPointF(csv_time, yL))
                    self.cursor_qline.setLine(p1.x(), p1.y(), p2.x(), p2.y())
                    # ensure it stays on top in case other items change
                    try:
                        scene = self.plot_widget.scene()
                        zs = [item.zValue() for item in scene.items()]
                        max_z = max(zs) if zs else 0
                        self.cursor_qline.setZValue(max_z + 100)
                    except Exception:
                        pass
                except Exception:
                    # fallback: try to set via PlotDataItem if available
                    if self.cursor_segment is not None:
                        self.cursor_segment.setData(x=[csv_time, csv_time], y=[yR_shifted, yL])
        except Exception:
            pass

        # Compute the two y positions (L and R) and draw a single vertical segment
        try:
            giL = max(0, min(int(self.marker_group_index_L), len(self.sums_L) - 1))
            arrL = self.sums_L[giL]
            yL = float(arrL[idx]) if idx < arrL.shape[0] else float(arrL[-1])
        except Exception:
            yL = 0.0

        try:
            if self.sums_R is not None and len(self.sums_R) > 0:
                giR = max(0, min(int(self.marker_group_index_R), len(self.sums_R) - 1))
                arrR = self.sums_R[giR]
                yR = float(arrR[idx]) if idx < arrR.shape[0] else float(arrR[-1])
                yR_shifted = yR - float(self.r_offset)
            else:
                yR_shifted = 0.0 - float(self.r_offset)
        except Exception:
            yR_shifted = 0.0 - float(self.r_offset)

        try:
            # update QGraphicsLineItem by mapping data coordinates to scene coordinates
            if self.cursor_qline is not None:
                try:
                    vb = self.plot_widget.getViewBox()
                    p1 = vb.mapViewToScene(QtCore.QPointF(csv_time, yR_shifted))
                    p2 = vb.mapViewToScene(QtCore.QPointF(csv_time, yL))
                    self.cursor_qline.setLine(p1.x(), p1.y(), p2.x(), p2.y())
                    # ensure it stays on top in case other items change
                    try:
                        scene = self.plot_widget.scene()
                        zs = [item.zValue() for item in scene.items()]
                        max_z = max(zs) if zs else 0
                        self.cursor_qline.setZValue(max_z + 100)
                    except Exception:
                        pass
                except Exception:
                    # fallback: try to set via PlotDataItem if available
                    if self.cursor_segment is not None:
                        self.cursor_segment.setData(x=[csv_time, csv_time], y=[yR_shifted, yL])
        except Exception:
            pass

    def update_time_label(self):
        if not self.video_cap or self.fps == 0:
            self.time_label.setText('00:00 / 00:00')
            self.frame_label.setText('Frame: 0 / 0')
            return
        current_seconds = self.current_frame / self.fps
        total_seconds = self.total_frames / self.fps
        self.time_label.setText(f"{self.format_time(current_seconds)} / {self.format_time(total_seconds)}")
        self.frame_label.setText(f"Frame: {self.current_frame} / {max(0, self.total_frames - 1)}")

    @staticmethod
    def format_time(seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def on_slider_released(self):
        try:
            val = self.progress_slider.value()
            # stop dragging state
            try:
                self._dragging = False
            except Exception:
                pass
            # perform a full safe seek (may disable controls briefly)
            self.seek_to_frame(val)
        except Exception:
            pass

    def on_slider_pressed(self):
        """Mark that user started dragging the slider."""
        try:
            self._dragging = True
        except Exception:
            pass

    def on_slider_moved(self, val):
        """Called frequently while user drags the slider. Do a throttled fast seek to update video display."""
        try:
            now = time.time()
            if (now - self._last_drag_seek_time) < float(self._drag_seek_interval):
                return
            self._last_drag_seek_time = now
            # perform a lightweight seek/display without disabling controls
            try:
                self.seek_to_frame_fast(int(val))
            except Exception:
                pass
        except Exception:
            pass

    def seek_to_frame_fast(self, frame_number):
        """Lightweight seek used during dragging: set CAP_PROP_POS_FRAMES, read and display frame.
        This avoids disabling UI controls and is tolerant to rapid calls.
        """
        if not self.video_cap or not getattr(self.video_cap, 'isOpened', lambda: False)():
            return
        # simple re-entrancy guard for fast seeks
        if getattr(self, '_fast_seek_lock', False):
            return
        self._fast_seek_lock = True
        try:
            try:
                frame_number = max(0, min(int(frame_number), max(0, int(self.total_frames) - 1)))
            except Exception:
                frame_number = max(0, int(frame_number))
            self.current_frame = int(frame_number)
            try:
                self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                ret, frame = self.video_cap.read()
            except Exception:
                ret = False
                frame = None
            if ret and frame is not None:
                try:
                    self._display_frame(frame)
                except Exception:
                    pass
            # update UI indicators but do not modify controls state
            try:
                self.progress_slider.setValue(self.current_frame)
            except Exception:
                pass
            try:
                self.update_time_label()
            except Exception:
                pass
            try:
                # update csv cursor to reflect preview position
                self._update_csv_cursor_from_video()
            except Exception:
                pass
        finally:
            self._fast_seek_lock = False

    def load_embedded_resources(self):
        print("[ephy] load_embedded_resources start", flush=True)
        # Cargar video embebido si existe
        try:
            if os.path.exists(self.embedded_video_path):
                try:
                    self.load_video(self.embedded_video_path)
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, 'Aviso', f'Error al cargar video embebido: {e}')
                    print(f"[ephy] load_embedded_resources: error loading video: {e}", flush=True)
            else:
                self.statusBar().showMessage(f'Video embebido no encontrado: {self.embedded_video_path}', 5000)
                print(f"[ephy] load_embedded_resources: video not found {self.embedded_video_path}", flush=True)
        except Exception as e:
            print(f"[ephy] load_embedded_resources unexpected error: {e}", flush=True)

        # Cargar CSVs embebidos
        try:
            self.load_csvs()
            print("[ephy] load_embedded_resources: load_csvs done", flush=True)
        except Exception as e:
            print(f"[ephy] load_embedded_resources: load_csvs error: {e}", flush=True)

        # Cargar datos de GaitRite (misma carpeta que los CSV de L/R si existen)
        try:
            self.load_gaitrite_data()
        except Exception:
            pass

        print("[ephy] load_embedded_resources end", flush=True)

    def load_csvs(self):
        print("[ephy] load_csvs start", flush=True)
        # Buscar primer CSV válido (normalmente L.csv)
        csv_to_plot = None
        for p in self.csv_paths:
            if os.path.exists(p):
                csv_to_plot = p
                break
        print(f"[ephy] load_csvs: csv_to_plot={csv_to_plot}", flush=True)
        if csv_to_plot is None:
            self.plot_widget.clear()
            self.plot_widget.plot([0], [0], pen=pg.mkPen('k'))
            print("[ephy] load_csvs: no csv found, showing placeholder", flush=True)
            return

        # Cargar CSV L
        try:
            df_L = pd.read_csv(csv_to_plot, header=0)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Aviso', f'Error leyendo CSV L: {e}')
            print(f"[ephy] load_csvs: error reading L.csv: {e}", flush=True)
            return

        max_col_L = min(32, df_L.shape[1])
        if max_col_L < 1:
            return
        dfL_sel = df_L.iloc[:, 0:max_col_L]

        # Intentar localizar R.csv en la misma carpeta que L.csv
        dir_csv = os.path.dirname(csv_to_plot)
        candidate_R = os.path.join(dir_csv, 'R.csv')
        df_R = None
        if os.path.exists(candidate_R):
            try:
                df_R = pd.read_csv(candidate_R, header=0)
            except Exception:
                df_R = None

        if df_R is not None:
            max_col_R = min(32, df_R.shape[1])
            if max_col_R < 1:
                dfR_sel = pd.DataFrame()
            else:
                dfR_sel = df_R.iloc[:, 0:max_col_R]
        else:
            dfR_sel = pd.DataFrame()

        cols_per_group = 8
        len_L = dfL_sel.shape[0]
        len_R = dfR_sel.shape[0] if not dfR_sel.empty else 0
        max_len = max(len_L, len_R, 1)

        # x axis in seconds
        x = np.arange(max_len) / float(self.csv_sampling_rate) if self.csv_sampling_rate > 0 else np.arange(max_len)

        # compute sums for L
        sums_L = []
        n_cols_L = dfL_sel.shape[1]
        for gi in range(4):
            start = gi * cols_per_group
            end = min(start + cols_per_group, n_cols_L)
            if start >= n_cols_L:
                y_sum = np.zeros(max_len, dtype=float)
            else:
                group_df = dfL_sel.iloc[:, start:end].fillna(0).astype(float)
                arr = group_df.to_numpy()
                if arr.shape[0] < max_len:
                    pad = np.zeros((max_len - arr.shape[0], arr.shape[1]), dtype=float)
                    arr = np.vstack([arr, pad])
                y_sum = arr.sum(axis=1)
            sums_L.append((start, end, y_sum))

        # compute sums for R
        sums_R = []
        if not dfR_sel.empty:
            n_cols_R = dfR_sel.shape[1]
            for gi in range(4):
                start = gi * cols_per_group
                end = min(start + cols_per_group, n_cols_R)
                if start >= n_cols_R:
                    y_sum = np.zeros(max_len, dtype=float)
                else:
                    group_df = dfR_sel.iloc[:, start:end].fillna(0).astype(float)
                    arr = group_df.to_numpy()
                    if arr.shape[0] < max_len:
                        pad = np.zeros((max_len - arr.shape[0], arr.shape[1]), dtype=float)
                        arr = np.vstack([arr, pad])
                    y_sum = arr.sum(axis=1)
                sums_R.append((start, end, y_sum))
        else:
            for gi in range(4):
                sums_R.append((0, 0, np.zeros(max_len, dtype=float)))

        # store arrays for synchronization
        self.sums_L = [y for (_, _, y) in sums_L]
        self.sums_R = [y for (_, _, y) in sums_R]
        self.csv_len = max_len

        # plot
        self.plot_widget.clear()
        self.plot_items_L = []
        self.plot_items_R = []
        colors = ['r', 'g', 'b', 'm']
        offset = 30000.0
        # store in instance so markers use same offset
        self.r_offset = float(offset)
        for gi in range(4):
            sL, eL, yL = sums_L[gi]
            penL = pg.mkPen(colors[gi % len(colors)], width=2)
            piL = self.plot_widget.plot(x, yL, pen=penL, name=f'L Grupo {gi+1} (cols {sL}..{eL-1 if eL> sL else sL})')
            self.plot_items_L.append(piL)

            sR, eR, yR = sums_R[gi]
            yR_shifted = yR - self.r_offset
            penR = pg.mkPen(colors[gi % len(colors)], width=2, style=QtCore.Qt.DashLine)
            piR = self.plot_widget.plot(x, yR_shifted, pen=penR, name=f'R Grupo {gi+1} (cols {sR}..{eR-1 if eR> sR else sR})')
            self.plot_items_R.append(piR)

        # Precreate scatter items once to avoid allocations during reproducción
        if self.scatter_L is None:
            self.scatter_L = pg.ScatterPlotItem(size=10, brush=pg.mkBrush(255, 200, 0), pen=pg.mkPen('k'))
            self.plot_widget.addItem(self.scatter_L)
            self.scatter_L.setData(x=[], y=[])
        if self.scatter_R is None:
            # use slightly darker blue for R markers to match footprint shade
            self.scatter_R = pg.ScatterPlotItem(size=10, brush=pg.mkBrush(33, 97, 140), pen=pg.mkPen('k'))
            self.plot_widget.addItem(self.scatter_R)
            self.scatter_R.setData(x=[], y=[])

        # keep R markers available but we will update only one point per side to save CPU
        try:
            self.scatter_R.setVisible(True)
        except Exception:
            pass

        # Create a single QGraphicsLineItem in the scene so it renders above plot curves
        if self.cursor_segment is None:
            try:
                seg_pen = pg.mkPen(color=(255, 200, 0), width=4)
                self.cursor_segment = pg.PlotDataItem(pen=seg_pen)
                # add after plotting so it renders on top; force very high Z
                self.plot_widget.addItem(self.cursor_segment)
                try:
                    self.cursor_segment.setZValue(10**6)
                except Exception:
                    pass
                self.cursor_segment.setData(x=[], y=[])
            except Exception:
                self.cursor_segment = None

        # hide the separate scatter markers now that we draw a single connecting segment
        try:
            if self.scatter_L is not None:
                self.scatter_L.setVisible(False)
            if self.scatter_R is not None:
                self.scatter_R.setVisible(False)
        except Exception:
            pass

        total_seconds = float(self.csv_len) / float(self.csv_sampling_rate) if self.csv_sampling_rate>0 else float(self.csv_len)
        win = min(self.plot_window_seconds, total_seconds)
        self.plot_widget.setXRange(0, win, padding=0)

        # update cursor initial position
        self._update_csv_cursor_from_video()
        print("[ephy] load_csvs done", flush=True)

    def closeEvent(self, event):
        print("[ephy] closeEvent triggered", flush=True)
        self.stop()
        event.accept()  # Aceptar el evento de cierre

    def showEvent(self, event):
        print("[ephy] VideoPlayer.showEvent called", flush=True)
        super().showEvent(event)

    def hideEvent(self, event):
        print("[ephy] VideoPlayer.hideEvent called", flush=True)
        super().hideEvent(event)

    def set_playback_rate(self, rate: float):
        """Set playback speed multiplier (e.g., 0.5, 1.0, 2.0). If playing, adjust timer interval immediately."""
        try:
            rate = float(rate)
            if rate <= 0:
                return
            self.playback_rate = rate
            # update label text if present
            try:
                if self.speed_label is not None:
                    # show as '1.00x' style
                    self.speed_label.setText(f'Velocidad: {self.playback_rate:.2f}x')
            except Exception:
                pass
            # if currently playing, restart timer with new interval
            try:
                if self.is_playing and self.fps > 0:
                    interval = int(max(1, 1000.0 / (self.fps * self.playback_rate)))
                    self.timer.start(interval)
            except Exception:
                pass
        except Exception:
            pass

    def show_empty_gaitrite(self):
        """Muestra plot vacío con representación de la alfombra (fallback simple).
        Usa las constantes CARPET_WIDTH_CM y CARPET_LENGTH_CM para las dimensiones.
        """
        try:
            self.gaitrite_plot.clear()
            # Use the global constants so carpet dimensions are correct
            CARPET_W = float(CARPET_WIDTH_CM)
            CARPET_H = float(CARPET_LENGTH_CM)
            bg_x = [0, CARPET_W, CARPET_W, 0, 0]
            bg_y = [0, 0, CARPET_H, CARPET_H, 0]
            # dibujar rectángulo de fondo (alfombra)
            self.gaitrite_plot.plot(bg_x, bg_y, pen=pg.mkPen('gray', width=2), fillLevel=0,
                                     brush=pg.mkBrush(240, 240, 240, 100))
            # informative text
            txt = pg.TextItem("Alfombra GaitRite\n(placeholder)", anchor=(0.5, 0.5), color='#7F8C8D')
            txt.setPos(CARPET_W / 2.0, CARPET_H / 2.0)
            self.gaitrite_plot.addItem(txt)
            # set view limits based on carpet
            try:
                self.gaitrite_plot.disableAutoRange()
                padding_x = max(1.0, CARPET_W * 0.05)
                padding_y = max(1.0, CARPET_H * 0.05)
                self.gaitrite_plot.setXRange(-padding_x, CARPET_W + padding_x, padding=0)
                self.gaitrite_plot.setYRange(-padding_y, CARPET_H + padding_y, padding=0)
            except Exception:
                pass
        except Exception:
            pass

    def load_gaitrite_data(self):
        """Carga y dibuja datos tipo GaitRite desde la misma carpeta que los CSV embebidos.
        Dibuja contornos de huella si existen, sino usa el fallback de rectángulos + trayectoria.
        También pinta la trayectoria combinada (left+right) si hay datos.
        """
        try:
            # buscar carpeta base a partir del primer csv conocido
            base_dir = None
            for p in self.csv_paths:
                if os.path.exists(p):
                    base_dir = os.path.dirname(p)
                    break
            if base_dir is None:
                # nothing to do
                return

            gait_file = os.path.join(base_dir, 'gaitrite_test.csv')
            left_fp = os.path.join(base_dir, 'generated_footprints_left.csv')
            right_fp = os.path.join(base_dir, 'generated_footprints_right.csv')

            df_gait = None
            if os.path.exists(gait_file):
                try:
                    df_gait = pd.read_csv(gait_file, delimiter=';')
                except Exception:
                    df_gait = pd.read_csv(gait_file)
                except Exception as e:
                    print(f"[ephy] load_gaitrite_data: error opening {gait_file}: {e}", flush=True)
                    df_gait = None

            # try to load precise contours first
            footprints_left_df = None
            footprints_right_df = None
            if os.path.exists(left_fp):
                try:
                    footprints_left_df = pd.read_csv(left_fp)
                except Exception:
                    footprints_left_df = None
            if os.path.exists(right_fp):
                try:
                    footprints_right_df = pd.read_csv(right_fp)
                except Exception:
                    footprints_right_df = None

            # clear plot and draw carpet
            self.gaitrite_plot.clear()
            self._draw_gaitrite_carpet(show_text=False)

            drew = False
            # if precise contours exist, draw them
            # left footprints stay red, right footprints use a slightly darker blue
            for df, color in ((footprints_left_df, '#E74C3C'), (footprints_right_df, '#21618C')):
                if df is None or df.empty:
                    continue
                try:
                    # attempt to draw polygons grouped by gait/event if such columns exist
                    if 'gait_id' in df.columns:
                        group_col = 'gait_id'
                    elif 'Gait_Id' in df.columns:
                        group_col = 'Gait_Id'
                    else:
                        group_col = None

                    if group_col is not None:
                        for gv, grp in df.groupby(group_col):
                            for ev, g2 in grp.groupby('event') if 'event' in grp.columns else ((None, grp),):
                                grp_sorted = g2.sort_values('sample_idx') if 'sample_idx' in g2.columns else g2
                                if 'x_cm' in grp_sorted.columns and 'y_cm' in grp_sorted.columns:
                                    # draw polygon/contour
                                    self.gaitrite_plot.plot(grp_sorted['x_cm'].values, grp_sorted['y_cm'].values,
                                                            pen=pg.mkPen(color=color, width=2))
                                    drew = True
                    else:
                        # If no grouping column, try to draw by contiguous runs of points
                        if 'x_cm' in df.columns and 'y_cm' in df.columns:
                            self.gaitrite_plot.plot(df['x_cm'].values, df['y_cm'].values,
                                                    pen=pg.mkPen(color=color, width=2))
                            drew = True
                except Exception:
                    continue

            # Build combined trajectory points (from footprints if available, else from gait_file)
            traj_x = []
            traj_y = []
            try:
                # Use exclusively gaitrite_test.csv to compute trajectory centers.
                if df_gait is not None and not df_gait.empty:
                    try:
                        CONVERSION_FACTOR = 1.27
                        # compute centers using midpoints from expected columns
                        if all(c in df_gait.columns for c in ('Ybottom', 'Ytop', 'Xback', 'Xfront')):
                            ctr_x = (((df_gait['Ybottom'].astype(float) + df_gait['Ytop'].astype(float)) / 2.0) * CONVERSION_FACTOR).values
                            ctr_y = (((df_gait['Xback'].astype(float) + df_gait['Xfront'].astype(float)) / 2.0) * CONVERSION_FACTOR).values
                            traj_x = list(ctr_x)
                            traj_y = list(ctr_y)
                        else:
                            # Try alternative column names if present (common variations)
                            alt_x = next((c for c in df_gait.columns if c.lower().startswith('y')), None)
                            alt_x2 = next((c for c in df_gait.columns if 'bottom' in c.lower() or 'top' in c.lower()), None)
                            alt_y = next((c for c in df_gait.columns if c.lower().startswith('x')), None)
                            if alt_x is not None and alt_y is not None:
                                try:
                                    traj_x = list(pd.to_numeric(df_gait[alt_x], errors='coerce').dropna().astype(float).values)
                                    traj_y = list(pd.to_numeric(df_gait[alt_y], errors='coerce').dropna().astype(float).values)
                                except Exception:
                                    traj_x = []
                                    traj_y = []
                    except Exception:
                        pass
            except Exception:
                pass

            # if we have a trajectory, draw it clearly on top
            try:
                if len(traj_x) > 1:
                    self.gaitrite_plot.plot(traj_x, traj_y, pen=pg.mkPen('black', width=2))
                    # mark start and end
                    try:
                        sp = pg.ScatterPlotItem(size=8, brush=pg.mkBrush(0, 200, 0), pen=pg.mkPen('k'))
                        ep = pg.ScatterPlotItem(size=8, brush=pg.mkBrush(200, 0, 0), pen=pg.mkPen('k'))
                        sp.setData(x=[traj_x[0]], y=[traj_y[0]])
                        ep.setData(x=[traj_x[-1]], y=[traj_y[-1]])
                        self.gaitrite_plot.addItem(sp)
                        self.gaitrite_plot.addItem(ep)
                    except Exception:
                        pass
            except Exception:
                pass

            # finally lock view to reasonable bounds if possible (include trajectory extents)
            try:
                self.gaitrite_plot.disableAutoRange()
                all_x = []
                all_y = []
                for it in self.gaitrite_plot.listDataItems():
                    try:
                        d = it.getData()
                        if d is None:
                            continue
                        xs, ys = d
                        all_x.extend(list(xs))
                        all_y.extend(list(ys))
                    except Exception:
                        continue
                if len(all_x) > 0 and len(all_y) > 0:
                    minx, maxx = min(all_x), max(all_x)
                    miny, maxy = min(all_y), max(all_y)
                    padding_x = max(1.0, (maxx - minx) * 0.10)
                    padding_y = max(1.0, (maxy - miny) * 0.08)
                    self.gaitrite_plot.setXRange(minx - padding_x, maxx + padding_x, padding=0)
                    self.gaitrite_plot.setYRange(miny - padding_y, maxy + padding_y, padding=0)
                else:
                    # fallback carpet size
                    CARPET_W = float(CARPET_WIDTH_CM)
                    CARPET_H = float(CARPET_LENGTH_CM)
                    padding_x = CARPET_W * 0.10
                    padding_y = CARPET_H * 0.08
                    self.gaitrite_plot.setXRange(-padding_x, CARPET_W + padding_x, padding=0)
                    self.gaitrite_plot.setYRange(-padding_y, CARPET_H + padding_y, padding=0)
            except Exception:
                pass

        except Exception:
            # on any problem keep the empty plot
            try:
                self.show_empty_gaitrite()
            except Exception:
                pass

    def _draw_gaitrite_carpet(self, show_text=True):
        """Dibuja una representación simple de la alfombra GaitRite (placeholder).
        Ahora usa CARPET_WIDTH_CM y CARPET_LENGTH_CM para las dimensiones.
        """
        try:
            self.gaitrite_plot.clear()
            CARPET_W = float(CARPET_WIDTH_CM)
            CARPET_H = float(CARPET_LENGTH_CM)
            bg_x = [0, CARPET_W, CARPET_W, 0, 0]
            bg_y = [0, 0, CARPET_H, CARPET_H, 0]
            self.gaitrite_plot.plot(bg_x, bg_y, pen=pg.mkPen('gray', width=2), fillLevel=0,
                                     brush=pg.mkBrush(240, 240, 240, 100))
            if show_text:
                txt = pg.TextItem("Alfombra GaitRite\n(placeholder)", anchor=(0.5, 0.5), color='#7F8C8D')
                txt.setPos(CARPET_W / 2.0, CARPET_H / 2.0)
                self.gaitrite_plot.addItem(txt)
            # set view
            try:
                self.gaitrite_plot.disableAutoRange()
                padding_x = max(1.0, CARPET_W * 0.05)
                padding_y = max(1.0, CARPET_H * 0.05)
                self.gaitrite_plot.setXRange(-padding_x, CARPET_W + padding_x, padding=0)
                self.gaitrite_plot.setYRange(-padding_y, CARPET_H + padding_y, padding=0)
            except Exception:
                pass
        except Exception:
            pass

    def discover_data_sets(self):
        """Busca carpetas de datos bajo el proyecto que contengan video (*.mp4) o CSV (L.csv).
        Retorna lista de tuplas (label, abs_path).
        """
        results = []
        base_dir = os.path.abspath(os.path.dirname(__file__))
        roots = [os.path.join(base_dir, 'data'), base_dir]
        seen = set()
        for root in roots:
            if not os.path.isdir(root):
                continue
            # limitar búsqueda a profundidad razonable: revisar subdirs hasta profundidad 3
            for dirpath, dirnames, filenames in os.walk(root):
                # compute depth relative to root
                rel = os.path.relpath(dirpath, root)
                depth = 0 if rel == '.' else rel.count(os.sep) + 1
                if depth > 3:
                    # prune deeper directories
                    dirnames[:] = []
                    continue
                # check for mp4 or L.csv presence
                has_video = any(f.lower().endswith('.mp4') for f in filenames)
                has_lcsv = any(f.lower() == 'l.csv' for f in filenames) or any(f.lower().endswith('l.csv') and f.lower() != 'l.csv' for f in filenames)
                if has_video or has_lcsv:
                    abspath = os.path.abspath(dirpath)
                    if abspath in seen:
                        continue
                    seen.add(abspath)
                    label = os.path.relpath(dirpath, base_dir)
                    results.append((label, abspath))
        # also try to include obvious P* top-level folders if none found
        if not results:
            for p in os.listdir(base_dir):
                pth = os.path.join(base_dir, p)
                if os.path.isdir(pth) and p.upper().startswith('P'):
                    results.append((p, pth))
        # ensure deterministic order
        results.sort()
        return results

    # ------------------ Nuevos helpers para selectores encadenados ------------------
    def populate_subjects(self):
        """Pobla self.combo_subject con carpetas dentro de data/ (solo directorios que empiecen por 'P').
        Deja una opción placeholder al inicio para que nada esté seleccionado por defecto.
        """
        try:
            base_dir = os.path.abspath(os.path.dirname(__file__))
            data_dir = os.path.join(base_dir, 'data')
            self.combo_subject.clear()
            # start disabled until we populate
            try:
                self.combo_group.clear()
                self.combo_session.clear()
                self.combo_group.setEnabled(False)
                self.combo_session.setEnabled(False)
                self.btn_load_dataset.setEnabled(False)
            except Exception:
                pass

            if not os.path.isdir(data_dir):
                # keep subject combo disabled and empty
                try:
                    self.combo_subject.setEnabled(False)
                except Exception:
                    pass
                return

            subjects = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
            # keep only P* folders to match dataset naming
            subjects = [d for d in subjects if d.upper().startswith('P')]
            subjects.sort()

            # add placeholder first so nothing is 'selected' by default
            try:
                self.combo_subject.addItem('Select subject...', userData=None)
            except Exception:
                pass

            for s in subjects:
                self.combo_subject.addItem(s, userData=os.path.join(data_dir, s))

            # ensure no real subject is selected initially
            try:
                self.combo_subject.setCurrentIndex(0)
                self.combo_subject.setEnabled(True)
            except Exception:
                pass
        except Exception:
            pass

    def on_subject_changed(self, index: int):
        try:
            print(f"[ephy] on_subject_changed: index={index}", flush=True)
            if index < 0:
                return
            subject_path = self.combo_subject.itemData(index)
            if not subject_path:
                # disable downstream
                try:
                    self.combo_group.clear()
                    self.combo_session.clear()
                    self.combo_group.setEnabled(False)
                    self.combo_session.setEnabled(False)
                    self.btn_load_dataset.setEnabled(False)
                except Exception:
                    pass
                return
            self.populate_groups(subject_path)
            # enable load button once a subject is selected (but only enable when groups/sessions present)
            try:
                self.btn_load_dataset.setEnabled(True)
            except Exception:
                pass
        except Exception:
            pass

    def populate_groups(self, subject_path: str):
        """Pobla self.combo_group con subdirectorios del subject (FP, NP, etc.), ignorando SITDOWN y STAND.
        Añade un placeholder al inicio para que no haya selección por defecto.
        """
        try:
            self.combo_group.clear()
            self.combo_session.clear()
            # start disabled until we populate
            self.combo_group.setEnabled(False)
            self.combo_session.setEnabled(False)
            if not subject_path or not os.path.isdir(subject_path):
                return
            groups = [d for d in os.listdir(subject_path) if os.path.isdir(os.path.join(subject_path, d))]
            # ignore these categories
            ignore = {'sitdown', 'stand'}
            groups = [g for g in groups if g.lower() not in ignore]
            groups.sort()

            # add placeholder first so nothing is selected by default
            try:
                self.combo_group.addItem('Select category...', userData=None)
            except Exception:
                pass

            for g in groups:
                self.combo_group.addItem(g, userData=os.path.join(subject_path, g))

            # ensure no real group is selected initially
            try:
                self.combo_group.setCurrentIndex(0)
                # enable the combo so user can open it and choose
                self.combo_group.setEnabled(True)
            except Exception:
                pass
        except Exception:
            pass

    def on_group_changed(self, index: int):
        try:
            print(f"[ephy] on_group_changed: index={index}", flush=True)
            if index < 0:
                return
            group_path = self.combo_group.itemData(index)
            if not group_path:
                # disable sessions
                try:
                    self.combo_session.clear()
                    self.combo_session.setEnabled(False)
                except Exception:
                    pass
                return
            self.populate_sessions(group_path)
        except Exception:
            pass

    def populate_sessions(self, group_path: str):
        """Pobla self.combo_session con subdirectorios de la categoría (1,2,...) o con archivos si no hay subdirs.
        Añade un placeholder al inicio para que no haya selección por defecto.
        """
        try:
            self.combo_session.clear()
            self.combo_session.setEnabled(False)
            if not group_path or not os.path.isdir(group_path):
                return
            # preferir subdirectorios numéricos
            subs = [d for d in os.listdir(group_path) if os.path.isdir(os.path.join(group_path, d))]
            subs.sort()

            # add placeholder first
            try:
                self.combo_session.addItem('Select session...', userData=None)
            except Exception:
                pass

            if subs:
                for s in subs:
                    self.combo_session.addItem(s, userData=os.path.join(group_path, s))
            else:
                # si no hay subdirs, permitir seleccionar la misma carpeta (por ejemplo si L.csv está en group)
                self.combo_session.addItem(os.path.basename(group_path), userData=group_path)

            # ensure no real session is selected initially
            try:
                self.combo_session.setCurrentIndex(0)
                self.combo_session.setEnabled(True)
            except Exception:
                pass
        except Exception:
            pass

    def on_load_dataset_clicked(self):
        """Construye la ruta seleccionada y llama a configure_dataset_from_path para cargar video/CSV."""
        try:
            subj_idx = self.combo_subject.currentIndex()
            if subj_idx < 0:
                QtWidgets.QMessageBox.information(self, 'Info', 'Selecciona primero un Subject')
                return
            subj_path = self.combo_subject.itemData(subj_idx)

            grp_idx = self.combo_group.currentIndex()
            grp_path = self.combo_group.itemData(grp_idx) if grp_idx >= 0 else None

            sess_idx = self.combo_session.currentIndex()
            sess_path = self.combo_session.itemData(sess_idx) if sess_idx >= 0 else None

            # preferir la ruta de sesión si existe, sino la de grupo, sino subject
            target = None
            if sess_path:
                target = sess_path
            elif grp_path:
                target = grp_path
            else:
                target = subj_path

            print(f"[ephy] on_load_dataset_clicked: subj={subj_path}, group={grp_path}, session={sess_path}, target={target}", flush=True)

            if not target or not os.path.isdir(target):
                QtWidgets.QMessageBox.warning(self, 'Aviso', f'Ruta seleccionada no válida: {target}')
                return

            # llamar a configurador que buscará MP4/L.csv recursivamente
            self.configure_dataset_from_path(target)

            # Reset playback and UI to start of dataset to avoid requiring manual Reset
            try:
                # stop playback if running
                try:
                    if getattr(self, 'is_playing', False):
                        self.stop()
                except Exception:
                    pass

                # ensure frame index zero and slider reset
                try:
                    self.current_frame = 0
                except Exception:
                    pass
                try:
                    self.progress_slider.setValue(0)
                except Exception:
                    pass

                # seek video capture to start and show first frame if available
                try:
                    if getattr(self, 'video_cap', None) is not None and getattr(self.video_cap, 'isOpened', lambda: False)():
                        try:
                            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            self.show_frame()
                        except Exception:
                            pass
                except Exception:
                    pass

                # update labels and csv cursor
                try:
                    self.update_time_label()
                except Exception:
                    pass
                try:
                    self._update_csv_cursor_from_video()
                except Exception:
                    pass

                try:
                    self.btn_play.setText('▶ Play')
                except Exception:
                    pass
            except Exception as e:
                print(f"[ephy] on_load_dataset_clicked: reset error: {e}", flush=True)

            # mostrar mensaje en status bar
            try:
                self.statusBar().showMessage(f'Loaded dataset: {target}', 5000)
            except Exception:
                pass
        except Exception as e:
            print(f"[ephy] on_load_dataset_clicked error: {e}", flush=True)
            pass

    def configure_dataset_from_path(self, path: str):
        """Configura rutas (video + csv_paths) a partir de una carpeta de datos y carga los recursos.
        Busca primero MP4 y luego L.csv en la carpeta; si no los encuentra, busca recursivamente.
        """
        try:
            # normalize
            base = os.path.abspath(path)
            print(f"[ephy] configure_dataset_from_path: scanning base={base}", flush=True)
            video_found = None
            lcsv_found = None
            # prefer files in the folder itself first
            try:
                for fn in sorted(os.listdir(base)):
                    if fn.lower().endswith('.mp4') and video_found is None:
                        video_found = os.path.join(base, fn)
                    if fn.lower() == 'l.csv' and lcsv_found is None:
                        lcsv_found = os.path.join(base, fn)
                # if not found, walk shallowly
                if video_found is None or lcsv_found is None:
                    for dirpath, dirnames, filenames in os.walk(base):
                        # skip SITDOWN/STAND dirs explicitly
                        dirnames[:] = [d for d in dirnames if d.lower() not in ('sitdown', 'stand')]
                        for fn in filenames:
                            if video_found is None and fn.lower().endswith('.mp4'):
                                video_found = os.path.join(dirpath, fn)
                            if lcsv_found is None and fn.lower().endswith('l.csv'):
                                lcsv_found = os.path.join(dirpath, fn)
                        # stop early if both found
                        if video_found is not None and lcsv_found is not None:
                            break
            except Exception:
                pass

            print(f"[ephy] configure_dataset_from_path: video_found={video_found}, lcsv_found={lcsv_found}", flush=True)

            # set instance paths
            if video_found is not None:
                self.embedded_video_path = video_found
                try:
                    self.load_video(self.embedded_video_path)
                except Exception as e:
                    print(f"[ephy] configure_dataset_from_path: error loading video {e}", flush=True)
            else:
                # no video found: clear current video and inform user
                print(f"[ephy] configure_dataset_from_path: no video in {base}", flush=True)
                try:
                    self.statusBar().showMessage('No video found in selected dataset', 5000)
                except Exception:
                    pass

            if lcsv_found is not None:
                self.csv_paths = [lcsv_found]
            else:
                # fallback: try to find any csv in folder
                any_csv = None
                try:
                    for dirpath, dirnames, filenames in os.walk(base):
                        dirnames[:] = [d for d in dirnames if d.lower() not in ('sitdown', 'stand')]
                        for fn in filenames:
                            if fn.lower().endswith('.csv'):
                                any_csv = os.path.join(dirpath, fn)
                                break
                        if any_csv:
                            break
                except Exception:
                    any_csv = None
                if any_csv:
                    self.csv_paths = [any_csv]
                else:
                    self.csv_paths = []

            print(f"[ephy] configure_dataset_from_path: final csv_paths={self.csv_paths}", flush=True)

            # Ensure footprints exist: if both left+right already present in dataset folder, do nothing.
            try:
                left_targets = [os.path.join(base, 'generated_footprints_left.csv'), os.path.join(base, 'footprints_left.csv')]
                right_targets = [os.path.join(base, 'generated_footprints_right.csv'), os.path.join(base, 'footprints_right.csv')]
                left_exists = any(os.path.exists(p) for p in left_targets)
                right_exists = any(os.path.exists(p) for p in right_targets)

                if left_exists and right_exists:
                    print(f"[ephy] configure_dataset_from_path: footprints already present in {base}, skipping generation", flush=True)
                else:
                    # First attempt: if gaitrite_test.csv exists in the dataset folder, use its Yarray column to generate footprints
                    gait_file = os.path.join(base, 'gaitrite_test.csv')
                    generated_any = False
                    if os.path.exists(gait_file):
                        try:
                            try:
                                df_g = pd.read_csv(gait_file, delimiter=';')
                            except Exception:
                                df_g = pd.read_csv(gait_file)
                        except Exception as e:
                            print(f"[ephy] configure_dataset_from_path: failed reading {gait_file}: {e}", flush=True)
                            df_g = None

                        if df_g is not None and not df_g.empty:
                            # required columns for decoding
                            req = {'Gait_Id', 'Event', 'Foot', 'Xback', 'Xfront', 'Ybottom', 'Ytop', 'Yarray'}
                            if req.issubset(set(df_g.columns)):
                                try:
                                    # try to reuse decoder from export_yarray_footprints if available
                                    try:
                                        from export_yarray_footprints import decode_yarray_to_xy
                                    except Exception:
                                        decode_yarray_to_xy = None

                                    accum = {0: [], 1: []}
                                    for _, r in df_g.iterrows():
                                        try:
                                            foot = int(r['Foot']) if pd.notna(r['Foot']) else None
                                        except Exception:
                                            foot = None
                                        if foot not in (0, 1):
                                            continue
                                        try:
                                            Xback_cm = float(r['Xback']) * 1.27
                                            Xfront_cm = float(r['Xfront']) * 1.27
                                            Ybottom_cm = float(r['Ybottom']) * 1.27
                                            Ytop_cm = float(r['Ytop']) * 1.27
                                        except Exception:
                                                                                       continue
                                        yarray_raw = str(r['Yarray']) if pd.notna(r['Yarray']) else ''
                                        if decode_yarray_to_xy is not None:
                                            df_xy = decode_yarray_to_xy(yarray_raw, Xback_cm, Xfront_cm, Ybottom_cm, Ytop_cm)
                                        else:
                                            # fallback implementation of decode similar to exporter
                                            try:
                                                vals = np.fromiter((ord(c) for c in yarray_raw), dtype=float, count=len(yarray_raw))
                                                if vals.size == 0 or not np.isfinite(vals).all():
                                                    df_xy = None
                                                else:
                                                    lo = np.percentile(vals, 1)
                                                    hi = np.percentile(vals, 99)
                                                    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
                                                        lo, hi = float(np.min(vals)), float(np.max(vals))
                                                    if hi == lo:
                                                        hi = lo + 1e-9
                                                    vals_norm = (vals - lo) / (hi - lo)
                                                    N = vals.shape[0]
                                                    x_cm = Ybottom_cm + vals_norm * (Ytop_cm - Ybottom_cm)
                                                    y_cm = np.linspace(Xback_cm, Xfront_cm, N)
                                                    df_xy = pd.DataFrame({
                                                        'sample_idx': np.arange(N, dtype=int),
                                                        'x_cm': x_cm.astype(float),
                                                        'y_cm': y_cm.astype(float),
                                                    })
                                            except Exception:
                                                df_xy = None

                                        if df_xy is None or df_xy.empty:
                                            continue

                                        df_xy = df_xy.copy()
                                        df_xy['participant'] = os.path.basename(base)
                                        df_xy['source_file'] = os.path.basename(gait_file)
                                        df_xy['gait_id'] = int(r['Gait_Id']) if pd.notna(r['Gait_Id']) else None
                                        df_xy['event'] = int(r['Event']) if pd.notna(r['Event']) else None
                                        df_xy['foot'] = foot
                                        df_xy['xback_cm'] = Xback_cm
                                        df_xy['xfront_cm'] = Xfront_cm
                                        df_xy['ybottom_cm'] = Ybottom_cm
                                        df_xy['ytop_cm'] = Ytop_cm
                                        df_xy['n_samples'] = int(df_xy.shape[0])

                                        accum[foot].append(df_xy)
                                    # write outputs for each foot if missing
                                    try:
                                        target_left = os.path.join(base, 'generated_footprints_left.csv')
                                        target_right = os.path.join(base, 'generated_footprints_right.csv')
                                        if not left_exists and accum[0]:
                                            out_left = pd.concat(accum[0], ignore_index=True).sort_values(['gait_id', 'event', 'sample_idx']).reset_index(drop=True)
                                            out_left.to_csv(target_left, index=False)
                                            print(f"[ephy] configure_dataset_from_path: wrote {target_left}", flush=True)
                                            generated_any = True
                                            left_exists = True
                                        if not right_exists and accum[1]:
                                            out_right = pd.concat(accum[1], ignore_index=True).sort_values(['gait_id', 'event', 'sample_idx']).reset_index(drop=True)
                                            out_right.to_csv(target_right, index=False)
                                            print(f"[ephy] configure_dataset_from_path: wrote {target_right}", flush=True)
                                            generated_any = True
                                            right_exists = True
                                        if generated_any:
                                            try:
                                                self.statusBar().showMessage('Generated footprints from gaitrite_test.csv', 5000)
                                            except Exception:
                                                pass
                                    except Exception as e:
                                        print(f"[ephy] configure_dataset_from_path: error writing generated footprints: {e}", flush=True)
                                except Exception as e:
                                    print(f"[ephy] configure_dataset_from_path: error processing {gait_file}: {e}", flush=True)
                            else:
                                print(f"[ephy] configure_dataset_from_path: gaitrite_test.csv missing required columns in {base}", flush=True)
                        else:
                            print(f"[ephy] configure_dataset_from_path: gaitrite_test.csv empty or unreadable in {base}", flush=True)

                    # If gaitrite generation did not produce footprints, fallback to participant-level exporter using *_tests_*.csv
                    if not (left_exists and right_exists) and not generated_any:
                        try:
                            from pathlib import Path
                            import shutil
                            participant_dir = None
                            p = Path(base)
                            for candidate in [p] + list(p.parents):
                                try:
                                    if candidate.name.upper().startswith('P') and candidate.is_dir():
                                        participant_dir = candidate
                                        break
                                except Exception:
                                    continue
                            if participant_dir is None:
                                participant_dir = p

                            # attempt to find tests CSVs in participant dir
                            tests = list(participant_dir.glob('*_tests_*.csv'))
                        except Exception:
                            tests = []

                        if tests:
                            try:
                                import export_yarray_footprints as eyf
                            except Exception as e:
                                print(f"[ephy] configure_dataset_from_path: cannot import export_yarray_footprints: {e}", flush=True)
                                eyf = None

                            if eyf is not None:
                                try:
                                    print(f"[ephy] configure_dataset_from_path: invoking export_yarray_footprints on {participant_dir}", flush=True)
                                    res = eyf.process_participant(participant_dir, conv=1.27, overwrite=False)
                                    print(f"[ephy] configure_dataset_from_path: export result={res}", flush=True)
                                except Exception as e:
                                    print(f"[ephy] configure_dataset_from_path: export error: {e}", flush=True)

                                # copy any produced footprints into the dataset folder, but only for missing targets
                                try:
                                    produced_map = {
                                        'left': [participant_dir / 'generated_footprints_left.csv', participant_dir / 'footprints_left.csv'],
                                        'right': [participant_dir / 'generated_footprints_right.csv', participant_dir / 'footprints_right.csv']
                                    }
                                    target_left = os.path.join(base, 'generated_footprints_left.csv')
                                    target_right = os.path.join(base, 'generated_footprints_right.csv')

                                    if not left_exists:
                                        for src in produced_map['left']:
                                            if src.exists():
                                                shutil.copy2(str(src), target_left)
                                                print(f"[ephy] configure_dataset_from_path: copied {src} -> {target_left}", flush=True)
                                                left_exists = True
                                                break
                                    if not right_exists:
                                        for src in produced_map['right']:
                                            if src.exists():
                                                shutil.copy2(str(src), target_right)
                                                print(f"[ephy] configure_dataset_from_path: copied {src} -> {target_right}", flush=True)
                                                right_exists = True
                                                break

                                    if left_exists or right_exists:
                                        try:
                                            self.statusBar().showMessage('Footprints generated/copied for gaitrite (dataset folder updated)', 5000)
                                        except Exception:
                                            pass
                                except Exception as e:
                                    print(f"[ephy] configure_dataset_from_path: error copying footprints: {e}", flush=True)
                        else:
                            print(f"[ephy] configure_dataset_from_path: no *_tests_*.csv in {participant_dir}, skipping participant export", flush=True)
            except Exception as e:
                print(f"[ephy] configure_dataset_from_path: unexpected error in footprint generation: {e}", flush=True)

            # After configuring paths, reload CSVs and gaitrite data
            try:
                self.load_csvs()
            except Exception as e:
                print(f"[ephy] configure_dataset_from_path: load_csvs error: {e}", flush=True)
            try:
                self.load_gaitrite_data()
            except Exception as e:
                print(f"[ephy] configure_dataset_from_path: load_gaitrite_data error: {e}", flush=True)
        except Exception:
            pass

def main():
    try:
        print("[ephy] starting QApplication", flush=True)
        app = QtWidgets.QApplication(sys.argv)
        # Allow the application to quit when the last window is closed
        app.setQuitOnLastWindowClosed(True)
        app.aboutToQuit.connect(lambda: print("[ephy] QApplication.aboutToQuit emitted", flush=True))
        player = VideoPlayer()
        print("[ephy] calling player.show()", flush=True)
        player.show()
        print("[ephy] player.show() returned", flush=True)
        print("[ephy] entering app.exec_()", flush=True)
        rc = app.exec_()
        print(f"[ephy] app exited rc={rc}", flush=True)
        sys.exit(rc)
    except Exception as e:
        import traceback
        print(f"[ephy] ERROR starting app: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
