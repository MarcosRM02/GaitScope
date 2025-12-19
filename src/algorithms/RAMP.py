"""
RAMP: Robust Adaptive Morphological Pressure
Algoritmo adaptativo de detección de eventos de marcha basado en análisis 
de presión plantar con morfología adaptativa.

Nota: Originalmente inspirado en el trabajo de Dobrescu et al., con 
mejoras significativas en el refinamiento de eventos usando segunda derivada
y validación temporal adaptativa.
"""

import numpy as np
from scipy.signal import savgol_filter, find_peaks, correlate
from scipy.stats import linregress
from sklearn.cluster import KMeans
from .base import GaitEventDetector


class Ramp(GaitEventDetector):
    """
    Detector de eventos de marcha usando el algoritmo RAMP 
    (Robust Adaptive Morphological Pressure).
    
    El algoritmo consta de 8 pasos:
    - Paso 0: Suma de presión de todos los sensores
    - Paso 1: Normalización IQR y suavizado Savitzky-Golay
    - Paso 2: Estimación del período de paso mediante autocorrelación
    - Paso 3: Segmentación binaria y clustering K-means
    - Paso 4: Limpieza morfológica (gaps y spikes)
    - Paso 5: Detección de candidatos mediante transiciones
    - Paso 6: Extracción de rampas
    - Paso 7: Refinamiento con derivada y nivel gamma
    - Paso 8: Validación temporal y eliminación de huérfanos
    """
    
    def __init__(
        self,
        sampling_rate=64,
        smooth_window_ms=40,
        polyorder=3,
        stance_fraction_est=0.6,
        min_step_period_s=0.3,
        max_step_period_s=3.0,
        peak_prom_frac=0.15,
        alpha_gap=0.15,
        alpha_spike=0.15,
        beta_window=0.4,
        ramp_high_level=0.9,
        min_stance_frac_step=0.2,
        max_stance_frac_step=1.0,
        min_swing_frac_step=0.15,
        max_swing_frac_step=1.0,
        peak_height_percentile_to=0.90,
        peak_prominence_to=0.2
    ):
        """
        Inicializa el detector con los parámetros del algoritmo.
        
        Args:
            sampling_rate: Frecuencia de muestreo en Hz
            smooth_window_ms: Ventana de suavizado Savitzky-Golay en milisegundos
            polyorder: Orden del polinomio para Savitzky-Golay
            stance_fraction_est: Estimación inicial del duty cycle (stance / ciclo). 
                Se usa sólo como prior; el valor efectivo se recalcula por trial 
                a partir de la señal.
            min_step_period_s: Período mínimo de paso esperado en segundos
            max_step_period_s: Período máximo de paso esperado en segundos
            peak_prom_frac: Fracción del máximo de autocorrelación para prominence
            alpha_gap: Fracción de T_stance para rellenar gaps
            alpha_spike: Fracción de T_swing para eliminar spikes
            beta_window: Fracción de T_stance para ventana de búsqueda de rampas
            ramp_high_level: Nivel de rampa usado para definir el tramo alto
            min_stance_frac_step: Fracción mínima de T_step para stance válido
            max_stance_frac_step: Fracción máxima de T_step para stance válido
            min_swing_frac_step: Fracción mínima de T_step para swing válido
            max_swing_frac_step: Fracción máxima de T_step para swing válido
            peak_height_percentile_to: Percentil para umbral de altura en picos TO (0-1, default: 0.90)
            peak_prominence_to: Prominencia fija para detección de picos TO en señal normalizada (default: 0.2)
        """
        self.fs = sampling_rate
        self.smooth_window_ms = smooth_window_ms
        self.polyorder = polyorder
        self.stance_fraction_est = stance_fraction_est
        self.min_step_period_s = min_step_period_s
        self.max_step_period_s = max_step_period_s
        self.peak_prom_frac = peak_prom_frac
        self.alpha_gap = alpha_gap
        self.alpha_spike = alpha_spike
        self.beta_window = beta_window
        self.ramp_high_level = ramp_high_level
        self.min_stance_frac_step = min_stance_frac_step
        self.max_stance_frac_step = max_stance_frac_step
        self.min_swing_frac_step = min_swing_frac_step
        self.max_swing_frac_step = max_swing_frac_step
        self.peak_height_percentile_to = peak_height_percentile_to
        self.peak_prominence_to = peak_prominence_to
        self.last_refinement_debug = None
        
    def detect(self, pressure_data: np.ndarray, foot=None) -> tuple[list[int], list[int]]:
        """
        Detecta eventos de marcha (Heel Strike y Toe Off).
        
        Args:
            pressure_data: Array (n_samples, 32) con datos de los 32 sensores
            foot: Pie a analizar (no utilizado en este algoritmo)
        
        Returns:
            heel_strikes: Lista de índices (muestras) de Heel Strikes
            toe_offs: Lista de índices (muestras) de Toe Offs
        """
        # PASO 0: Suma de presión
        pressure_sum = self._paso_0_pressure_sum(pressure_data)
        
        # PASO 1: Normalización IQR y suavizado
        x_smooth = self._paso_1_preprocessing(pressure_sum)
        
        # PASO 2: Estimación del período de paso
        T_step, T_stance, T_swing = self._paso_2_period_estimation(x_smooth)
        
        # PASO 3: Segmentación binaria y clustering
        state_binary = self._paso_3_segmentation_clustering(x_smooth, T_step, T_stance)
        
        # NUEVO: estimar duty cycle real a partir de state_binary
        duty_cycle = self._estimate_duty_cycle_from_state_binary(state_binary)
        
        # Actualizar stance_fraction_est para este trial
        self.stance_fraction_est = duty_cycle
        
        # Recalcular T_stance y T_swing en función del nuevo duty
        T_stance = duty_cycle * T_step
        T_swing = T_step - T_stance
        
        # PASO 4: Limpieza morfológica
        state_clean = self._paso_4_morphological_cleaning(state_binary, T_stance, T_swing)
        
        # PASO 5: Detección de candidatos mediante transiciones
        hs_candidates, to_candidates = self._paso_5_candidate_detection(state_clean)
        
        # PASO 6: Extracción de rampas
        hs_ramps, to_ramps = self._paso_6_ramp_extraction(
            x_smooth, hs_candidates, to_candidates, T_step, state_clean
        )
        
        # PASO 7: Refinamiento con derivada y nivel gamma + frontera stance/swing
        hs_refined, to_refined = self._paso_7_derivative_refinement(
            x_smooth, hs_ramps, to_ramps, state_clean
        )
        
        # PASO 8: Validación temporal y eliminación de huérfanos
        hs_final, to_final = self._paso_8_temporal_validation_and_orphan_removal(
            hs_refined, to_refined, T_step
        )
        
        # Convertir a listas
        return hs_final.tolist(), to_final.tolist()
    
    def _paso_0_pressure_sum(self, pressure_data: np.ndarray) -> np.ndarray:
        """
        Paso 0: Calcula la suma de presión de todos los sensores.
        
        Args:
            pressure_data: Array (n_samples, 32) con datos de presión
            
        Returns:
            pressure_sum: Array (n_samples,) con la suma de presión
        """
        return pressure_data.sum(axis=1)
    
    def _paso_1_preprocessing(self, pressure_sum: np.ndarray) -> np.ndarray:
        """
        Paso 1: Normalización IQR y suavizado Savitzky-Golay.
        
        Args:
            pressure_sum: Array con la suma de presión
            
        Returns:
            x_smooth: Señal normalizada y suavizada
        """
        # Normalización IQR
        q1 = np.percentile(pressure_sum, 25)
        q3 = np.percentile(pressure_sum, 75)
        iqr = q3 - q1
        median = np.median(pressure_sum)
        
        x_normalized = (pressure_sum - median) / iqr
        
        # Calcular window_length desde milisegundos
        window_length = int(self.fs * self.smooth_window_ms / 1000)
        
        # Ajustar a impar y >= polyorder + 2
        if window_length % 2 == 0:
            window_length += 1
        window_length = max(window_length, self.polyorder + 2)
        
        # Suavizado Savitzky-Golay
        x_smooth = savgol_filter(x_normalized, window_length, self.polyorder)
        
        return x_smooth
    
    def _paso_2_period_estimation(self, x_smooth: np.ndarray) -> tuple[float, float, float]:
        """
        Paso 2: Estimación del período de paso mediante autocorrelación.
        
        Args:
            x_smooth: Señal suavizada
            
        Returns:
            T_step: Período de paso estimado (en muestras)
            T_stance: Duración de stance estimada (en muestras)
            T_swing: Duración de swing estimada (en muestras)
        """
        # Centrar la señal
        x_centered = x_smooth - np.mean(x_smooth)
        
        # Autocorrelación
        autocorr = correlate(x_centered, x_centered, mode='full')
        autocorr = autocorr[len(autocorr)//2:]  # Solo la mitad positiva
        
        # Normalizar
        autocorr = autocorr / autocorr[0]
        
        # Calcular ventana de búsqueda desde tiempo
        min_lag = int(self.fs * self.min_step_period_s)
        max_lag = min(int(self.fs * self.max_step_period_s), len(autocorr))
        
        # Calcular prominence relativo al máximo en la ventana
        if max_lag > min_lag:
            max_autocorr_window = np.max(autocorr[min_lag:max_lag])
            prominence = self.peak_prom_frac * max_autocorr_window
        else:
            prominence = 0.1
        
        # Encontrar picos con prominence en la ventana
        peaks, properties = find_peaks(autocorr[min_lag:max_lag], prominence=prominence)
        peaks = peaks + min_lag  # Ajustar índices
        
        # El primer pico corresponde al período de paso
        if len(peaks) > 0:
            T_step = peaks[0]
        else:
            # Fallback: buscar máximo global en la ventana
            T_step = np.argmax(autocorr[min_lag:max_lag]) + min_lag
        
        # Estimar duraciones de stance y swing
        T_stance = self.stance_fraction_est * T_step
        T_swing = T_step - T_stance
        
        return T_step, T_stance, T_swing
    
    def _estimate_duty_cycle_from_state_binary(self, state_binary: np.ndarray) -> float:
        """
        Estima el duty cycle stance/swing (fracción de tiempo en stance)
        a partir de la señal binaria state_binary (0=swing, 1=stance).

        Estrategia sencilla y robusta:
          - duty_raw = media de state_binary (proporción de 1s).
          - Limitar el resultado a un rango razonable, p.ej. [0.2, 0.8],
            para evitar valores degenerados en señales raras.

        Args:
            state_binary: array binario (0/1) tras el Paso 3.

        Returns:
            duty_cycle: fracción de tiempo en stance (0–1).
        """
        if state_binary.size == 0:
            # Fallback: usar prior actual
            return self.stance_fraction_est

        duty_raw = float(np.mean(state_binary))

        # Clamp a rango razonable
        duty_clamped = max(0.2, min(0.8, duty_raw))

        return duty_clamped

    def _estimate_amplitude_boundary(self, x_smooth: np.ndarray,
                                     state_clean: np.ndarray) -> float | None:
        """
        Estima un umbral de amplitud que separa swing (LOW) de stance (HIGH)
        a partir de la propia señal del trial.

        Estrategia:
          - Tomar las muestras de x_smooth etiquetadas como swing (0) y stance (1)
            según state_clean.
          - Calcular la mediana de cada grupo.
          - Usar como frontera el punto medio entre ambas medianas.
          - Si no hay suficientes muestras de alguno de los estados, devolver None
            y dejar que la lógica de gamma actúe como fallback.

        Args:
            x_smooth: señal suavizada normalizada (Pasos 1–2).
            state_clean: máscara binaria limpia (0=swing, 1=stance) tras Paso 4.

        Returns:
            Umbral de amplitud (float) o None si no se puede estimar de forma fiable.
        """
        if state_clean is None or state_clean.size == 0:
            return None

        swing_mask = (state_clean == 0)
        stance_mask = (state_clean == 1)

        # Necesitamos muestras de ambos estados
        if not np.any(swing_mask) or not np.any(stance_mask):
            return None

        swing_vals = x_smooth[swing_mask]
        stance_vals = x_smooth[stance_mask]

        # Por seguridad, requerir un mínimo de muestras en cada grupo
        if swing_vals.size < 10 or stance_vals.size < 10:
            return None

        swing_med = float(np.median(swing_vals))
        stance_med = float(np.median(stance_vals))

        # Si por alguna razón stance no es más alto que swing, no usar este criterio
        if stance_med <= swing_med:
            return None

        boundary = 0.5 * (swing_med + stance_med)

        return boundary

    
    def _paso_3_segmentation_clustering(self, x_smooth: np.ndarray, 
                                       T_step: float, T_stance: float) -> np.ndarray:
        """
        Paso 3: Clustering K-means por amplitud (muestra a muestra).
        
        Clasificamos cada muestra según su amplitud usando K-means.
        El histograma bimodal de la señal define los dos estados HIGH/LOW.
        
        Args:
            x_smooth: Señal suavizada
            T_step: Período de paso estimado (no usado, mantener por compatibilidad)
            T_stance: Duración estimada de stance (no usado, mantener por compatibilidad)
            
        Returns:
            state_binary: Array binario (0=LOW/swing, 1=HIGH/stance)
        """
        # Construir array 2D para clustering: cada muestra es un dato
        values = x_smooth.reshape(-1, 1)
        
        # Clustering K-means con k=2 sobre amplitudes
        kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
        labels = kmeans.fit_predict(values)
        
        # Identificar cuál cluster es HIGH (mayor media)
        mean0 = values[labels == 0].mean()
        mean1 = values[labels == 1].mean()
        high_label = 1 if mean1 > mean0 else 0
        
        # Construir state_binary: 1 si pertenece al cluster HIGH, 0 si LOW
        state_binary = np.zeros(len(x_smooth), dtype=int)
        state_binary[labels == high_label] = 1
        
        return state_binary
    
    def _paso_4_morphological_cleaning(self, state_binary: np.ndarray, 
                                      T_stance: float, T_swing: float) -> np.ndarray:
        """
        Paso 4: Limpieza morfológica - rellenar gaps y eliminar spikes.
        
        Args:
            state_binary: Array binario de estados
            T_stance: Duración estimada de stance
            T_swing: Duración estimada de swing
            
        Returns:
            state_clean: Array binario limpiado
        """
        state_clean = state_binary.copy()
        
        # Calcular umbrales: gaps contra T_stance, spikes contra T_swing
        max_gap_length = int(self.alpha_gap * T_stance)
        max_spike_length = int(self.alpha_spike * T_swing)
        
        # RELLENAR GAPS (segmentos cortos de 0 entre 1s)
        changed = True
        while changed:
            changed = False
            i = 0
            while i < len(state_clean) - 1:
                if state_clean[i] == 1 and state_clean[i + 1] == 0:
                    # Inicio de gap
                    gap_start = i + 1
                    gap_end = gap_start
                    
                    # Encontrar final del gap
                    while gap_end < len(state_clean) and state_clean[gap_end] == 0:
                        gap_end += 1
                    
                    gap_length = gap_end - gap_start
                    
                    # Si el gap es corto y está seguido por 1, rellenar
                    if gap_length <= max_gap_length and gap_end < len(state_clean) and state_clean[gap_end] == 1:
                        state_clean[gap_start:gap_end] = 1
                        changed = True
                    
                    i = gap_end
                else:
                    i += 1
        
        # ELIMINAR SPIKES (segmentos cortos de 1 entre 0s)
        changed = True
        while changed:
            changed = False
            i = 0
            while i < len(state_clean) - 1:
                if state_clean[i] == 0 and state_clean[i + 1] == 1:
                    # Inicio de spike
                    spike_start = i + 1
                    spike_end = spike_start
                    
                    # Encontrar final del spike
                    while spike_end < len(state_clean) and state_clean[spike_end] == 1:
                        spike_end += 1
                    
                    spike_length = spike_end - spike_start
                    
                    # Si el spike es corto y está seguido por 0, eliminar
                    if spike_length <= max_spike_length and spike_end < len(state_clean) and state_clean[spike_end] == 0:
                        state_clean[spike_start:spike_end] = 0
                        changed = True
                    
                    i = spike_end
                else:
                    i += 1
        
        return state_clean
    
    def _paso_5_candidate_detection(self, state_clean: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Paso 5: Detección de candidatos mediante transiciones.
        
        Args:
            state_clean: Array binario limpiado
            
        Returns:
            hs_candidates: Índices de candidatos a Heel Strike (transiciones 0→1)
            to_candidates: Índices de candidatos a Toe Off (transiciones 1→0)
        """
        # Detectar transiciones usando diff
        diff = np.diff(state_clean)
        
        # HS: transición 0 → 1 (diff == 1)
        hs_candidates = np.where(diff == 1)[0] + 1  # +1 porque diff reduce el tamaño
        
        # TO: transición 1 → 0 (diff == -1)
        to_candidates = np.where(diff == -1)[0] + 1
        
        return hs_candidates, to_candidates
    
    def _paso_6_ramp_extraction(self, x_smooth: np.ndarray, 
                                hs_candidates: np.ndarray,
                                to_candidates: np.ndarray,
                                T_step: float,
                                state_clean: np.ndarray) -> tuple[list, list]:
        """
        Paso 6: Extracción de rampas para refinar eventos.
        
        Args:
            x_smooth: Señal suavizada
            hs_candidates: Candidatos a Heel Strike
            to_candidates: Candidatos a Toe Off
            T_step: Período de paso estimado
            state_clean: Array binario de estados limpiados
            
        Returns:
            hs_ramps: Lista de diccionarios con información de rampas HS
            to_ramps: Lista de diccionarios con información de rampas TO
        """
        window_samples = int(self.beta_window * self.stance_fraction_est * T_step)
        
        # Obtener segmentos de state_clean
        segments_clean = []
        states_clean = []
        
        # Detectar cambios de estado
        diff = np.diff(state_clean)
        changes = np.where(diff != 0)[0] + 1
        breakpoints = [0] + changes.tolist() + [len(state_clean)]
        
        for i in range(len(breakpoints) - 1):
            start = breakpoints[i]
            end = breakpoints[i + 1]
            state = 'HIGH' if state_clean[start] == 1 else 'LOW'
            segments_clean.append((start, end))
            states_clean.append(state)
        
        # ===== EXTRAER RAMPAS DE SUBIDA (HS) =====
        hs_ramps = []
        
        for hs_idx in hs_candidates:
            # Definir ventana de búsqueda
            window_start = max(0, hs_idx - window_samples)
            window_end = min(len(x_smooth), hs_idx + window_samples)
            
            # Buscar mínimo local ANTES de la transición (inicio de rampa)
            pre_transition = x_smooth[window_start:hs_idx]
            if len(pre_transition) > 0:
                ramp_start_local = np.argmin(pre_transition)
                ramp_start = window_start + ramp_start_local
            else:
                ramp_start = window_start
            
            # Estimar plateau: mediana del segmento HIGH correspondiente
            plateau_value = None
            for (seg_start, seg_end), st in zip(segments_clean, states_clean):
                if st == 'HIGH' and seg_start <= hs_idx < seg_end:
                    # Tomar parte central del segmento (evitar bordes)
                    center_start = seg_start + int(0.2 * (seg_end - seg_start))
                    center_end = seg_start + int(0.8 * (seg_end - seg_start))
                    if center_end > center_start:
                        plateau_value = np.median(x_smooth[center_start:center_end])
                    break
            
            if plateau_value is None:
                plateau_value = np.median(x_smooth[window_start:window_end])
            
            # Buscar punto donde señal alcanza ramp_high_level del plateau después de la transición
            post_transition = x_smooth[hs_idx:window_end]
            min_val = x_smooth[ramp_start]
            target_value = min_val + self.ramp_high_level * (plateau_value - min_val)
            
            ramp_end = hs_idx
            for i, val in enumerate(post_transition):
                if val >= target_value:
                    ramp_end = hs_idx + i
                    break
            
            hs_ramps.append({
                'candidate_idx': int(hs_idx),
                'ramp_start': int(ramp_start),
                'ramp_end': int(ramp_end),
                'min_value': float(min_val),
                'plateau_value': float(plateau_value),
                'window_start': int(window_start),
                'window_end': int(window_end)
            })
        
        # ===== EXTRAER RAMPAS DE BAJADA (TO) =====
        to_ramps = []
        
        for to_idx in to_candidates:
            # Definir ventana de búsqueda
            window_start = max(0, to_idx - window_samples)
            window_end = min(len(x_smooth), to_idx + window_samples)
            
            # Estimar plateau: mediana del segmento HIGH anterior
            plateau_value = None
            for (seg_start, seg_end), st in zip(segments_clean, states_clean):
                if st == 'HIGH' and seg_start < to_idx <= seg_end:
                    center_start = seg_start + int(0.2 * (seg_end - seg_start))
                    center_end = seg_start + int(0.8 * (seg_end - seg_start))
                    if center_end > center_start:
                        plateau_value = np.median(x_smooth[center_start:center_end])
                    break
            
            if plateau_value is None:
                plateau_value = np.median(x_smooth[window_start:window_end])
            
            # Buscar mínimo local DESPUÉS de la transición (final de rampa)
            post_transition = x_smooth[to_idx:window_end]
            if len(post_transition) > 0:
                ramp_end_local = np.argmin(post_transition)
                ramp_end = to_idx + ramp_end_local
            else:
                ramp_end = window_end - 1
            
            # Inicio de rampa: donde señal cae desde ramp_high_level del plateau antes de la transición
            pre_transition = x_smooth[window_start:to_idx]
            min_val = x_smooth[ramp_end]
            target_value = plateau_value - (1.0 - self.ramp_high_level) * (plateau_value - min_val)
            
            ramp_start = to_idx
            for i in range(len(pre_transition) - 1, -1, -1):
                if pre_transition[i] >= target_value:
                    ramp_start = window_start + i
                    break
            
            to_ramps.append({
                'candidate_idx': int(to_idx),
                'ramp_start': int(ramp_start),
                'ramp_end': int(ramp_end),
                'plateau_value': float(plateau_value),
                'min_value': float(min_val),
                'window_start': int(window_start),
                'window_end': int(window_end)
            })
        
        return hs_ramps, to_ramps
    
    def _paso_7_derivative_refinement(self, x_smooth: np.ndarray,
                                     hs_ramps: list,
                                     to_ramps: list,
                                     state_clean: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Paso 7: Refinamiento usando máximo de segunda derivada.
        
        Estrategia (basada en análisis de clustering del notebook):
        1. HS: Extender -3 samples al INICIO (contexto previo)
           TO: Extender +3 samples al FINAL (contexto posterior)
        2. Normalizar cada rampa extendida a [0,1]
        3. Calcular segunda derivada con np.diff dos veces
        4. Buscar máximo de segunda derivada en TODA la rampa extendida
        5. El índice del máximo de 2ª derivada es el evento refinado
        
        Args:
            x_smooth: Señal suavizada
            hs_ramps: Lista de diccionarios con información de rampas HS
            to_ramps: Lista de diccionarios con información de rampas TO
            state_clean: Array binario de estados limpiados (no usado)
            
        Returns:
            hs_refined: Eventos HS refinados
            to_refined: Eventos TO refinados
        """
        DT_MS = 1000.0 / self.fs
        self.last_refinement_debug = {
            'hs': [],
            'to': [],
            'dt_ms': DT_MS
        }

        hs_events_refined = []

        for ramp_idx, ramp in enumerate(hs_ramps):
            ramp_start = ramp['ramp_start']
            ramp_end = ramp['ramp_end']
            
            # HS: Extender -3 samples al INICIO (como en notebook líneas 109-119)
            ramp_start_ext = max(0, ramp_start - 3)
            ramp_signal = x_smooth[ramp_start_ext:ramp_end]

            debug_entry = {
                'ramp_index': ramp_idx,
                'candidate_idx': int(ramp['candidate_idx']),
                'ramp_start': int(ramp_start_ext),
                'ramp_end': int(ramp_end),
                'ramp_signal': ramp_signal.copy(),
                'status': 'ok'
            }
            
            if len(ramp_signal) < 5:
                # Rampa demasiado corta para calcular segunda derivada, usar candidato original
                hs_events_refined.append(ramp['candidate_idx'])
                debug_entry.update({
                    'status': 'short_ramp',
                    'normalized_signal': None,
                    'first_derivative': None,
                    'second_derivative': None,
                    'refined_idx': int(ramp['candidate_idx']),
                    'max_idx_local': None
                })
                self.last_refinement_debug['hs'].append(debug_entry)
                continue
            
            # Normalizar amplitud a [0,1] - HS es ascendente
            r_norm = (ramp_signal - ramp_signal.min()) / (ramp_signal.max() - ramp_signal.min() + 1e-9)
            
            # Calcular segunda derivada usando np.diff dos veces (como en el notebook)
            first_derivative = np.diff(r_norm) / DT_MS  # 1ª derivada
            second_derivative = np.diff(first_derivative) / DT_MS  # 2ª derivada
            
            # Buscar máximo en TODA la 2ª derivada (sin restricción 20%-80%)
            if len(second_derivative) > 0:
                max_idx_local = np.argmax(second_derivative)
            else:
                # Si no hay 2ª derivada, usar candidato original
                hs_events_refined.append(ramp['candidate_idx'])
                debug_entry.update({
                    'status': 'no_second_derivative',
                    'normalized_signal': r_norm.copy(),
                    'first_derivative': first_derivative.copy(),
                    'second_derivative': second_derivative.copy(),
                    'refined_idx': int(ramp['candidate_idx']),
                    'max_idx_local': None
                })
                self.last_refinement_debug['hs'].append(debug_entry)
                continue
            
            # El índice del máximo + offset para alineación con x_smooth
            # second_derivative[i] corresponde a x_smooth[ramp_start_ext + i + 1]
            t_refined = ramp_start_ext + max_idx_local + 1
            
            # Asegurar que está dentro de los límites válidos
            t_refined = max(ramp_start_ext, min(len(x_smooth) - 1, t_refined))
            
            hs_events_refined.append(t_refined)
            debug_entry.update({
                'normalized_signal': r_norm.copy(),
                'first_derivative': first_derivative.copy(),
                'second_derivative': second_derivative.copy(),
                'refined_idx': int(t_refined),
                'max_idx_local': int(max_idx_local)
            })
            self.last_refinement_debug['hs'].append(debug_entry)
        
        # Refinar eventos TO
        to_events_refined = []
        
        for ramp_idx, ramp in enumerate(to_ramps):
            ramp_start = ramp['ramp_start']
            ramp_end = ramp['ramp_end']
            
            # TO: Extender +3 samples al FINAL (como en notebook líneas 109-119)
            ramp_end_ext = min(ramp_end + 3, len(x_smooth))
            ramp_signal = x_smooth[ramp_start:ramp_end_ext]

            debug_entry = {
                'ramp_index': ramp_idx,
                'candidate_idx': int(ramp['candidate_idx']),
                'ramp_start': int(ramp_start),
                'ramp_end': int(ramp_end_ext),
                'ramp_signal': ramp_signal.copy(),
                'status': 'ok'
            }
            
            if len(ramp_signal) < 5:
                # Rampa demasiado corta para calcular segunda derivada, usar candidato original
                to_events_refined.append(ramp['candidate_idx'])
                debug_entry.update({
                    'status': 'short_ramp',
                    'normalized_signal': None,
                    'first_derivative': None,
                    'second_derivative': None,
                    'refined_idx': int(ramp['candidate_idx']),
                    'max_idx_local': None
                })
                self.last_refinement_debug['to'].append(debug_entry)
                continue
            
            # Normalizar amplitud a [0,1] - TO es descendente, NO invertir
            # (en el notebook se visualiza tal cual, sin inversión)
            r_norm = (ramp_signal - ramp_signal.min()) / (ramp_signal.max() - ramp_signal.min() + 1e-9)
            
            # Calcular segunda derivada usando np.diff dos veces (como en el notebook)
            first_derivative = np.diff(r_norm) / DT_MS  # 1ª derivada
            second_derivative = np.diff(first_derivative) / DT_MS  # 2ª derivada
            
            # Para TO (rampa de bajada), buscamos el MÁXIMO de la segunda derivada
            # usando detección de picos con find_peaks
            if len(second_derivative) > 0:
                # Calcular posición relativa del candidato en la 2ª derivada
                candidate_relative = ramp['candidate_idx'] - ramp_start
                # Ajustar por offset de 2ª derivada (+1 sample respecto a señal)
                candidate_in_second_deriv = candidate_relative - 1
                
                # Normalizar segunda derivada para aplicar thresholds consistentes
                second_norm = (second_derivative - second_derivative.min()) / \
                              (second_derivative.max() - second_derivative.min() + 1e-9)
                
                # Calcular umbral de altura como percentil
                height_threshold = np.quantile(second_norm, self.peak_height_percentile_to)
                
                # Detectar picos con restricciones de altura y prominencia
                peaks_idx, props = find_peaks(
                    second_norm,
                    height=height_threshold,
                    prominence=self.peak_prominence_to
                )
                
                # Filtrar picos válidos (índice > candidato, estrictamente mayor)
                valid_peaks = peaks_idx[peaks_idx > candidate_in_second_deriv]
                
                # Encontrar argmax global en región después del candidato
                region_after_candidate = second_derivative[candidate_in_second_deriv + 1:]
                if len(region_after_candidate) > 0:
                    argmax_rel = candidate_in_second_deriv + 1 + np.argmax(region_after_candidate)
                else:
                    # No hay región después del candidato, fallback al candidato mismo
                    argmax_rel = candidate_in_second_deriv
                
                # LÓGICA DE SELECCIÓN
                if valid_peaks.size == 0:
                    # Caso 0: No hay picos válidos → usar argmax después del candidato
                    max_idx_local = argmax_rel
                    
                elif valid_peaks.size == 1:
                    # Caso 1: Un solo pico válido
                    # Comparar con argmax: elegir el más cercano al candidato
                    peak_candidate = valid_peaks[0]
                    dist_peak = abs(peak_candidate - candidate_in_second_deriv)
                    dist_argmax = abs(argmax_rel - candidate_in_second_deriv)
                    
                    if dist_argmax < dist_peak:
                        max_idx_local = argmax_rel
                    else:
                        max_idx_local = peak_candidate
                
                else:
                    # Caso múltiples: Elegir el pico más cercano al candidato (primero a la derecha)
                    peak_candidate = valid_peaks[0]
                    dist_peak = abs(peak_candidate - candidate_in_second_deriv)
                    dist_argmax = abs(argmax_rel - candidate_in_second_deriv)
                    
                    if dist_argmax < dist_peak:
                        max_idx_local = argmax_rel
                    else:
                        max_idx_local = peak_candidate
                
            else:
                # Si no hay 2ª derivada, usar candidato original
                to_events_refined.append(ramp['candidate_idx'])
                debug_entry.update({
                    'status': 'no_second_derivative',
                    'normalized_signal': r_norm.copy(),
                    'first_derivative': first_derivative.copy(),
                    'second_derivative': second_derivative.copy(),
                    'second_derivative_norm': None,
                    'peaks_detected': None,
                    'num_peaks': 0,
                    'refined_idx': int(ramp['candidate_idx']),
                    'max_idx_local': None
                })
                self.last_refinement_debug['to'].append(debug_entry)
                continue
            
            # El índice del máximo + offset para alineación con x_smooth
            # second_derivative[i] corresponde a x_smooth[ramp_start + i + 1]
            t_refined = ramp_start + max_idx_local + 1
            
            # Asegurar que está dentro de los límites válidos
            t_refined = max(ramp_start, min(len(x_smooth) - 1, t_refined))
            
            to_events_refined.append(t_refined)
            debug_entry.update({
                'normalized_signal': r_norm.copy(),
                'first_derivative': first_derivative.copy(),
                'second_derivative': second_derivative.copy(),
                'second_derivative_norm': second_norm.copy(),
                'peaks_detected': peaks_idx.copy() if peaks_idx.size > 0 else None,
                'num_peaks': int(peaks_idx.size),
                'refined_idx': int(t_refined),
                'max_idx_local': int(max_idx_local)
            })
            self.last_refinement_debug['to'].append(debug_entry)
        
        return np.array(hs_events_refined), np.array(to_events_refined)
    
    def _paso_8_temporal_validation_and_orphan_removal(self, hs_refined: np.ndarray,
                                                       to_refined: np.ndarray,
                                                       T_step: float) -> tuple[np.ndarray, np.ndarray]:
        """
        Paso 8: Validación temporal y eliminación de huérfanos.
        
        Args:
            hs_refined: Eventos HS refinados
            to_refined: Eventos TO refinados
            T_step: Período de paso estimado
            
        Returns:
            hs_final: Eventos HS validados y sin huérfanos
            to_final: Eventos TO validados y sin huérfanos
        """
        # Calcular límites temporales como fracciones de T_step
        min_stance_samples = int(self.min_stance_frac_step * T_step)
        max_stance_samples = int(self.max_stance_frac_step * T_step)
        min_swing_samples = int(self.min_swing_frac_step * T_step)
        max_swing_samples = int(self.max_swing_frac_step * T_step)
        
        # Combinar eventos y ordenar
        events_combined = []
        for hs in hs_refined:
            events_combined.append(('HS', int(hs)))
        for to in to_refined:
            events_combined.append(('TO', int(to)))
        
        events_combined.sort(key=lambda x: x[1])
        
        # Validar secuencia
        events_valid = []
        expected_next = 'HS'
        
        i = 0
        while i < len(events_combined):
            event_type, event_idx = events_combined[i]
            
            # Verificar orden esperado
            if event_type != expected_next:
                i += 1
                continue
            
            # Si es HS, verificar duración de stance
            if event_type == 'HS':
                # Buscar próximo TO
                next_to_idx = None
                for j in range(i + 1, len(events_combined)):
                    if events_combined[j][0] == 'TO':
                        next_to_idx = events_combined[j][1]
                        break
                
                if next_to_idx is not None:
                    stance_duration = next_to_idx - event_idx
                    if stance_duration < min_stance_samples or stance_duration > max_stance_samples:
                        i += 1
                        continue
                
                events_valid.append(('HS', event_idx))
                expected_next = 'TO'
            
            # Si es TO, verificar duración de swing
            elif event_type == 'TO':
                # Buscar próximo HS
                next_hs_idx = None
                for j in range(i + 1, len(events_combined)):
                    if events_combined[j][0] == 'HS':
                        next_hs_idx = events_combined[j][1]
                        break
                
                if next_hs_idx is not None:
                    swing_duration = next_hs_idx - event_idx
                    if swing_duration < min_swing_samples or swing_duration > max_swing_samples:
                        # Swing inválido, remover último HS también
                        if len(events_valid) > 0 and events_valid[-1][0] == 'HS':
                            events_valid.pop()
                        i += 1
                        expected_next = 'HS'
                        continue
                
                events_valid.append(('TO', event_idx))
                expected_next = 'HS'
            
            i += 1
        
        # Separar eventos
        hs_temp = np.array([idx for event_type, idx in events_valid if event_type == 'HS'])
        to_temp = np.array([idx for event_type, idx in events_valid if event_type == 'TO'])
        
        # Emparejar eventos correctamente
        hs_final = []
        to_final = []
        
        for hs_idx in hs_temp:
            # Buscar TO correspondiente (debe estar después del HS)
            to_candidates = to_temp[to_temp > hs_idx]
            if len(to_candidates) > 0:
                to_idx = to_candidates[0]
                
                # Verificar que no haya otro HS antes de este TO
                hs_between = hs_temp[(hs_temp > hs_idx) & (hs_temp < to_idx)]
                if len(hs_between) == 0:
                    # Par válido HS-TO
                    hs_final.append(hs_idx)
                    # Solo agregar TO si no está ya en la lista
                    if to_idx not in to_final:
                        to_final.append(to_idx)
        
        return np.array(hs_final), np.array(to_final)