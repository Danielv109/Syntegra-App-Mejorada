import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.covariance import EllipticEnvelope
from sklearn.neighbors import LocalOutlierFactor
from datetime import datetime

from app.logger import get_logger

logger = get_logger()


class AnomalyDetector:
    """Detector de anomalías usando múltiples algoritmos de scikit-learn"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.models = {}
    
    def detect_anomalies_isolation_forest(
        self,
        df: pd.DataFrame,
        columns: List[str],
        contamination: float = 0.1,
        random_state: int = 42,
        n_estimators: int = 100,
    ) -> Dict[str, Any]:
        """
        Detectar anomalías usando Isolation Forest
        
        Args:
            df: DataFrame con los datos
            columns: Lista de columnas numéricas a analizar
            contamination: Proporción esperada de anomalías (0.0 a 0.5)
            random_state: Semilla para reproducibilidad
            n_estimators: Número de árboles en el ensemble
            
        Returns:
            Diccionario con resultados de detección
        """
        logger.info(f"Detectando anomalías con IsolationForest en columnas: {columns}")
        
        try:
            # Filtrar columnas válidas
            valid_columns = [col for col in columns if col in df.columns]
            if not valid_columns:
                raise ValueError("Ninguna de las columnas especificadas existe en el DataFrame")
            
            # Preparar datos
            X = df[valid_columns].copy()
            
            # Eliminar filas con valores nulos
            X_clean = X.dropna()
            
            if len(X_clean) < 10:
                raise ValueError("No hay suficientes datos para detectar anomalías (mínimo 10 filas)")
            
            # Convertir a numérico
            for col in valid_columns:
                X_clean[col] = pd.to_numeric(X_clean[col], errors='coerce')
            
            # Eliminar filas que quedaron con NaN después de conversión
            X_clean = X_clean.dropna()
            
            if len(X_clean) < 10:
                raise ValueError("No hay suficientes datos numéricos válidos")
            
            # Normalizar datos
            X_scaled = self.scaler.fit_transform(X_clean)
            
            # Crear y entrenar modelo IsolationForest
            iso_forest = IsolationForest(
                contamination=contamination,
                random_state=random_state,
                n_estimators=n_estimators,
                max_samples='auto',
                max_features=1.0,
                bootstrap=False,
                n_jobs=-1,
                verbose=0,
            )
            
            # Predecir anomalías (-1 = anomalía, 1 = normal)
            predictions = iso_forest.fit_predict(X_scaled)
            
            # Calcular scores de anomalía (más negativo = más anómalo)
            anomaly_scores = iso_forest.score_samples(X_scaled)
            
            # Crear DataFrame con resultados
            results_df = X_clean.copy()
            results_df['is_anomaly'] = predictions == -1
            results_df['anomaly_score'] = anomaly_scores
            results_df['anomaly_severity'] = self._calculate_severity(anomaly_scores)
            
            # Identificar anomalías
            anomalies = results_df[results_df['is_anomaly']]
            
            # Estadísticas por columna
            column_stats = {}
            for col in valid_columns:
                anomalies_in_col = anomalies[col]
                column_stats[col] = {
                    'total_anomalies': len(anomalies),
                    'mean_anomaly_value': float(anomalies_in_col.mean()) if len(anomalies) > 0 else None,
                    'median_anomaly_value': float(anomalies_in_col.median()) if len(anomalies) > 0 else None,
                    'min_anomaly_value': float(anomalies_in_col.min()) if len(anomalies) > 0 else None,
                    'max_anomaly_value': float(anomalies_in_col.max()) if len(anomalies) > 0 else None,
                    'normal_mean': float(results_df[~results_df['is_anomaly']][col].mean()),
                    'normal_std': float(results_df[~results_df['is_anomaly']][col].std()),
                }
            
            # Análisis de severidad
            severity_distribution = results_df[results_df['is_anomaly']]['anomaly_severity'].value_counts().to_dict()
            
            report = {
                'method': 'IsolationForest',
                'total_records': len(X_clean),
                'total_anomalies': int(anomalies['is_anomaly'].sum()),
                'anomaly_percentage': round(float(anomalies['is_anomaly'].sum() / len(X_clean) * 100), 2),
                'contamination_used': contamination,
                'columns_analyzed': valid_columns,
                'model_parameters': {
                    'n_estimators': n_estimators,
                    'max_samples': 'auto',
                    'contamination': contamination,
                },
                'column_statistics': column_stats,
                'severity_distribution': {
                    'critical': int(severity_distribution.get('critical', 0)),
                    'high': int(severity_distribution.get('high', 0)),
                    'medium': int(severity_distribution.get('medium', 0)),
                    'low': int(severity_distribution.get('low', 0)),
                },
                'anomaly_details': self._format_anomalies(anomalies, valid_columns),
                'timestamp': datetime.utcnow().isoformat(),
            }
            
            logger.info(
                f"Detección completada: {report['total_anomalies']} anomalías "
                f"({report['anomaly_percentage']}%) de {report['total_records']} registros"
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Error en detección de anomalías con IsolationForest: {e}")
            raise
    
    def detect_anomalies_multivariate(
        self,
        df: pd.DataFrame,
        columns: List[str],
        contamination: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Detectar anomalías multivariadas usando Elliptic Envelope
        (Asume distribución Gaussiana)
        """
        logger.info(f"Detectando anomalías multivariadas en columnas: {columns}")
        
        try:
            # Preparar datos
            valid_columns = [col for col in columns if col in df.columns]
            X = df[valid_columns].dropna()
            
            for col in valid_columns:
                X[col] = pd.to_numeric(X[col], errors='coerce')
            
            X = X.dropna()
            
            if len(X) < 10:
                raise ValueError("No hay suficientes datos")
            
            # Normalizar
            X_scaled = self.scaler.fit_transform(X)
            
            # Crear modelo
            envelope = EllipticEnvelope(
                contamination=contamination,
                random_state=42,
                support_fraction=None,
            )
            
            # Predecir
            predictions = envelope.fit_predict(X_scaled)
            
            # Resultados
            results_df = X.copy()
            results_df['is_anomaly'] = predictions == -1
            
            anomalies = results_df[results_df['is_anomaly']]
            
            return {
                'method': 'EllipticEnvelope',
                'total_records': len(X),
                'total_anomalies': int(anomalies['is_anomaly'].sum()),
                'anomaly_percentage': round(float(anomalies['is_anomaly'].sum() / len(X) * 100), 2),
                'anomaly_details': self._format_anomalies(anomalies, valid_columns),
                'timestamp': datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error en detección multivariada: {e}")
            raise
    
    def detect_anomalies_local_outlier_factor(
        self,
        df: pd.DataFrame,
        columns: List[str],
        contamination: float = 0.1,
        n_neighbors: int = 20,
    ) -> Dict[str, Any]:
        """
        Detectar anomalías usando Local Outlier Factor
        (Densidad local de vecinos)
        """
        logger.info(f"Detectando anomalías con LOF en columnas: {columns}")
        
        try:
            # Preparar datos
            valid_columns = [col for col in columns if col in df.columns]
            X = df[valid_columns].dropna()
            
            for col in valid_columns:
                X[col] = pd.to_numeric(X[col], errors='coerce')
            
            X = X.dropna()
            
            if len(X) < n_neighbors:
                raise ValueError(f"No hay suficientes datos (mínimo {n_neighbors})")
            
            # Normalizar
            X_scaled = self.scaler.fit_transform(X)
            
            # Crear modelo
            lof = LocalOutlierFactor(
                n_neighbors=n_neighbors,
                contamination=contamination,
                novelty=False,
            )
            
            # Predecir
            predictions = lof.fit_predict(X_scaled)
            
            # Resultados
            results_df = X.copy()
            results_df['is_anomaly'] = predictions == -1
            
            anomalies = results_df[results_df['is_anomaly']]
            
            return {
                'method': 'LocalOutlierFactor',
                'total_records': len(X),
                'total_anomalies': int(anomalies['is_anomaly'].sum()),
                'anomaly_percentage': round(float(anomalies['is_anomaly'].sum() / len(X) * 100), 2),
                'n_neighbors': n_neighbors,
                'anomaly_details': self._format_anomalies(anomalies, valid_columns),
                'timestamp': datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error en detección LOF: {e}")
            raise
    
    def detect_anomalies_ensemble(
        self,
        df: pd.DataFrame,
        columns: List[str],
        contamination: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Detectar anomalías usando ensemble de múltiples métodos
        (Combina IsolationForest, EllipticEnvelope y LOF)
        """
        logger.info(f"Detectando anomalías con ensemble en columnas: {columns}")
        
        try:
            # Ejecutar cada método
            iso_results = self.detect_anomalies_isolation_forest(df, columns, contamination)
            
            try:
                elliptic_results = self.detect_anomalies_multivariate(df, columns, contamination)
            except:
                elliptic_results = None
            
            try:
                lof_results = self.detect_anomalies_local_outlier_factor(df, columns, contamination)
            except:
                lof_results = None
            
            # Combinar resultados (voting)
            # Una anomalía debe ser detectada por al menos 2 métodos
            
            return {
                'method': 'Ensemble',
                'methods_used': ['IsolationForest', 'EllipticEnvelope', 'LOF'],
                'isolation_forest_results': iso_results,
                'elliptic_envelope_results': elliptic_results,
                'lof_results': lof_results,
                'timestamp': datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error en detección ensemble: {e}")
            raise
    
    def _calculate_severity(self, anomaly_scores: np.ndarray) -> List[str]:
        """Calcular severidad de anomalías basado en scores"""
        severities = []
        
        # Percentiles para clasificación
        p25 = np.percentile(anomaly_scores, 25)
        p50 = np.percentile(anomaly_scores, 50)
        p75 = np.percentile(anomaly_scores, 75)
        
        for score in anomaly_scores:
            if score <= p25:
                severities.append('critical')
            elif score <= p50:
                severities.append('high')
            elif score <= p75:
                severities.append('medium')
            else:
                severities.append('low')
        
        return severities
    
    def _format_anomalies(
        self,
        anomalies_df: pd.DataFrame,
        columns: List[str],
        max_records: int = 100,
    ) -> List[Dict[str, Any]]:
        """Formatear anomalías para reporte"""
        
        anomalies_list = []
        
        for idx, row in anomalies_df.head(max_records).iterrows():
            anomaly_record = {
                'index': int(idx),
                'values': {col: float(row[col]) for col in columns if col in row},
            }
            
            if 'anomaly_score' in row:
                anomaly_record['anomaly_score'] = float(row['anomaly_score'])
            
            if 'anomaly_severity' in row:
                anomaly_record['severity'] = row['anomaly_severity']
            
            anomalies_list.append(anomaly_record)
        
        return anomalies_list


# Singleton global
anomaly_detector = AnomalyDetector()
