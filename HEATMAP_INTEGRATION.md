# Integración del Heatmap en Video Gait Analyzer

## Descripción General

El proyec### Gestión de Datos

- ✅ Reutiliza datos CSV ya cargados (L.csv, R.csv)
- ✅ Coordenadas de sensores cargadas una vez al inicio (video_gait_analyzer/in/)
- ✅ Sin carga duplicada de archivos
- ✅ Rendimiento optimizadoatmap_Project ha sido integrado exitosamente en el Video Gait Analyzer, permitiendo visualizar animaciones de mapas de calor de presión plantar junto con el video y los gráficos de análisis de marcha.

## Arquitectura de la Integración

### Componentes Principales

1. **HeatmapAdapter** (`video_gait_analyzer/core/heatmap_adapter.py`)

   - Adaptador Qt que encapsula la lógica de Heatmap_Project
   - Gestiona el Animator, Worker y PreRenderer en un QThread independiente
   - Expone señales Qt para comunicación thread-safe con la GUI
   - API: `start()`, `stop()`, `pause()`, `resume()`, `set_rate()`, `set_data()`, `seek()`

2. **HeatmapWidget** (`video_gait_analyzer/widgets/heatmap_widget.py`)

   - Widget Qt para mostrar frames del heatmap
   - Convierte arrays numpy BGR a QPixmap con escalado automático
   - Mantiene aspect ratio y soporta redimensionamiento dinámico

3. **HeatmapUtils** (`video_gait_analyzer/utils/heatmap_utils.py`)
   - Funciones de utilidad para cargar datos de heatmap
   - Lee coordenadas de sensores desde JSON
   - Lee secuencias de presión desde CSV
   - Busca y valida archivos de datos automáticamente

### Flujo de Datos

```
Heatmap_Project/
├── animator.py          → Renderiza frames (sin cambios)
├── prerenderer.py       → Buffer de pre-renderizado (sin cambios)
├── worker.py            → No usado directamente
└── heatmap.py           → Funciones de rendering (sin cambios)
                             ↓
                      HeatmapAdapter
                    (Qt Thread + Señales)
                             ↓
                      frame_ready signal
                             ↓
                      HeatmapWidget
                   (Display en UI principal)
```

### Integración en VideoPlayer

El VideoPlayer coordina todos los componentes:

```
VideoPlayer
├── Video Display (izquierda superior)
├── Plots Section (izquierda inferior)
│   ├── CSV Plots (izquierda)
│   └── Heatmap Widget (derecha) ← NUEVO
├── GaitRite Plot (derecha)
└── Controls
    ├── Video Controls
    └── Heatmap Controls ← NUEVO
        ├── Play/Pause
        ├── FPS Control (1-120 Hz)
        └── Sync with Video
```

## Características Implementadas

### 1. Renderizado Independiente

- ✅ El heatmap corre en un QThread separado
- ✅ Frame rate independiente del video (configurable 1-120 Hz)
- ✅ No bloquea la UI ni la reproducción de video
- ✅ Usa PreRenderer para optimizar buffer de frames

### 2. Controles de Usuario

- ✅ Botón Play/Pause independiente
- ✅ Control de FPS con QSpinBox
- ✅ Checkbox para sincronizar con video
- ✅ Información de FPS en tiempo real

### 3. Sincronización con Video (Opcional)

- ✅ Mapeo proporcional entre frames de video y heatmap
- ✅ Actualización automática al cambiar frame de video
- ✅ Se puede activar/desactivar en tiempo real

### 4. Gestión de Datos

- ✅ Carga automática desde directorio de dataset
- ✅ Soporta archivos L.csv, R.csv, leftPoints.json, rightPoints.json
- ✅ Validación de datos antes de cargar
- ✅ Mensajes de error informativos

### 5. Optimizaciones Preservadas

- ✅ Pre-rendering con buffer circular (8 frames)
- ✅ Vectorización numpy (del Animator original)
- ✅ Kernels pre-computados
- ✅ Renderizado eficiente BGR->RGB->QImage

## Uso

### Cargar Dataset con Heatmap

1. Seleccionar un dataset que contenga:

   - `L.csv`: Secuencia de presiones pie izquierdo
   - `R.csv`: Secuencia de presiones pie derecho
   - `leftPoints.json`: Coordenadas de sensores izquierdo
   - `rightPoints.json`: Coordenadas de sensores derecho

2. Hacer clic en "Load Dataset"

   - Se cargan automáticamente CSV, GaitRite y Heatmap

3. El panel de heatmap mostrará "X frames loaded"

### Controlar Animación

- **Play/Pause**: Inicia/detiene la animación del heatmap
- **FPS**: Ajusta la velocidad de reproducción (1-120 Hz)
- **Sync with video**: Acopla el heatmap al tiempo del video

### Modo Sincronizado

Cuando está activado "Sync with video":

- El heatmap salta al frame correspondiente al video actual
- Se actualiza automáticamente durante reproducción
- Útil para correlacionar eventos visuales

### Modo Independiente (por defecto)

Cuando NO está sincronizado:

- El heatmap corre a su propio FPS
- Cicla continuamente los frames
- Útil para análisis continuo

## Estructura de Archivos

### Nuevos Archivos Creados

```
video_gait_analyzer/
├── core/
│   └── heatmap_adapter.py        # Adaptador Qt para Heatmap_Project
├── widgets/
│   └── heatmap_widget.py         # Widget de visualización
└── utils/
    └── heatmap_utils.py          # Utilidades de carga de datos
```

### Archivos Modificados

```
video_gait_analyzer/
├── core/
│   └── video_player.py           # Integración en UI principal
├── widgets/
│   └── __init__.py               # Export HeatmapWidget
└── utils/
    └── __init__.py               # Export heatmap_utils
```

### Archivos de Heatmap_Project (sin cambios)

```
Heatmap_Project/
├── animator.py                   # Lógica de renderizado
├── prerenderer.py                # Buffer de pre-rendering
├── heatmap.py                    # Funciones de rendering
├── io_utils.py                   # I/O de datos
└── gui.py                        # GUI standalone (no usado)
```

## Pruebas

### Validación Manual

Para validar la integración:

1. **Equivalencia Visual**

   - Comparar animación integrada vs standalone
   - Verificar colormaps, trails, COP, índices
   - Confirmar timing perceptual idéntico

2. **Rendimiento**

   - Reproducir video a 30 FPS + heatmap a 60 Hz simultáneamente
   - Verificar que no hay lag en la UI
   - Monitorear uso de CPU/memoria

3. **Sincronización**

   - Activar sync mode
   - Avanzar/retroceder video frame por frame
   - Verificar que heatmap sigue correctamente

4. **Limpieza de Recursos**
   - Cargar dataset, cerrar aplicación
   - Verificar que no quedan threads huérfanos
   - Repetir varias veces

### Datasets de Prueba

Usar los datos en:

```
data/P*/FP/          # Datos de sujetos con heatmap
data/P*/SP/
data/P*/NP/
```

Cada directorio debe contener L.csv, R.csv y archivos JSON de coordenadas.

## Limitaciones Conocidas

1. **Mapeo de Frames**

   - La sincronización asume mapeo lineal proporcional
   - No considera timestamps exactos
   - Puede haber pequeños desfases en videos de duración variable

2. **Tamaño de Widget**

   - El heatmap ocupa 1/3 del ancho de la sección de plots
   - No es redimensionable por el usuario (solo con la ventana)

3. **Datos Requeridos**
   - Necesita al menos un pie (L o R) con datos
   - No maneja casos con sensores faltantes elegantemente

## Mejoras Futuras

1. **Mapeo Temporal Preciso**

   - Usar timestamps de CSV y video para sincronización exacta
   - Interpolar frames si las frecuencias difieren

2. **Controles Avanzados**

   - Ajuste de colormap en runtime
   - Control de smoothness/radius
   - Export de frames individuales

3. **Panel Flotante**

   - Opción de mostrar heatmap en ventana separada
   - Fullscreen mode para presentaciones

4. **Multi-Dataset**
   - Comparación de heatmaps de múltiples sujetos
   - Overlay de heatmaps

## Notas Técnicas

### Thread Safety

- Toda comunicación entre threads usa Qt signals/slots
- El adapter invoca métodos del worker via `QMetaObject.invokeMethod`
- Los frames se emiten como numpy arrays (copy-on-write es seguro)

### Gestión de Memoria

- PreRenderer mantiene buffer de 8 frames (~10 MB típico)
- Frames se evictan automáticamente fuera de ventana
- Widget guarda solo el frame actual (~1.2 MB)

### Compatibilidad Qt

- Usa PyQt5 (igual que el resto del proyecto)
- Heatmap_Project usa PySide6 internamente (no conflicto gracias al adapter)
- Las señales se definen con `QtCore.pyqtSignal`

## Contacto y Soporte

Para problemas o preguntas sobre la integración del heatmap, consultar:

- `ARCHITECTURE.md` para visión general del proyecto
- `PROJECT_SUMMARY.md` para resumen de funcionalidades
- Logs de consola con prefijo `[HeatmapAdapter]`, `[HeatmapWidget]`, `[HeatmapWorker]`
