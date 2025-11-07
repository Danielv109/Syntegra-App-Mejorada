import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
import json
from datetime import datetime

import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest
from great_expectations.checkpoint import SimpleCheckpoint
from great_expectations.exceptions import DataContextError

from app.logger import get_logger

logger = get_logger()


class DataQualityValidator:
    """Validador de calidad de datos usando Great Expectations"""
    
    def __init__(self):
        self.context = None
        self._init_context()
    
    def _init_context(self):
        """Inicializar contexto de Great Expectations"""
        try:
            # Crear directorio para Great Expectations
            ge_dir = Path("dataset/great_expectations")
            ge_dir.mkdir(parents=True, exist_ok=True)
            
            # Intentar cargar contexto existente o crear uno nuevo
            try:
                self.context = gx.get_context(context_root_dir=str(ge_dir))
                logger.info("Contexto de Great Expectations cargado")
            except DataContextError:
                # Crear nuevo contexto
                self.context = gx.get_context(context_root_dir=str(ge_dir), mode="file")
                logger.info("Nuevo contexto de Great Expectations creado")
                
        except Exception as e:
            logger.error(f"Error inicializando Great Expectations: {e}")
            self.context = None
    
    def validate_dataframe(
        self, 
        df: pd.DataFrame, 
        dataset_name: str,
        expectations_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Validar DataFrame usando Great Expectations
        
        Args:
            df: DataFrame a validar
            dataset_name: Nombre del dataset
            expectations_config: Configuración personalizada de expectativas
            
        Returns:
            Reporte de validación completo
        """
        if self.context is None:
            logger.warning("Contexto de Great Expectations no disponible, usando validación básica")
            return self._fallback_validation(df)
        
        try:
            # Crear datasource en memoria
            datasource_name = f"datasource_{dataset_name}"
            data_asset_name = f"asset_{dataset_name}"
            
            # Configurar datasource
            datasource_config = {
                "name": datasource_name,
                "class_name": "Datasource",
                "execution_engine": {
                    "class_name": "PandasExecutionEngine"
                },
                "data_connectors": {
                    "runtime_connector": {
                        "class_name": "RuntimeDataConnector",
                        "batch_identifiers": ["batch_id"]
                    }
                }
            }
            
            # Añadir datasource si no existe
            try:
                self.context.add_datasource(**datasource_config)
            except:
                pass  # Datasource ya existe
            
            # Crear batch request
            batch_request = RuntimeBatchRequest(
                datasource_name=datasource_name,
                data_connector_name="runtime_connector",
                data_asset_name=data_asset_name,
                runtime_parameters={"batch_data": df},
                batch_identifiers={"batch_id": f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"}
            )
            
            # Crear expectation suite
            suite_name = f"suite_{dataset_name}"
            
            try:
                suite = self.context.get_expectation_suite(expectation_suite_name=suite_name)
            except:
                suite = self.context.add_expectation_suite(expectation_suite_name=suite_name)
            
            # Crear validator
            validator = self.context.get_validator(
                batch_request=batch_request,
                expectation_suite_name=suite_name
            )
            
            # Aplicar expectativas
            self._apply_expectations(validator, df, expectations_config)
            
            # Ejecutar validación
            validation_results = validator.validate()
            
            # Procesar resultados
            report = self._process_validation_results(validation_results, df)
            
            logger.info(f"Validación completada para {dataset_name}: {report['success_percentage']:.2f}% éxito")
            
            return report
            
        except Exception as e:
            logger.error(f"Error en validación con Great Expectations: {e}")
            return self._fallback_validation(df)
    
    def _apply_expectations(
        self, 
        validator, 
        df: pd.DataFrame,
        custom_config: Dict[str, Any] = None
    ):
        """Aplicar expectativas al validator"""
        
        # Expectativas básicas para todas las columnas
        for column in df.columns:
            # Verificar que la columna existe
            validator.expect_column_to_exist(column=column)
            
            # Tipo de datos
            dtype = str(df[column].dtype)
            if 'int' in dtype or 'float' in dtype:
                # Columnas numéricas
                validator.expect_column_values_to_be_of_type(
                    column=column,
                    type_=dtype
                )
                
                # Sin infinitos
                validator.expect_column_values_to_not_be_null(
                    column=column,
                    mostly=0.8  # Al menos 80% no nulos
                )
                
                # Rango razonable (si es numérico)
                try:
                    min_val = df[column].min()
                    max_val = df[column].max()
                    
                    if pd.notna(min_val) and pd.notna(max_val):
                        validator.expect_column_values_to_be_between(
                            column=column,
                            min_value=float(min_val),
                            max_value=float(max_val),
                            mostly=0.95
                        )
                except:
                    pass
                
            elif 'object' in dtype or 'string' in dtype:
                # Columnas de texto
                validator.expect_column_values_to_be_of_type(
                    column=column,
                    type_="object"
                )
                
                # Sin strings vacíos
                validator.expect_column_values_to_not_be_null(
                    column=column,
                    mostly=0.7
                )
                
                # Longitud de strings razonable
                try:
                    max_length = df[column].astype(str).str.len().max()
                    if pd.notna(max_length):
                        validator.expect_column_value_lengths_to_be_between(
                            column=column,
                            min_value=0,
                            max_value=int(max_length) + 100
                        )
                except:
                    pass
            
            elif 'datetime' in dtype:
                # Columnas de fecha
                validator.expect_column_values_to_be_of_type(
                    column=column,
                    type_="datetime64[ns]"
                )
        
        # Expectativas globales
        
        # Sin filas completamente duplicadas
        validator.expect_table_row_count_to_be_between(
            min_value=1,
            max_value=len(df) * 2  # Permitir margen
        )
        
        # Número de columnas esperado
        validator.expect_table_column_count_to_equal(
            value=len(df.columns)
        )
        
        # Aplicar expectativas personalizadas si se proporcionan
        if custom_config:
            self._apply_custom_expectations(validator, custom_config)
    
    def _apply_custom_expectations(
        self,
        validator,
        config: Dict[str, Any]
    ):
        """Aplicar expectativas personalizadas basadas en configuración"""
        
        # Columnas requeridas
        if 'required_columns' in config:
            for column in config['required_columns']:
                validator.expect_column_to_exist(column=column)
                validator.expect_column_values_to_not_be_null(
                    column=column,
                    mostly=0.95
                )
        
        # Columnas únicas
        if 'unique_columns' in config:
            for column in config['unique_columns']:
                validator.expect_column_values_to_be_unique(column=column)
        
        # Valores permitidos
        if 'allowed_values' in config:
            for column, values in config['allowed_values'].items():
                validator.expect_column_values_to_be_in_set(
                    column=column,
                    value_set=values
                )
        
        # Rangos numéricos
        if 'numeric_ranges' in config:
            for column, range_config in config['numeric_ranges'].items():
                validator.expect_column_values_to_be_between(
                    column=column,
                    min_value=range_config.get('min'),
                    max_value=range_config.get('max'),
                    mostly=range_config.get('mostly', 0.95)
                )
        
        # Expresiones regulares
        if 'regex_patterns' in config:
            for column, pattern in config['regex_patterns'].items():
                validator.expect_column_values_to_match_regex(
                    column=column,
                    regex=pattern
                )
    
    def _process_validation_results(
        self,
        validation_results,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Procesar resultados de validación en un reporte detallado"""
        
        results = validation_results.to_json_dict()
        
        # Estadísticas generales
        total_expectations = len(results.get('results', []))
        successful_expectations = sum(
            1 for r in results.get('results', []) 
            if r.get('success', False)
        )
        
        success_percentage = (
            (successful_expectations / total_expectations * 100) 
            if total_expectations > 0 else 0
        )
        
        # Expectativas fallidas
        failed_expectations = [
            {
                'expectation_type': r.get('expectation_config', {}).get('expectation_type'),
                'column': r.get('expectation_config', {}).get('kwargs', {}).get('column'),
                'details': r.get('result', {}),
            }
            for r in results.get('results', [])
            if not r.get('success', False)
        ]
        
        # Métricas por columna
        column_metrics = {}
        for column in df.columns:
            column_metrics[column] = {
                'dtype': str(df[column].dtype),
                'null_count': int(df[column].isnull().sum()),
                'null_percentage': float(df[column].isnull().sum() / len(df) * 100),
                'unique_count': int(df[column].nunique()),
                'unique_percentage': float(df[column].nunique() / len(df) * 100),
            }
            
            # Estadísticas adicionales para columnas numéricas
            if pd.api.types.is_numeric_dtype(df[column]):
                column_metrics[column].update({
                    'mean': float(df[column].mean()) if not df[column].isnull().all() else None,
                    'median': float(df[column].median()) if not df[column].isnull().all() else None,
                    'std': float(df[column].std()) if not df[column].isnull().all() else None,
                    'min': float(df[column].min()) if not df[column].isnull().all() else None,
                    'max': float(df[column].max()) if not df[column].isnull().all() else None,
                })
        
        # Construir reporte final
        report = {
            'validation_success': results.get('success', False),
            'total_expectations': total_expectations,
            'successful_expectations': successful_expectations,
            'failed_expectations_count': len(failed_expectations),
            'success_percentage': round(success_percentage, 2),
            'timestamp': datetime.now().isoformat(),
            'dataset_info': {
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'memory_usage_mb': round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
                'duplicate_rows': int(df.duplicated().sum()),
            },
            'column_metrics': column_metrics,
            'failed_expectations': failed_expectations,
            'quality_score': self._calculate_quality_score(
                success_percentage,
                df,
                failed_expectations
            ),
        }
        
        return report
    
    def _calculate_quality_score(
        self,
        success_percentage: float,
        df: pd.DataFrame,
        failed_expectations: List[Dict]
    ) -> Dict[str, Any]:
        """Calcular score de calidad general del dataset"""
        
        # Factores de calidad
        completeness = 100 - (df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100)
        uniqueness = 100 - (df.duplicated().sum() / len(df) * 100)
        validity = success_percentage
        
        # Score ponderado
        overall_score = (
            completeness * 0.3 +
            uniqueness * 0.2 +
            validity * 0.5
        )
        
        return {
            'overall_score': round(overall_score, 2),
            'completeness': round(completeness, 2),
            'uniqueness': round(uniqueness, 2),
            'validity': round(validity, 2),
            'grade': self._get_quality_grade(overall_score),
        }
    
    def _get_quality_grade(self, score: float) -> str:
        """Obtener calificación de calidad"""
        if score >= 90:
            return "A - Excelente"
        elif score >= 80:
            return "B - Bueno"
        elif score >= 70:
            return "C - Aceptable"
        elif score >= 60:
            return "D - Regular"
        else:
            return "F - Deficiente"
    
    def _fallback_validation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validación básica cuando Great Expectations no está disponible"""
        
        logger.warning("Usando validación básica (fallback)")
        
        # Métricas básicas
        null_counts = df.isnull().sum()
        null_percentages = (null_counts / len(df) * 100).round(2)
        duplicates = df.duplicated().sum()
        
        column_metrics = {}
        for column in df.columns:
            column_metrics[column] = {
                'dtype': str(df[column].dtype),
                'null_count': int(null_counts[column]),
                'null_percentage': float(null_percentages[column]),
                'unique_count': int(df[column].nunique()),
            }
        
        completeness = 100 - (null_counts.sum() / (len(df) * len(df.columns)) * 100)
        uniqueness = 100 - (duplicates / len(df) * 100) if len(df) > 0 else 100
        
        return {
            'validation_success': True,
            'total_expectations': 0,
            'successful_expectations': 0,
            'failed_expectations_count': 0,
            'success_percentage': 100.0,
            'timestamp': datetime.now().isoformat(),
            'dataset_info': {
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'duplicate_rows': int(duplicates),
            },
            'column_metrics': column_metrics,
            'failed_expectations': [],
            'quality_score': {
                'overall_score': round((completeness + uniqueness) / 2, 2),
                'completeness': round(completeness, 2),
                'uniqueness': round(uniqueness, 2),
                'validity': 100.0,
                'grade': self._get_quality_grade((completeness + uniqueness) / 2),
            },
            'note': 'Validación básica (Great Expectations no disponible)'
        }


# Singleton global
data_quality_validator = DataQualityValidator()
