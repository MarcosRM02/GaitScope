"""Clase base abstracta para algoritmos de detección de eventos de marcha"""

from abc import ABC, abstractmethod
import numpy as np
import pandas as pd


class GaitEventDetector(ABC):
    """
    Clase base para detectores de eventos de marcha.
    
    Todos los algoritmos heredan de esta clase y deben implementar detect().
    """
    
    @abstractmethod
    def detect(self, pressure_data: np.ndarray, foot=None) -> tuple[list[int], list[int]]:
        """
        Detecta eventos de marcha a partir de datos de presión.
        
        Args:
            pressure_data: Array (n_samples, 32) con datos de los 32 sensores
            foot: Pie a analizar. Usar constantes: FOOT_LEFT ('L') o FOOT_RIGHT ('R')
        
        Returns:
            heel_strikes: Lista de índices (muestras) de Heel Strikes
            toe_offs: Lista de índices (muestras) de Toe Offs
        """
        pass
    
    def to_events_dataframe(self, pressure_data: np.ndarray, sampling_rate: int, spurious_init=None, spurious_end=None,  foot=None) -> pd.DataFrame:
        """
        Detecta eventos y los convierte a DataFrame estándar.
        
        Args:
            pressure_data: Array (n_samples, 32) con datos de los 32 sensores
            foot: Pie a analizar. Usar constantes: FOOT_LEFT ('L') o FOOT_RIGHT ('R')
            sampling_rate: Frecuencia de muestreo en Hz
            spurious_init: Índice de muestra donde inicia la región válida (None = sin filtrado inicial)
            spurious_end: Índice de muestra donde termina la región válida (None = sin filtrado final)
        
        Returns:
            DataFrame con columnas: event_type, event_number, time_seconds, foot
        """
        # Detectar eventos (índices de muestras) - pasar foot al detector
        ic_indices, to_indices = self.detect(pressure_data, foot=foot)
        
        # Calcular tiempos de corte si se especifican límites espurios
        valid_start_time = spurious_init / sampling_rate if spurious_init is not None else -np.inf
        valid_end_time = spurious_end / sampling_rate if spurious_end is not None else np.inf
        
        # Construir lista de eventos
        events = []
        
        # Añadir Heel Strikes (solo los que están en la región válida)
        for i, idx in enumerate(ic_indices, start=1):
            time_sec = idx / sampling_rate
            if valid_start_time <= time_sec <= valid_end_time:
                events.append({
                    'event_type': 'HS',
                    'event_number': i,
                    'time_seconds': time_sec,
                    'foot': foot
                })
        
        # Añadir Toe Offs (solo los que están en la región válida)
        for i, idx in enumerate(to_indices, start=1):
            time_sec = idx / sampling_rate
            if valid_start_time <= time_sec <= valid_end_time:
                events.append({
                    'event_type': 'TO',
                    'event_number': i,
                    'time_seconds': time_sec,
                    'foot': foot
                })
        
        # Convertir a DataFrame y ordenar por tiempo
        df = pd.DataFrame(events)
        if len(df) > 0:
            df = df.sort_values('time_seconds').reset_index(drop=True)
        
        return df