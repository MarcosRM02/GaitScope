#!/usr/bin/env python3
"""
Reproductor de Video Simple con Interfaz Gráfica
Usa tkinter para la interfaz y OpenCV para la reproducción
"""

import tkinter as tk
from tkinter import filedialog, ttk
import cv2
from PIL import Image, ImageTk
import threading
import time


class VideoPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("Reproductor de Video")
        self.root.geometry("900x700")
        
        # Variables del reproductor
        self.video_cap = None
        self.is_playing = False
        self.is_paused = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30
        self.video_path = None
        self.play_thread = None
        self.canvas_image = None  # Referencia a la imagen en el canvas
        
        # Crear interfaz
        self.create_widgets()
        
        # Atajos de teclado
        self.root.bind('<space>', lambda e: self.toggle_play_pause())
        self.root.bind('<Left>', lambda e: self.prev_frame())
        self.root.bind('<Right>', lambda e: self.next_frame())
        self.root.bind('<Control-Left>', lambda e: self.backward())
        self.root.bind('<Control-Right>', lambda e: self.forward())
        
    def create_widgets(self):
        # Frame superior - Canvas para el video
        self.video_frame = tk.Frame(self.root, bg="black")
        self.video_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(self.video_frame, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Frame de controles
        controls_frame = tk.Frame(self.root, bg="#f0f0f0")
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Barra de progreso
        progress_frame = tk.Frame(controls_frame, bg="#f0f0f0")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_slider = ttk.Scale(
            progress_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.progress_var,
            command=self.on_slider_change
        )
        self.progress_slider.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=5)
        
        self.time_label = tk.Label(
            progress_frame,
            text="00:00 / 00:00",
            bg="#f0f0f0",
            font=("Arial", 10)
        )
        self.time_label.pack(side=tk.RIGHT, padx=5)
        
        # Label para número de frame
        self.frame_label = tk.Label(
            progress_frame,
            text="Frame: 0 / 0",
            bg="#f0f0f0",
            font=("Arial", 9),
            fg="#444"
        )
        self.frame_label.pack(side=tk.RIGHT, padx=10)
        
        # Botones de control
        buttons_frame = tk.Frame(controls_frame, bg="#f0f0f0")
        buttons_frame.pack()
        
        # Botón abrir archivo
        self.btn_open = tk.Button(
            buttons_frame,
            text="📁 Abrir Video",
            command=self.open_file,
            font=("Arial", 12),
            width=12,
            bg="#4CAF50",
            fg="white",
            relief=tk.RAISED,
            cursor="hand2"
        )
        self.btn_open.pack(side=tk.LEFT, padx=5)
        
        # Botón frame anterior
        self.btn_prev_frame = tk.Button(
            buttons_frame,
            text="◀ Frame",
            command=self.prev_frame,
            font=("Arial", 10),
            width=8,
            state=tk.DISABLED
        )
        self.btn_prev_frame.pack(side=tk.LEFT, padx=2)
        
        # Botón retroceder
        self.btn_backward = tk.Button(
            buttons_frame,
            text="⏪ -5s",
            command=self.backward,
            font=("Arial", 12),
            width=8,
            state=tk.DISABLED
        )
        self.btn_backward.pack(side=tk.LEFT, padx=5)
        
        # Botón play/pause
        self.btn_play = tk.Button(
            buttons_frame,
            text="▶ Play",
            command=self.toggle_play_pause,
            font=("Arial", 12, "bold"),
            width=10,
            bg="#2196F3",
            fg="white",
            relief=tk.RAISED,
            cursor="hand2",
            state=tk.DISABLED
        )
        self.btn_play.pack(side=tk.LEFT, padx=5)
        
        # Botón adelantar
        self.btn_forward = tk.Button(
            buttons_frame,
            text="+5s ⏩",
            command=self.forward,
            font=("Arial", 12),
            width=8,
            state=tk.DISABLED
        )
        self.btn_forward.pack(side=tk.LEFT, padx=5)
        
        # Botón siguiente frame
        self.btn_next_frame = tk.Button(
            buttons_frame,
            text="Frame ▶",
            command=self.next_frame,
            font=("Arial", 10),
            width=8,
            state=tk.DISABLED
        )
        self.btn_next_frame.pack(side=tk.LEFT, padx=2)
        
        # Botón detener
        self.btn_stop = tk.Button(
            buttons_frame,
            text="⏹ Stop",
            command=self.stop,
            font=("Arial", 12),
            width=8,
            bg="#f44336",
            fg="white",
            state=tk.DISABLED
        )
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        # Botón exportar frame
        self.btn_export = tk.Button(
            buttons_frame,
            text="📷 Exportar",
            command=self.export_current_frame,
            font=("Arial", 10),
            width=10,
            bg="#FF9800",
            fg="white",
            state=tk.DISABLED
        )
        self.btn_export.pack(side=tk.LEFT, padx=5)
        
        # Label para el nombre del archivo
        self.file_label = tk.Label(
            self.root,
            text="No hay video cargado",
            bg="#f0f0f0",
            font=("Arial", 10, "italic"),
            fg="#666"
        )
        self.file_label.pack(pady=5)
        
    def open_file(self):
        """Abre un diálogo para seleccionar un archivo de video"""
        file_path = filedialog.askopenfilename(
            title="Seleccionar video",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mkv *.mov *.flv *.wmv"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.load_video(file_path)
            
    def load_video(self, path):
        """Carga un video desde la ruta especificada"""
        # Detener reproducción anterior si existe
        if self.is_playing:
            self.stop()
        
        # Limpiar canvas
        self.canvas.delete("all")
        self.canvas_image = None
            
        self.video_path = path
        self.video_cap = cv2.VideoCapture(path)
        
        if not self.video_cap.isOpened():
            self.file_label.config(text="Error al cargar el video")
            return
            
        # Obtener información del video
        self.total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.video_cap.get(cv2.CAP_PROP_FPS)
        self.current_frame = 0
        
        # Actualizar interfaz
        filename = path.split("/")[-1]
        self.file_label.config(text=f"📹 {filename}")
        self.progress_slider.config(to=self.total_frames - 1)
        self.update_time_label()
        
        # Habilitar botones
        self.btn_play.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_forward.config(state=tk.NORMAL)
        self.btn_backward.config(state=tk.NORMAL)
        self.btn_next_frame.config(state=tk.NORMAL)
        self.btn_prev_frame.config(state=tk.NORMAL)
        self.btn_export.config(state=tk.NORMAL)
        
        # Mostrar primer frame
        self.show_frame()
        
    def toggle_play_pause(self):
        """Alterna entre reproducir y pausar"""
        if not self.video_cap:
            return
            
        if self.is_playing and not self.is_paused:
            # Pausar
            self.is_paused = True
            self.btn_play.config(text="▶ Play")
        elif self.is_playing and self.is_paused:
            # Reanudar
            self.is_paused = False
            self.btn_play.config(text="⏸ Pause")
        else:
            # Iniciar reproducción
            self.is_playing = True
            self.is_paused = False
            self.btn_play.config(text="⏸ Pause")
            self.play_thread = threading.Thread(target=self.play_video, daemon=True)
            self.play_thread.start()
            
    def play_video(self):
        """Reproduce el video en un hilo separado"""
        while self.is_playing and self.current_frame < self.total_frames:
            if self.is_paused:
                time.sleep(0.1)
                continue
                
            start_time = time.time()
            
            # Leer y mostrar frame
            ret = self.show_frame()
            if not ret:
                break
                
            self.current_frame += 1
            
            # Actualizar progreso en el hilo principal (thread-safe)
            self.root.after(0, self.progress_var.set, self.current_frame)
            self.root.after(0, self.update_time_label)
            
            # Controlar FPS
            elapsed = time.time() - start_time
            sleep_time = max(0, (1.0 / self.fps) - elapsed)
            time.sleep(sleep_time)
            
        # Video terminado
        if self.current_frame >= self.total_frames - 1:
            self.is_playing = False
            self.root.after(0, self.btn_play.config, {"text": "▶ Play"})
            
    def show_frame(self):
        """Muestra el frame actual en el canvas"""
        if not self.video_cap:
            return False
            
        ret, frame = self.video_cap.read()
        if ret:
            # Convertir de BGR a RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Redimensionar para ajustar al canvas
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                # Calcular proporciones
                frame_height, frame_width = frame_rgb.shape[:2]
                scale = min(canvas_width / frame_width, canvas_height / frame_height)
                new_width = int(frame_width * scale)
                new_height = int(frame_height * scale)
                
                frame_resized = cv2.resize(frame_rgb, (new_width, new_height))
                
                # Convertir a ImageTk
                img = Image.fromarray(frame_resized)
                imgtk = ImageTk.PhotoImage(image=img)
                
                # Centrar en canvas
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                
                # Actualizar imagen existente o crear nueva
                if self.canvas_image is None:
                    self.canvas_image = self.canvas.create_image(
                        x, y, anchor=tk.NW, image=imgtk
                    )
                else:
                    # Reutilizar el objeto existente (evita parpadeos)
                    self.canvas.coords(self.canvas_image, x, y)
                    self.canvas.itemconfig(self.canvas_image, image=imgtk)
                
                self.canvas.image = imgtk  # Mantener referencia
                
        return ret
                
    def stop(self):
        """Detiene la reproducción y vuelve al inicio"""
        self.is_playing = False
        self.is_paused = False
        self.current_frame = 0
        
        if self.video_cap:
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.show_frame()
            
        self.btn_play.config(text="▶ Play")
        self.progress_var.set(0)
        self.update_time_label()
        
    def forward(self):
        """Avanza 5 segundos en el video"""
        if not self.video_cap:
            return
            
        frames_to_skip = int(5 * self.fps)
        new_frame = min(self.current_frame + frames_to_skip, self.total_frames - 1)
        self.seek_to_frame(new_frame)
        
    def backward(self):
        """Retrocede 5 segundos en el video"""
        if not self.video_cap:
            return
            
        frames_to_skip = int(5 * self.fps)
        new_frame = max(self.current_frame - frames_to_skip, 0)
        self.seek_to_frame(new_frame)
    
    def next_frame(self):
        """Avanza un frame"""
        if not self.video_cap:
            return
        
        # Si está reproduciendo, pausar primero
        if self.is_playing and not self.is_paused:
            self.is_paused = True
            self.btn_play.config(text="▶ Play")
            
        new_frame = min(self.current_frame + 1, self.total_frames - 1)
        self.seek_to_frame(new_frame)
    
    def prev_frame(self):
        """Retrocede un frame"""
        if not self.video_cap:
            return
        
        # Si está reproduciendo, pausar primero
        if self.is_playing and not self.is_paused:
            self.is_paused = True
            self.btn_play.config(text="▶ Play")
            
        new_frame = max(self.current_frame - 1, 0)
        self.seek_to_frame(new_frame)
        
    def seek_to_frame(self, frame_number):
        """Salta a un frame específico"""
        if not self.video_cap:
            return
            
        self.current_frame = frame_number
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self.show_frame()
        self.progress_var.set(frame_number)
        self.update_time_label()
        
    def on_slider_change(self, value):
        """Maneja el cambio en la barra de progreso"""
        if not self.video_cap:
            return
        
        # Permitir seek incluso durante reproducción
        was_playing = self.is_playing and not self.is_paused
        if was_playing:
            self.is_paused = True
            
        frame_number = int(float(value))
        self.seek_to_frame(frame_number)
        
        if was_playing:
            self.is_paused = False
        
    def update_time_label(self):
        """Actualiza la etiqueta de tiempo"""
        if not self.video_cap or self.fps == 0:
            return
            
        current_seconds = self.current_frame / self.fps
        total_seconds = self.total_frames / self.fps
        
        current_time = self.format_time(current_seconds)
        total_time = self.format_time(total_seconds)
        
        self.time_label.config(text=f"{current_time} / {total_time}")
        self.frame_label.config(text=f"Frame: {self.current_frame} / {self.total_frames - 1}")
        
    @staticmethod
    def format_time(seconds):
        """Formatea segundos a MM:SS"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"
        
    def on_closing(self):
        """Maneja el cierre de la ventana"""
        self.is_playing = False
        if self.video_cap:
            self.video_cap.release()
        cv2.destroyAllWindows()
        self.root.destroy()
    
    # ========================================
    # Métodos para análisis de frames
    # ========================================
    
    def get_current_frame(self):
        """Obtiene el frame actual como array numpy (BGR)"""
        if not self.video_cap:
            return None
        
        # Guardar posición actual
        current_pos = self.video_cap.get(cv2.CAP_PROP_POS_FRAMES)
        
        # Ir al frame deseado
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.video_cap.read()
        
        # Restaurar posición
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)
        
        return frame if ret else None
    
    def get_frame_at(self, frame_number):
        """Obtiene un frame específico como array numpy (BGR)"""
        if not self.video_cap or frame_number < 0 or frame_number >= self.total_frames:
            return None
        
        # Guardar posición actual
        current_pos = self.video_cap.get(cv2.CAP_PROP_POS_FRAMES)
        
        # Ir al frame deseado
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.video_cap.read()
        
        # Restaurar posición
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)
        
        return frame if ret else None
    
    def get_video_info(self):
        """Obtiene información del video cargado"""
        if not self.video_cap:
            return None
        
        return {
            'path': self.video_path,
            'total_frames': self.total_frames,
            'fps': self.fps,
            'current_frame': self.current_frame,
            'width': int(self.video_cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(self.video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'codec': int(self.video_cap.get(cv2.CAP_PROP_FOURCC)),
            'duration': self.total_frames / self.fps if self.fps > 0 else 0
        }
    
    def export_current_frame(self, output_path=None):
        """Exporta el frame actual como imagen"""
        frame = self.get_current_frame()
        if frame is None:
            return False
        
        if output_path is None:
            from tkinter import filedialog
            output_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("JPEG files", "*.jpg"),
                    ("All files", "*.*")
                ]
            )
        
        if output_path:
            cv2.imwrite(output_path, frame)
            return True
        return False


def main():
    root = tk.Tk()
    player = VideoPlayer(root)
    root.protocol("WM_DELETE_WINDOW", player.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
