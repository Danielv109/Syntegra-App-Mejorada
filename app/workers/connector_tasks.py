import pandas as pd
from pathlib import Path
from datetime import datetime
from celery import Task

from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.data_source import DataSource
from app.models.dataset import ETLHistory, DatasetStatus
from app.services.data_connectors import validate_connector_config
from app.logger import get_logger
from app.data_processing.processor import process_incoming_data

logger = get_logger()


class ConnectorTask(Task):
    """Clase base para tareas de conectores con reintentos"""
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(base=ConnectorTask, bind=True, name="connectors.ingest_source")
def ingest_source(self, source_id: int):
    """
    Ejecutar ingesta de datos desde un conector (modo simulado)
    """
    db = SessionLocal()
    logger.info(f"Iniciando ingesta desde conector {source_id}")
    
    try:
        # Cargar data source
        source = db.query(DataSource).filter(DataSource.id == source_id).first()
        
        if not source:
            raise ValueError(f"Data source {source_id} no encontrado")
        
        # Actualizar status a processing
        source.status = 'processing'
        db.commit()
        
        # Crear registro ETL
        etl_record = ETLHistory(
            dataset_id=None,
            task_id=self.request.id,
            status=DatasetStatus.PENDING,
            step="Iniciando ingesta de conector",
        )
        db.add(etl_record)
        db.commit()
        
        # Validar configuración
        is_valid, error_msg = validate_connector_config(source.config_json)
        
        if not is_valid:
            logger.error(f"Configuración inválida: {error_msg}")
            
            source.status = 'error'
            etl_record.status = DatasetStatus.FAILED
            etl_record.message = f"Configuración inválida: {error_msg}"
            etl_record.completed_at = datetime.utcnow()
            
            db.commit()
            return {
                "status": "failed",
                "error": error_msg,
            }
        
        # Actualizar ETL status
        etl_record.status = DatasetStatus.PROCESSING
        etl_record.step = "Generando datos de prueba"
        db.commit()
        
        # Generar datos simulados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"dataset/raw/{source_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{timestamp}.csv"
        
        # Generar CSV de prueba con 5 filas
        sample_data = generate_sample_data(source.config_json)
        df = pd.DataFrame(sample_data)
        df.to_csv(output_file, index=False)
        
        logger.info(f"Archivo generado: {output_file}")
        
        # **NUEVO: Procesar datos con data_processing**
        try:
            # Determinar tipo de fuente desde config
            processing_type = source.config_json.get('processing_type', source.type)
            
            # Procesar datos
            processing_result = process_incoming_data(
                raw_data=sample_data,
                source_type=processing_type,
                db=db
            )
            
            logger.info(
                f"Datos procesados: {processing_result['processed_successfully']} exitosos, "
                f"{processing_result['failed']} fallidos"
            )
            
        except Exception as e:
            logger.warning(f"Error procesando datos (continúa de todas formas): {e}")
        
        # Actualizar ETL record
        etl_record.status = DatasetStatus.SUCCESS
        etl_record.step = "Ingesta completada"
        etl_record.message = f"Archivo generado: {output_file}"
        etl_record.completed_at = datetime.utcnow()
        
        # Actualizar data source
        source.last_run_at = datetime.utcnow()
        source.status = 'idle'
        
        db.commit()
        
        logger.info(f"Ingesta completada exitosamente para conector {source_id}")
        
        return {
            "status": "success",
            "source_id": source_id,
            "file_path": str(output_file),
            "rows": len(df),
            "processed_records": processing_result.get('processed_successfully', 0) if 'processing_result' in locals() else 0,
        }
        
    except Exception as e:
        logger.error(f"Error en ingesta de conector {source_id}: {e}")
        
        if 'source' in locals():
            source.status = 'error'
        
        if 'etl_record' in locals():
            etl_record.status = DatasetStatus.FAILED
            etl_record.completed_at = datetime.utcnow()
            etl_record.message = f"Error: {str(e)}"
        
        db.commit()
        raise
        
    finally:
        db.close()


def generate_sample_data(config: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Generar datos de ejemplo basados en configuración"""
    
    connector_type = config.get('type', 'simple_csv')
    
    # Extraer columnas si están definidas
    columns = config.get('columns', ['id', 'name', 'value', 'date'])
    
    # Generar 5 filas de datos de ejemplo
    sample_data = []
    
    for i in range(1, 6):
        row = {}
        for col in columns:
            if 'id' in col.lower():
                row[col] = i
            elif 'name' in col.lower():
                row[col] = f"Sample_{i}"
            elif 'value' in col.lower():
                row[col] = 100.0 * i
            elif 'date' in col.lower():
                row[col] = datetime.now().strftime("%Y-%m-%d")
            else:
                row[col] = f"data_{i}"
        
        sample_data.append(row)
    
    return sample_data
