import av
import cv2
import threading
import queue
import time

VIDEO_PATH = "recorded_video.mp4"
BUFFER_SIZE = 60
SEEK_SECONDS = 5

frame_queue = queue.Queue(maxsize=BUFFER_SIZE)
stop_flag = threading.Event()
paused = threading.Event()

# -------------------------------
# Hilo de decodificación
# -------------------------------
def decode_frames(container, stream, queue, stop_flag):
    for frame in container.decode(stream):
        if stop_flag.is_set():
            break
        queue.put(frame)
    stop_flag.set()

# -------------------------------
# Seek
# -------------------------------
def seek(container, stream, target_seconds):
    container.seek(int(target_seconds * av.time_base), any_frame=False, stream=stream)
    while not frame_queue.empty():
        frame_queue.get()
    return container.decode(stream)

# -------------------------------
# Abrir video
# -------------------------------
container = av.open(VIDEO_PATH)
video_stream = container.streams.video[0]

# Crear ventana redimensionable
window_name = "PyAV Reproductor"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
# Ajustar al tamaño de la pantalla (80% del tamaño)
screen_width = 1920  # Ajusta según tu resolución
screen_height = 1080  # Ajusta según tu resolución
cv2.resizeWindow(window_name, int(screen_width * 0.8), int(screen_height * 0.8))

# iniciar hilo decodificador
decode_thread = threading.Thread(target=decode_frames, args=(container, video_stream, frame_queue, stop_flag))
decode_thread.start()

print("Controles: SPACE pause/play, LEFT/RIGHT seek, ESC/q salir")

current_time = 0.0
last_display_time = time.time()

# -------------------------------
# Loop de reproducción
# -------------------------------
while not stop_flag.is_set():
    if paused.is_set():
        key = cv2.waitKey(100) & 0xFF
        if key == 32:  # SPACE
            paused.clear()
        elif key in [27, ord('q')]:
            stop_flag.set()
        continue

    try:
        frame = frame_queue.get(timeout=1)
    except queue.Empty:
        break

    img = frame.to_ndarray(format="bgr24")
    cv2.imshow(window_name, img)

    # Calcular delay basado en timestamps
    if frame.time is not None:
        target_display_time = last_display_time + (frame.time - current_time)
        now = time.time()
        sleep_time = max(0, target_display_time - now)
        time.sleep(sleep_time)
        last_display_time = time.time()
        current_time = frame.time
    else:
        # Si no hay timestamp, usar FPS promedio
        fps = float(video_stream.average_rate) if video_stream.average_rate else 30.0
        time.sleep(1.0/fps)
        current_time += 1.0/fps
        last_display_time = time.time()

    # Capturar teclas
    key = cv2.waitKey(1) & 0xFF
    if key == 32:  # SPACE
        paused.set()
    elif key == 27 or key == ord('q'):
        stop_flag.set()
    elif key == 81:  # flecha izquierda
        new_time = max(0, current_time - SEEK_SECONDS)
        frame_queue_iter = seek(container, video_stream, new_time)
        current_time = new_time
        last_display_time = time.time()
    elif key == 83:  # flecha derecha
        new_time = current_time + SEEK_SECONDS
        frame_queue_iter = seek(container, video_stream, new_time)
        current_time = new_time
        last_display_time = time.time()

# -------------------------------
# Cerrar todo
# -------------------------------
stop_flag.set()
decode_thread.join()
cv2.destroyAllWindows()
container.close()
