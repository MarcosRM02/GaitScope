# Guía de Uso - Integración del Heatmap

## Inicio Rápido

### 1. Verificar la Instalación

Ejecutar el script de validación:

```bash
cd /home/marcos/Escritorio/Trabajo/Visualizador_Videos
python test_heatmap_integration.py
```

Todos los tests deberían pasar (✓ PASS).

### 2. Lanzar la Aplicación

```bash
python -m video_gait_analyzer.main
```

O si está instalado el paquete:

```bash
video-gait-analyzer
```

### 3. Cargar un Dataset con Heatmap

1. **Seleccionar Dataset**: Usar el dropdown para elegir un participante/sesión
2. **Hacer clic en "Load Dataset"**: Carga automáticamente:

   - Video (si existe)
   - Datos CSV de sensores
   - Datos GaitRite
   - **Datos de Heatmap** (nuevo)

3. **Verificar Carga**: El panel de heatmap (derecha inferior) debe mostrar:
   ```
   Heatmap: XXX frames loaded
   ```

### 4. Controlar el Heatmap

#### Botones Principales

- **▶ Play / ⏸ Pause**: Iniciar/detener animación del heatmap
- **FPS Spinner**: Ajustar velocidad (1-120 Hz)
- **Sync with video**: Sincronizar con reproducción de video

#### Modos de Operación

**Modo Independiente (por defecto)**

- Heatmap corre a su propio FPS
- No se sincroniza con el video
- Ideal para observación continua

**Modo Sincronizado**

- Activar checkbox "Sync with video"
- Heatmap sigue el tiempo del video
- Útil para correlacionar eventos visuales

### 5. Reproducción de Video + Heatmap

**Reproducir ambos simultáneamente:**

1. Hacer clic en "▶ Play" del video (botones principales)
2. Hacer clic en "▶ Play" del heatmap (panel heatmap)
3. Ambos corren independientemente

**Sincronizar:**

1. Activar "Sync with video"
2. Reproducir el video
3. El heatmap avanza automáticamente con el video

## Estructura de Datos Requerida

Para que el heatmap funcione, el directorio del dataset debe contener:

```
session_directory/
├── L.csv                    # Secuencia de presiones pie izquierdo
├── R.csv                    # Secuencia de presiones pie derecho
├── video_anonymized.mp4     # (opcional) Video
└── gaitrite_footprints.csv  # (opcional) Datos GaitRite
```

**Nota**: Las coordenadas de sensores (leftPoints.json, rightPoints.json) se cargan automáticamente desde `video_gait_analyzer/in/` al iniciar la aplicación, ya que son las mismas para todos los participantes.

### Formato de Archivos

**L.csv / R.csv** (CSV sin header):

```
123,456,789,...    # Frame 1: valores de presión por sensor
145,478,801,...    # Frame 2
...
```

**leftPoints.json / rightPoints.json**:

```json
[
  [10.5, 20.3],    # Sensor 1: [x, y]
  [15.2, 25.7],    # Sensor 2
  ...
]
```

O formato con claves:

```json
{
  "coordinates": [[10.5, 20.3], [15.2, 25.7], ...]
}
```

## Atajos de Teclado

### Controles de Video

- **Space**: Play/Pause video
- **→**: Frame siguiente
- **←**: Frame anterior

### Controles de Heatmap

- No hay atajos específicos (usar botones)
- Se pueden añadir fácilmente si se requiere

## Solución de Problemas

### El heatmap no aparece

**Causa**: No se encontraron datos de heatmap en el directorio

**Solución**:

1. Verificar que el directorio contiene L.csv, R.csv y archivos JSON
2. Revisar logs en consola para errores de carga
3. Ejecutar `test_heatmap_integration.py` para diagnosticar

### El heatmap se ve distorsionado

**Causa**: Tamaño de ventana demasiado pequeño

**Solución**:

1. Maximizar la ventana
2. El widget mantiene aspect ratio automáticamente
3. Redimensionar panel si es necesario

### La animación va muy lenta/rápida

**Causa**: FPS incorrecto

**Solución**:

1. Ajustar el spinner de FPS (típicamente 30-60 Hz)
2. Verificar que no hay lag del sistema
3. Reducir FPS si CPU está saturada

### El heatmap no sincroniza con el video

**Causa**: Checkbox no activado o mapeo incorrecto

**Solución**:

1. Activar "Sync with video"
2. Si hay desfase, puede ser por diferencia de duración
3. El mapeo es proporcional (lineal)

### La aplicación se congela

**Causa**: Posible deadlock o thread bloqueado

**Solución**:

1. Cerrar y reiniciar aplicación
2. Verificar logs de consola
3. Reportar error con traceback

### Error al cerrar la aplicación

**Causa**: Threads del heatmap no se detuvieron

**Solución**:

1. Normalmente el closeEvent los detiene automáticamente
2. Si quedan procesos huérfanos, matar con `pkill -f video-gait-analyzer`
3. Revisar que HeatmapAdapter.stop() se llama correctamente

## Ajustes Avanzados

### Cambiar Parámetros del Heatmap

Actualmente los parámetros están fijos en HeatmapAdapter:

```python
self.params = {
    'wFinal': 175,        # Ancho de heatmap individual
    'hFinal': 520,        # Alto de heatmap individual
    'gridW': 13,          # Grilla de interpolación ancho
    'gridH': 39,          # Grilla de interpolación alto
    'radius': 22,         # Radio de kernel gaussiano
    'smoothness': 1.8,    # Suavizado del kernel
    'margin': 50,         # Margen de la imagen
    'legendWidth': 80,    # Ancho de la barra de color
    'trailLength': 10,    # Longitud de estela de COP
    'fps': 64             # FPS por defecto
}
```

Para modificarlos:

1. Editar `video_gait_analyzer/core/heatmap_adapter.py`
2. Cambiar valores en `__init__`
3. O llamar `adapter.update_params(radius=30, smoothness=2.0)` desde código

### Personalizar Colormap

El colormap está definido en `Heatmap_Project/heatmap.py`:

1. Localizar función `render_heatmap_from_flatZ`
2. Modificar `cv2.applyColorMap(..., cv2.COLORMAP_JET)`
3. Opciones: COLORMAP_HOT, COLORMAP_RAINBOW, COLORMAP_VIRIDIS, etc.

### Añadir Controles UI

Para exponer parámetros en la UI:

1. Añadir QSpinBox/QSlider en `_build_heatmap_controls()`
2. Conectar a callback que llame `adapter.update_params(**kwargs)`
3. El adapter recreará el Animator con nuevos parámetros

## Rendimiento

### Métricas Típicas

- **FPS del Heatmap**: 30-60 Hz en hardware moderno
- **Latencia**: <50ms entre frame y display
- **Uso de CPU**: ~5-10% adicional (depende de FPS)
- **Memoria**: ~15-20 MB adicionales (buffer + frame actual)

### Optimización

Si hay problemas de rendimiento:

1. **Reducir FPS**: Bajar a 30 Hz o menos
2. **Reducir buffer**: Editar `PreRenderer(capacity=4)` en heatmap_adapter.py
3. **Simplificar rendering**: Reducir `gridW/gridH` para interpolación más rápida

## Ejemplos de Uso

### Caso 1: Análisis de Marcha Básico

```
1. Cargar dataset del sujeto
2. Reproducir video a velocidad normal (1.0x)
3. Activar heatmap sincronizado
4. Observar correlación entre video y presión plantar
```

### Caso 2: Análisis de COP

```
1. Cargar dataset
2. Poner heatmap en modo independiente
3. Ajustar FPS a 15 Hz (más lento)
4. Observar trayectoria del Centro de Presión (puntos rosas)
```

### Caso 3: Comparación de Condiciones

```
1. Cargar dataset FP (fast pace)
2. Observar y anotar patrones
3. Cargar dataset SP (slow pace)
4. Comparar diferencias visuales
```

## Registro de Cambios

### Versión Inicial (2025-10-13)

**Características implementadas:**

- ✓ HeatmapAdapter con QThread
- ✓ HeatmapWidget con auto-scaling
- ✓ Controles de Play/Pause/FPS
- ✓ Sincronización opcional con video
- ✓ Carga automática de datos
- ✓ PreRenderer optimizado
- ✓ Gestión de recursos y cleanup

**Limitaciones conocidas:**

- Mapeo temporal lineal (no timestamps exactos)
- Parámetros de rendering no ajustables desde UI
- Panel no redimensionable individualmente

## Recursos Adicionales

- **Documentación Técnica**: Ver `HEATMAP_INTEGRATION.md`
- **Arquitectura**: Ver `ARCHITECTURE.md`
- **Resumen del Proyecto**: Ver `PROJECT_SUMMARY.md`
- **Instalación**: Ver `INSTALL.md`

## Contacto

Para problemas o sugerencias sobre el heatmap, consultar los logs de consola con prefijos:

- `[HeatmapAdapter]`
- `[HeatmapWidget]`
- `[HeatmapWorker]`
- `[HeatmapUtils]`
