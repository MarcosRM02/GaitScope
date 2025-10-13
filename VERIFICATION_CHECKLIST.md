# Checklist de Verificación - Integración del Heatmap

Use este checklist para validar que la integración del heatmap funciona correctamente.

## ☐ Pre-requisitos

- [ ] Python 3.8+ instalado
- [ ] Dependencias instaladas (PyQt5, NumPy, OpenCV, Pandas, PyQtGraph)
- [ ] Proyecto Heatmap_Project presente en el directorio raíz
- [ ] Video Gait Analyzer funciona sin errores

## ☐ Validación de Instalación

### Test Automatizado

```bash
cd /home/marcos/Escritorio/Trabajo/Visualizador_Videos
python test_heatmap_integration.py
```

- [ ] Test 1: Heatmap_Project disponible - PASS
- [ ] Test 2: Imports funcionan - PASS
- [ ] Test 3: HeatmapAdapter se instancia - PASS
- [ ] Test 4: HeatmapWidget se instancia - PASS
- [ ] Test 5: Carga de datos funciona - PASS

**Resultado esperado**: `✓ 5/5 tests pasados`

Si algún test falla, revisar mensajes de error en consola.

## ☐ Verificación Visual

### Iniciar Aplicación

```bash
python -m video_gait_analyzer.main
```

- [ ] Aplicación se abre sin errores
- [ ] Ventana principal visible
- [ ] Todos los paneles presentes (video, plots, gaitrite, heatmap)

### Layout del Heatmap

- [ ] Panel de heatmap visible en sección inferior derecha
- [ ] Label "Heatmap: Ready" presente
- [ ] Controles visibles:
  - [ ] Botón "▶ Play"
  - [ ] Label "FPS:"
  - [ ] Spinbox con valor 64
  - [ ] Checkbox "Sync with video"
- [ ] Widget de display (fondo gris) presente

## ☐ Carga de Datos

### Seleccionar Dataset

- [ ] Dropdown de datasets funciona
- [ ] Seleccionar un dataset con datos de heatmap (ej: P1/FP)
- [ ] Click "Load Dataset"

### Verificar Carga

- [ ] Consola muestra: `[HeatmapUtils] Loaded X left coordinates`
- [ ] Consola muestra: `[HeatmapUtils] Loaded Y left frames`
- [ ] Label actualizado: "Heatmap: XXX frames loaded"
- [ ] Botón "▶ Play" habilitado
- [ ] Checkbox "Sync with video" habilitado

**Si no carga**:

- Verificar que el directorio contiene L.csv, R.csv, leftPoints.json, rightPoints.json
- Revisar logs de consola para errores

## ☐ Renderizado del Heatmap

### Iniciar Animación

- [ ] Click botón "▶ Play" del heatmap
- [ ] Botón cambia a "⏸ Pause"
- [ ] Widget de heatmap muestra animación

### Verificar Visual

- [ ] Dos heatmaps visibles (izquierdo y derecho)
- [ ] Colores tipo "jet" (azul→verde→amarillo→rojo)
- [ ] Barra de color (colorbar) visible a la derecha
- [ ] Puntos rosas (COP) visibles y móviles
- [ ] Estelas de puntos rosas (trails) visibles
- [ ] Índices de sensores dibujados sobre heatmaps
- [ ] Contador de frame visible (ej: "1/500")
- [ ] Contador de tiempo visible (ej: "00:00.0")

### Calidad Visual

- [ ] Animación suave (sin saltos)
- [ ] Colores vibrantes e idénticos al Heatmap_Project standalone
- [ ] Sin distorsión de aspect ratio
- [ ] Escalado suave al redimensionar ventana

## ☐ Controles del Heatmap

### Play/Pause

- [ ] Click "⏸ Pause" → animación se detiene
- [ ] Click "▶ Play" → animación se reanuda
- [ ] Frame actual se mantiene al pausar

### Control de FPS

- [ ] Cambiar spinbox a 30 → animación más lenta
- [ ] Cambiar spinbox a 120 → animación más rápida
- [ ] Cambio de velocidad es inmediato
- [ ] Label muestra FPS real (ej: "Heatmap: 29.8 FPS")

### Sincronización con Video

- [ ] Cargar video (si disponible en dataset)
- [ ] Activar checkbox "Sync with video"
- [ ] Click "▶ Play" del video
- [ ] Heatmap avanza sincronizado con video
- [ ] Pausar video → heatmap también se detiene
- [ ] Seek video (arrastar slider) → heatmap salta al frame correspondiente

## ☐ Rendimiento

### CPU y Memoria

- [ ] Uso de CPU <20% durante reproducción (monitorear con `top` o `htop`)
- [ ] Sin lag en UI (botones responden inmediatamente)
- [ ] Video + Heatmap simultáneos sin congelación

### Test de Estrés

- [ ] Heatmap a 120 Hz + Video a 30 FPS simultáneos
- [ ] UI permanece responsive
- [ ] Sin mensajes de error en consola
- [ ] Cerrar aplicación → sin procesos huérfanos

## ☐ Limpieza de Recursos

### Cierre Normal

- [ ] Click X de la ventana
- [ ] Aplicación se cierra sin error
- [ ] Consola muestra: `[VideoPlayer] Closing window...`
- [ ] Consola muestra: `[HeatmapAdapter] Thread stopped`

### Verificar Procesos

```bash
ps aux | grep python
```

- [ ] No quedan procesos de `video_gait_analyzer` o `heatmap`

### Ciclo de Vida

- [ ] Abrir aplicación
- [ ] Cargar dataset
- [ ] Iniciar heatmap
- [ ] Cerrar aplicación
- [ ] Repetir 3 veces sin errores

## ☐ Casos de Borde

### Dataset Sin Heatmap

- [ ] Cargar dataset sin L.csv/R.csv
- [ ] Aplicación no crashea
- [ ] Label muestra: "Heatmap: No data"
- [ ] Botones deshabilitados

### Dataset Parcial

- [ ] Dataset con solo L.csv (sin R.csv)
- [ ] Heatmap muestra solo pie izquierdo
- [ ] Pie derecho en blanco
- [ ] Sin errores en consola

### Redimensionamiento Extremo

- [ ] Minimizar ventana al mínimo
- [ ] Heatmap se escala correctamente
- [ ] Maximizar ventana
- [ ] Heatmap se expande sin distorsión

## ☐ Integración con Otros Componentes

### Video

- [ ] Reproducir video + heatmap independientes → funciona
- [ ] Sincronizar heatmap con video → funciona
- [ ] Cambiar velocidad de video → no afecta heatmap (modo independiente)

### Plots CSV

- [ ] Plots CSV se muestran correctamente junto al heatmap
- [ ] Cursor amarillo funciona
- [ ] Heatmap no interfiere con plots

### GaitRite

- [ ] Plot GaitRite se muestra en sidebar derecha
- [ ] No hay conflictos con heatmap

## ☐ Logs y Depuración

### Mensajes Esperados en Consola

Durante inicio:

```
[HeatmapAdapter] Initialized
[VideoPlayer] Initialized
```

Durante carga de datos:

```
[HeatmapUtils] Loaded X left coordinates
[HeatmapUtils] Loaded Y left frames
[VideoPlayer] Heatmap data loaded: Z frames
```

Durante reproducción:

```
[HeatmapWorker] Started
```

Durante cierre:

```
[VideoPlayer] Closing window...
[HeatmapAdapter] Thread stopped
```

### Sin Errores

- [ ] No hay tracebacks en consola
- [ ] No hay mensajes de "Error" o "Warning" críticos
- [ ] Logs son informativos, no alarmantes

## ☐ Comparación con Standalone

### Test Visual Lado a Lado

1. Ejecutar Heatmap_Project standalone:

```bash
cd Heatmap_Project
python main.py
```

2. Ejecutar Video Gait Analyzer con mismo dataset

3. Comparar visualmente:

- [ ] Colormaps idénticos
- [ ] COP (puntos rosas) en mismas posiciones
- [ ] Trails tienen misma longitud y forma
- [ ] Índices de sensores en mismas posiciones
- [ ] Timing perceptual similar (no hay desfase notable)

## ☐ Documentación

- [ ] README.md menciona integración del heatmap
- [ ] HEATMAP_INTEGRATION.md presente y legible
- [ ] HEATMAP_USAGE.md presente con instrucciones claras
- [ ] IMPLEMENTATION_SUMMARY.md documenta completitud

## Resultados

### Puntuación

- **Tests pasados**: \_\_\_ / 100
- **Errores encontrados**: \_\_\_
- **Rendimiento**: [ ] Óptimo [ ] Aceptable [ ] Mejorable

### Notas

```
(Espacio para notas sobre problemas encontrados o comportamientos inesperados)






```

### Estado Final

- [ ] ✅ **APROBADO** - Todo funciona correctamente
- [ ] ⚠️ **APROBADO CON OBSERVACIONES** - Funciona pero hay issues menores
- [ ] ❌ **RECHAZADO** - Problemas críticos que impiden uso

---

**Fecha de verificación**: ******\_\_\_******  
**Verificado por**: ******\_\_\_******  
**Firma**: ******\_\_\_******
