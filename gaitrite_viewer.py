"""
GaitRite Viewer component for GaitScope application.
"""

import numpy as np
import pandas as pd
import pyqtgraph as pg
import traceback
from pathlib import Path
from PyQt5 import QtWidgets, QtCore

from ..utils import CARPET_WIDTH_CM, CARPET_LENGTH_CM


class GaitRiteViewer(QtWidgets.QWidget):
    """Widget para visualizar datos de GaitRite con pyqtgraph"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gaitrite_tests_df = None
        self.gaitrite_testsets_df = None
        self.current_participant = None
        self.current_prueba = None
        self.current_intento = None
        
        # Mapeo para numeración secuencial
        self.sequential_to_gait_id = {}
        self.gait_id_to_sequential = {}
        
        self.init_ui()
    
    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Solo el título, eliminamos toda la información del dataset
        title = QtWidgets.QLabel("🚶 GaitRite Analysis")
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px; color: #2c3e50;")
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)
        
        # Plot de GaitRite ocupa todo el espacio disponible
        self.gaitrite_plot = pg.PlotWidget()
        self.gaitrite_plot.setBackground('white')
        self.gaitrite_plot.setMinimumSize(400, 700)  # Más alto para mejor visualización
        
        # Vista completamente fija sin interacción
        self.gaitrite_plot.setMouseEnabled(x=False, y=False)
        self.gaitrite_plot.setMenuEnabled(False)
        self.gaitrite_plot.hideButtons()  # Ocultar botones de auto-scale
        
        # Configurar etiquetas y grid
        plot_item = self.gaitrite_plot.getPlotItem()
        plot_item.setLabel('left', 'Longitud (cm)', **{'color': '#2c3e50', 'font-size': '10pt'})
        plot_item.setLabel('bottom', 'Ancho (cm)', **{'color': '#2c3e50', 'font-size': '10pt'})
        plot_item.showGrid(True, True, alpha=0.3)
        
        # Configurar para que mantenga el aspect ratio pero permita ver todo
        plot_item.setAspectLocked(False)  # No bloquear aspect ratio para evitar cortes
        
        layout.addWidget(self.gaitrite_plot)
        
        # Leyenda compacta
        legend_label = QtWidgets.QLabel("🔴 Pie Izquierdo  🔵 Pie Derecho  ⚫ Trayectoria")
        legend_label.setStyleSheet("font-size: 10px; color: #7f8c8d; padding: 3px;")
        legend_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(legend_label)
        
        # Inicializar plot vacío
        self.show_empty_plot()
    
    def _set_plot_aspect_locked(self, plot_widget, ratio):
        """Bloquea el aspect ratio del plot"""
        try:
            plot_item = plot_widget.getPlotItem()
            if plot_item:
                plot_item.setAspectLocked(True, ratio=ratio)
        except Exception as e:
            print(f"DEBUG: Error setting aspect ratio: {e}")
    
    def show_empty_plot(self):
        """Muestra un plot vacío con el fondo de la alfombra"""
        self.gaitrite_plot.clear()
        self._draw_carpet_background()
    
    def _draw_carpet_background(self, show_text=True):
        """Dibuja el rectángulo de la alfombra."""
        bg_x = [0, CARPET_WIDTH_CM, CARPET_WIDTH_CM, 0, 0]
        bg_y = [0, 0, CARPET_LENGTH_CM, CARPET_LENGTH_CM, 0]
        self.gaitrite_plot.plot(
            bg_x, bg_y,
            pen=pg.mkPen('gray', width=2),
            fillLevel=0,
            brush=pg.mkBrush(240, 240, 240, 100)  # Fondo gris claro
        )
        
        # Solo mostrar texto cuando no hay datos (plot vacío)
        if show_text:
            text_item = pg.TextItem(
                f"🚶 Alfombra GaitRite\n{CARPET_WIDTH_CM} × {CARPET_LENGTH_CM} cm",
                anchor=(0.5, 0.5),
                color='#7F8C8D',
                fill=pg.mkBrush(255, 255, 255, 180),
                border=pg.mkPen('#BDC3C7', width=1)
            )
            text_item.setPos(CARPET_WIDTH_CM/2, CARPET_LENGTH_CM/2)
            self.gaitrite_plot.addItem(text_item)
    
    def load_gaitrite_data(self, participant, prueba, intento):
        """Carga datos de GaitRite siguiendo la lógica del archivo de referencia"""
        try:
            self.current_participant = participant
            self.current_prueba = prueba
            self.current_intento = intento
            
            # Buscar archivos GaitRite en la carpeta específica del intento - COMO EN EL ARCHIVO DE REFERENCIA
            intent_path = Path("data") / participant / prueba / intento
            
            # Buscar archivo gaitrite_test.csv en la carpeta del intento
            gaitrite_file = intent_path / "gaitrite_test.csv"
            
            if not gaitrite_file.exists():
                # Fallback: buscar en el directorio raíz
                gaitrite_file = Path("gaitrite_test.csv")
                if not gaitrite_file.exists():
                    self.gaitrite_tests_df = None
                    self.show_empty_plot()
                    return
            
            # Cargar datos usando el mismo método que el archivo de referencia
            print(f"DEBUG: Cargando archivo GaitRite desde: {gaitrite_file}")
            self.gaitrite_tests_df = pd.read_csv(gaitrite_file, delimiter=';')
            print(f"DEBUG: Cargado CSV de GaitRite: {len(self.gaitrite_tests_df)} registros")
            print(f"DEBUG: Columnas disponibles: {list(self.gaitrite_tests_df.columns)}")
            
            # Visualizar automáticamente sin mostrar información
            if 'Gait_Id' in self.gaitrite_tests_df.columns:
                gait_ids = self.gaitrite_tests_df['Gait_Id'].unique()
                
                # Mostrar automáticamente el primer test
                if len(gait_ids) > 0:
                    first_gait_id = sorted(gait_ids)[0]
                    print(f"DEBUG: Visualizando automáticamente Gait_Id: {first_gait_id}")
                    self.visualize_gait_test(first_gait_id)
            else:
                # Si no hay Gait_Id, visualizar todos los datos directamente
                self.visualize_direct_data()
            
            print(f"DEBUG: Datos GaitRite cargados y visualizados para {participant}/{prueba}")
            
        except Exception as e:
            print(f"DEBUG: Error cargando datos GaitRite: {e}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            self.gaitrite_tests_df = None
            self.show_empty_plot()
    
    def visualize_gait_test(self, gait_id):
        """Visualiza un test específico siguiendo EXACTAMENTE la lógica del archivo de referencia"""
        if self.gaitrite_tests_df is None:
            self.show_empty_plot()
            return
            
        print(f"DEBUG: === VISUALIZACIÓN GAIT_ID {gait_id} (ESTRATEGIA REFERENCIA) ===")
        
        # Filtrar datos para el Gait_Id seleccionado - IGUAL QUE EN EL ARCHIVO DE REFERENCIA
        selected_gait = self.gaitrite_tests_df[self.gaitrite_tests_df['Gait_Id'] == gait_id].copy()
        
        if len(selected_gait) == 0:
            print(f"DEBUG: No se encontraron datos para Gait_Id {gait_id}")
            self.show_empty_plot()
            return
            
        print(f"DEBUG: Encontradas {len(selected_gait)} huellas para Gait_Id {gait_id}")
        
        # Limpiar plot anterior y dibujar fondo SIN texto (ya que vamos a mostrar datos)
        self.gaitrite_plot.clear()
        self._draw_carpet_background(show_text=False)
        
        # INTENTAR DIBUJAR CONTORNOS DESDE CSVs DE HUELLAS (como en archivo de referencia)
        drew_contours = False
        
        # Intentar cargar y dibujar contornos precisos si existen los archivos
        try:
            # Buscar archivos de contornos de huellas en la carpeta del intento
            intent_path = Path("data") / self.current_participant / self.current_prueba / self.current_intento
            
            # Buscar archivos originales primero
            footprints_left_file = intent_path / "footprints_left.csv"
            footprints_right_file = intent_path / "footprints_right.csv"
            
            # Si no existen, buscar archivos generados
            if not footprints_left_file.exists():
                footprints_left_file = intent_path / "generated_footprints_left.csv"
            if not footprints_right_file.exists():
                footprints_right_file = intent_path / "generated_footprints_right.csv"
            
            footprints_left_df = None
            footprints_right_df = None
            
            if footprints_left_file.exists():
                try:
                    footprints_left_df = pd.read_csv(footprints_left_file)
                    print(f"DEBUG: Cargado {footprints_left_file.name}: {len(footprints_left_df)} registros")
                except:
                    # Fallback con delimiter=';' por compatibilidad
                    footprints_left_df = pd.read_csv(footprints_left_file, delimiter=';')
                    print(f"DEBUG: Cargado {footprints_left_file.name} (delimiter=;): {len(footprints_left_df)} registros")
                
            if footprints_right_file.exists():
                try:
                    footprints_right_df = pd.read_csv(footprints_right_file)
                    print(f"DEBUG: Cargado {footprints_right_file.name}: {len(footprints_right_df)} registros")
                except:
                    # Fallback con delimiter=';' por compatibilidad
                    footprints_right_df = pd.read_csv(footprints_right_file, delimiter=';') 
                    print(f"DEBUG: Cargado {footprints_right_file.name} (delimiter=;): {len(footprints_right_df)} registros")
            
            # Si no existen los archivos, intentar generarlos usando export_yarray_footprints
            if footprints_left_df is None or footprints_right_df is None:
                print("DEBUG: Archivos de contornos no encontrados, intentando generar desde Yarray...")
                footprints_left_df, footprints_right_df = self._generate_footprints_from_yarray(gait_id)
            
            # Dibuja contornos precisos de las huellas si están disponibles
            if footprints_left_df is not None or footprints_right_df is not None:
                print("DEBUG: Dibujando contornos precisos de huellas")
                
                # Primero dibujar los contornos estilizados
                for df, color_name in ((footprints_left_df, 'red'), (footprints_right_df, 'blue')):
                    if df is None or df.empty:
                        continue
                    try:
                        # Filtra por gait_id del test seleccionado
                        df_g = df[df['gait_id'] == gait_id]
                        if df_g.empty:
                            continue
                        # Agrupa por evento y dibuja polilíneas ordenadas por sample_idx
                        for ev, grp in df_g.groupby('event'):
                            grp_sorted = grp.sort_values('sample_idx')
                            if 'x_cm' in grp_sorted.columns and 'y_cm' in grp_sorted.columns:
                                # Colores más intensos y estilizados
                                if color_name == 'red':
                                    pen_color = pg.mkPen(color='#E74C3C', width=3, style=QtCore.Qt.SolidLine)
                                    brush_color = pg.mkBrush(231, 76, 60, 60)  # Rojo semi-transparente
                                else:
                                    pen_color = pg.mkPen(color='#3498DB', width=3, style=QtCore.Qt.SolidLine)
                                    brush_color = pg.mkBrush(52, 152, 219, 60)  # Azul semi-transparente
                                
                                # Dibuja el contorno con relleno
                                self.gaitrite_plot.plot(
                                    grp_sorted['x_cm'].values,
                                    grp_sorted['y_cm'].values,
                                    pen=pen_color,
                                    fillLevel=None,
                                    brush=brush_color
                                )
                                drew_contours = True
                    except Exception as e:
                        print(f"DEBUG: Error dibujando contornos {color_name}: {e}")
                        continue
                
                # Dibujar trayectoria también cuando hay contornos
                if drew_contours:
                    try:
                        print("DEBUG: Dibujando trayectoria con contornos")
                        traj_x = (((selected_gait['Ybottom'] + selected_gait['Ytop']) / 2) * 1.27).values
                        traj_y = (((selected_gait['Xback'] + selected_gait['Xfront']) / 2) * 1.27).values
                        
                        # Trayectoria más estilizada
                        self.gaitrite_plot.plot(
                            traj_x, traj_y, 
                            pen=pg.mkPen(color='#2C3E50', width=3, style=QtCore.Qt.DashLine),
                            symbol='o', 
                            symbolSize=8, 
                            symbolBrush=pg.mkBrush('#34495E'),
                            symbolPen=pg.mkPen('#2C3E50', width=2)
                        )
                        print("DEBUG: Trayectoria estilizada dibujada con contornos")
                    except Exception as e:
                        print(f"DEBUG: Error dibujando trayectoria con contornos: {e}")
                        
        except Exception as e:
            print(f"DEBUG: Error cargando archivos de contornos: {e}")
        
        # Si no se pudieron dibujar contornos, usar FALLBACK: rectángulos y trayectoria
        if not drew_contours:
            print("DEBUG: Usando fallback - rectángulos desde CSV principal")
            
            # Convierte coordenadas usando factor 1.27
            CONVERSION_FACTOR = 1.27
            footprints_drawn = 0
            for _, row in selected_gait.iterrows():
                try:
                    # Calcula rectángulo de presión
                    x = row['Ybottom'] * CONVERSION_FACTOR  
                    y = row['Xback'] * CONVERSION_FACTOR
                    width = (row['Ytop'] - row['Ybottom']) * CONVERSION_FACTOR
                    height = (row['Xfront'] - row['Xback']) * CONVERSION_FACTOR
                    
                    print(f"DEBUG: Rectángulo Event={row['Event']}, Foot={'L' if row['Foot']==0 else 'R'}")
                    print(f"      x={x:.1f}, y={y:.1f}, w={width:.1f}, h={height:.1f}")
                    
                    # Validar coordenadas
                    if pd.isna([x, y, width, height]).any() or width <= 0 or height <= 0:
                        print(f"      Saltando por coordenadas inválidas")
                        continue
                    
                    # Color según el pie (rojo=izquierdo, azul=derecho)
                    pen_color = pg.mkPen('red', width=2) if row['Foot'] == 0 else pg.mkPen('blue', width=2)
                    
                    # Dibuja rectángulo
                    rect_x = [x, x + width, x + width, x, x]
                    rect_y = [y, y, y + height, y + height, y]
                    self.gaitrite_plot.plot(rect_x, rect_y, pen=pen_color)
                    
                    footprints_drawn += 1
                    
                except Exception as e:
                    print(f"DEBUG: Error dibujando rectángulo: {e}")
                    continue

            print(f"DEBUG: Dibujados {footprints_drawn} rectángulos")
            
            # Dibujar trayectoria - EXACTAMENTE COMO EN EL ARCHIVO DE REFERENCIA
            try:
                traj_x = (((selected_gait['Ybottom'] + selected_gait['Ytop']) / 2) * 1.27).values
                traj_y = (((selected_gait['Xback'] + selected_gait['Xfront']) / 2) * 1.27).values
                self.gaitrite_plot.plot(traj_x, traj_y, pen=pg.mkPen('black', width=2))
                print("DEBUG: Trayectoria dibujada")
            except Exception as e:
                print(f"DEBUG: Error dibujando trayectoria: {e}")
        
        # Configurar vista para mostrar todo el contenido sin cortes
        self._lock_gaitrite_view()
        
        print("DEBUG: === FIN VISUALIZACIÓN SIGUIENDO ESTRATEGIA REFERENCIA ===")
    
    def _lock_gaitrite_view(self):
        """Fija la gráfica completamente al tamaño de la alfombra sin zoom."""
        try:
            self.gaitrite_plot.disableAutoRange()
            
            # Padding reducido para mayor zoom
            padding_x = CARPET_WIDTH_CM * 0.10  # 10% de margen = ~6cm cada lado
            padding_y = CARPET_LENGTH_CM * 0.08  # 8% de margen = ~39cm arriba/abajo
            
            # Vista fija con más zoom
            self.gaitrite_plot.setXRange(-padding_x, CARPET_WIDTH_CM + padding_x, padding=0)
            self.gaitrite_plot.setYRange(-padding_y, CARPET_LENGTH_CM + padding_y, padding=0)
            
            # Límites idénticos al rango para evitar zoom/pan
            self.gaitrite_plot.setLimits(
                xMin=-padding_x, xMax=CARPET_WIDTH_CM + padding_x, 
                yMin=-padding_y, yMax=CARPET_LENGTH_CM + padding_y
            )
            
            # Deshabilitar completamente la interacción de zoom/pan
            self.gaitrite_plot.setMouseEnabled(x=False, y=False)
            self.gaitrite_plot.setMenuEnabled(False)
            
            # No bloquear aspect ratio para permitir mejor ajuste al contenedor
            # self._set_plot_aspect_locked(self.gaitrite_plot, 1.0)
        except Exception as e:
            print(f"DEBUG: Error bloqueando vista: {e}")

    def visualize_direct_data(self):
        """Visualiza directamente todos los datos disponibles sin selección de test"""
        print("DEBUG: === VISUALIZACIÓN DIRECTA DE DATOS ===")
        
        if self.gaitrite_tests_df is None or self.gaitrite_tests_df.empty:
            print("DEBUG: No hay datos para visualizar")
            self.show_empty_plot()
            return
        
        print(f"DEBUG: Visualizando {len(self.gaitrite_tests_df)} huellas directamente")
        
        # Si hay Gait_Id, usar el primer ID disponible
        if 'Gait_Id' in self.gaitrite_tests_df.columns:
            gait_ids = self.gaitrite_tests_df['Gait_Id'].unique()
            if len(gait_ids) > 0:
                first_gait_id = sorted(gait_ids)[0]
                self.visualize_gait_test(first_gait_id)
                return
        
        # Fallback: dibujar rectángulos básicos desde el DataFrame principal
        self.gaitrite_plot.clear()
        self._draw_carpet_background(show_text=False)
        
        # Dibujar rectángulos básicos usando factor de conversión
        CONVERSION_FACTOR = 1.27
        for _, row in self.gaitrite_tests_df.iterrows():
            try:
                x = row['Ybottom'] * CONVERSION_FACTOR  
                y = row['Xback'] * CONVERSION_FACTOR
                width = (row['Ytop'] - row['Ybottom']) * CONVERSION_FACTOR
                height = (row['Xfront'] - row['Xback']) * CONVERSION_FACTOR
                
                if pd.isna([x, y, width, height]).any() or width <= 0 or height <= 0:
                    continue
                
                pen_color = pg.mkPen('red', width=2) if row['Foot'] == 0 else pg.mkPen('blue', width=2)
                rect_x = [x, x + width, x + width, x, x]
                rect_y = [y, y, y + height, y + height, y]
                self.gaitrite_plot.plot(rect_x, rect_y, pen=pen_color)
            except Exception:
                continue
        
        # Configurar vista fija
        self._lock_gaitrite_view()
        
        print("DEBUG: === FIN VISUALIZACIÓN DIRECTA ===")
    
    def _generate_footprints_from_yarray(self, gait_id):
        """
        Genera contornos de huellas desde Yarray usando la lógica de export_yarray_footprints.py
        Guarda los datos en CSV para futuras ejecuciones.
        """
        try:
            print("DEBUG: === GENERANDO CONTORNOS DESDE YARRAY ===")
            
            # Usar el DataFrame que ya tenemos cargado si tiene la columna Yarray
            if self.gaitrite_tests_df is not None and 'Yarray' in self.gaitrite_tests_df.columns:
                print("DEBUG: Usando datos GaitRite ya cargados")
                df = self.gaitrite_tests_df.copy()
                
                # Factor de conversión (igual que en export_yarray_footprints.py)
                conv = 1.27
                
                # Acumuladores por pie
                accum = {0: [], 1: []}  # 0=izquierdo, 1=derecho
                
                # Filtrar por el gait_id específico que queremos visualizar
                df_filtered = df[df['Gait_Id'] == gait_id].copy()
                if df_filtered.empty:
                    print(f"DEBUG: No se encontró Gait_Id {gait_id} en datos cargados")
                    return None, None
                
                print(f"DEBUG: Encontradas {len(df_filtered)} huellas para Gait_Id {gait_id}")
                
                # Orden estable por Event
                df_filtered = df_filtered.sort_values(["Event"]).reset_index(drop=True)
                
                for _, r in df_filtered.iterrows():
                    try:
                        foot = int(r["Foot"]) if pd.notna(r["Foot"]) else None
                    except Exception:
                        foot = None
                    if foot not in (0, 1):
                        continue
                    
                    try:
                        Xback_cm = float(r["Xback"]) * conv
                        Xfront_cm = float(r["Xfront"]) * conv
                        Ybottom_cm = float(r["Ybottom"]) * conv
                        Ytop_cm = float(r["Ytop"]) * conv
                    except Exception:
                        continue
                    
                    yarray_raw = str(r["Yarray"]) if pd.notna(r["Yarray"]) else ""
                    print(f"DEBUG: Procesando Event={r['Event']}, Foot={foot}, Yarray length={len(yarray_raw)}")
                    
                    df_xy = self._decode_yarray_to_xy(yarray_raw, Xback_cm, Xfront_cm, Ybottom_cm, Ytop_cm)
                    if df_xy is None or df_xy.empty:
                        print(f"DEBUG: No se pudo decodificar Yarray para Event={r['Event']}")
                        continue
                    
                    print(f"DEBUG: Decodificados {len(df_xy)} puntos para Event={r['Event']}")
                    
                    # Añadir metadatos
                    df_xy["participant"] = self.current_participant
                    df_xy["source_file"] = "gaitrite_test.csv"
                    df_xy["gait_id"] = int(r["Gait_Id"]) if pd.notna(r["Gait_Id"]) else None
                    df_xy["event"] = int(r["Event"]) if pd.notna(r["Event"]) else None
                    df_xy["foot"] = foot
                    df_xy["xback_cm"] = Xback_cm
                    df_xy["xfront_cm"] = Xfront_cm
                    df_xy["ybottom_cm"] = Ybottom_cm
                    df_xy["ytop_cm"] = Ytop_cm
                    df_xy["n_samples"] = int(df_xy.shape[0])
                    
                    accum[foot].append(df_xy)
            else:
                print("DEBUG: No hay datos Yarray disponibles en el DataFrame cargado")
                return None, None
            
            # Crear DataFrames finales y guardar en CSV
            footprints_left_df = None
            footprints_right_df = None
            
            # Crear carpeta del intento si no existe
            intent_path = Path("data") / self.current_participant / self.current_prueba / self.current_intento
            intent_path.mkdir(parents=True, exist_ok=True)
            
            for foot, foot_name in ((0, "left"), (1, "right")):
                if accum[foot]:
                    out_df = pd.concat(accum[foot], ignore_index=True)
                    # Orden por gait/event/sample_idx
                    out_df = out_df.sort_values(["gait_id", "event", "sample_idx"]).reset_index(drop=True)
                    
                    # Nombre fijo del archivo en la carpeta del intento
                    csv_filename = f"generated_footprints_{foot_name}.csv"
                    csv_path = intent_path / csv_filename
                    
                    # Guardar CSV
                    out_df.to_csv(csv_path, index=False)
                    print(f"DEBUG: Guardado {csv_filename} con {len(out_df)} registros")
                    
                    if foot == 0:
                        footprints_left_df = out_df
                    else:
                        footprints_right_df = out_df
            
            print("DEBUG: === FIN GENERACIÓN DESDE YARRAY ===")
            return footprints_left_df, footprints_right_df
            
        except Exception as e:
            print(f"DEBUG: Error generando contornos desde Yarray: {e}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            return None, None
    
    def _robust_minmax(self, vals):
        """Devuelve (lo, hi) usando percentiles 1 y 99; si colapsan, usa min/max reales."""
        if vals.size == 0:
            return 0.0, 1.0
        p1, p99 = np.percentile(vals, [1, 99])
        if not np.isfinite(p1) or not np.isfinite(p99) or p99 <= p1:
            p1, p99 = float(np.min(vals)), float(np.max(vals))
        if p99 == p1:
            # Evitar división por cero más adelante
            p99 = p1 + 1e-9
        return float(p1), float(p99)
    
    def _decode_yarray_to_xy(self, yarray_raw, Xback_cm, Xfront_cm, Ybottom_cm, Ytop_cm):
        """
        Decodifica Yarray a una serie de puntos (x_cm, y_cm) en orientación vertical.
        Lógica extraída de export_yarray_footprints.py
        """
        if not isinstance(yarray_raw, str) or len(yarray_raw) == 0:
            return None
        
        vals = np.fromiter((ord(c) for c in yarray_raw), dtype=float, count=len(yarray_raw))
        if vals.size == 0 or not np.isfinite(vals).all():
            return None
        
        lo, hi = self._robust_minmax(vals)
        vals_norm = (vals - lo) / (hi - lo)
        
        # Ancho lateral (x)
        dx = (Ytop_cm - Ybottom_cm)
        dy = (Xfront_cm - Xback_cm)
        if abs(dx) < 1e-9 or abs(dy) < 1e-9:
            return None
        
        x_cm = Ybottom_cm + vals_norm * dx
        N = vals.shape[0]
        y_cm = np.linspace(Xback_cm, Xfront_cm, N)
        
        df = pd.DataFrame({
            "sample_idx": np.arange(N, dtype=int),
            "x_cm": x_cm.astype(float),
            "y_cm": y_cm.astype(float),
        })
        return df
