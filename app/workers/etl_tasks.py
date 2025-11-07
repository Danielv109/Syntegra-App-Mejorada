import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from celery import Task
from sqlalchemy import text

from app.workers.celery_app import celery_app
from app.database import SessionLocal, engine
from app.models.dataset import Dataset, ETLHistory, DatasetStatus
from app.logger import get_logger

logger = get_logger()


class ETLTask(Task):
    """Clase base para tareas ETL con reintentos"""
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(base=ETLTask, bind=True, name="etl.process_dataset")
def process_dataset_task(self, dataset_id: int):
    """
    Tarea asíncrona para procesar dataset
    """
    db = SessionLocal()
    logger.info(f"Iniciando procesamiento de dataset {dataset_id}")
    
    try:
        # Obtener dataset
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} no encontrado")
        
        # Crear registro de historial ETL
        etl_record = ETLHistory(
            dataset_id=dataset_id,
            task_id=self.request.id,
            status=DatasetStatus.PROCESSING,
            step="Iniciando proceso ETL",
        )
        db.add(etl_record)
        db.commit()
        
        # Actualizar estado del dataset
        dataset.status = DatasetStatus.PROCESSING
        db.commit()
        
        # Paso 1: Leer archivo
        logger.info(f"Leyendo archivo: {dataset.file_path}")
        etl_record.step = "Leyendo archivo"
        db.commit()
        
        df = read_file(dataset.file_path, dataset.file_type)
        
        # Paso 2: Limpieza de datos
        logger.info("Limpiando datos")
        etl_record.step = "Limpiando datos"
        db.commit()
        
        df_clean = clean_dataframe(df)
        
        # Paso 3: Validación de calidad
        logger.info("Validando calidad de datos")
        etl_record.step = "Validando calidad"
        db.commit()
        
        quality_report = validate_data_quality(df_clean)
        
        # Paso 4: Guardar en base de datos
        logger.info("Guardando datos procesados")
        etl_record.step = "Guardando en base de datos"
        db.commit()
        
        # Obtener schema del cliente
        client = dataset.client
        schema_name = client.schema_name
        table_name = f"dataset_{dataset_id}"
        
        # Crear tabla en el schema del cliente
        create_client_table(df_clean, schema_name, table_name)
        
        # Guardar datos
        df_clean.to_sql(
            table_name,
            engine,
            schema=schema_name,
            if_exists="replace",
            index=False,
        )
        
        # Paso 5: Guardar versión procesada
        processed_path = f"dataset/processed/dataset_{dataset_id}.parquet"
        Path(processed_path).parent.mkdir(parents=True, exist_ok=True)
        df_clean.to_parquet(processed_path)
        
        # Actualizar metadata del dataset
        dataset.rows_count = len(df_clean)
        dataset.columns_count = len(df_clean.columns)
        dataset.status = DatasetStatus.SUCCESS
        dataset.processed_at = datetime.utcnow()
        dataset.metadata = {
            "quality_report": quality_report,
            "columns": list(df_clean.columns),
            "dtypes": {col: str(dtype) for col, dtype in df_clean.dtypes.items()},
        }
        
        # Actualizar ETL history
        etl_record.status = DatasetStatus.SUCCESS
        etl_record.completed_at = datetime.utcnow()
        etl_record.message = "Procesamiento completado exitosamente"
        
        db.commit()
        
        logger.info(f"Dataset {dataset_id} procesado exitosamente")
        
        return {
            "status": "success",
            "dataset_id": dataset_id,
            "rows_processed": len(df_clean),
            "columns": list(df_clean.columns),
        }
        
    except Exception as e:
        logger.error(f"Error procesando dataset {dataset_id}: {str(e)}")
        
        # Actualizar estado de error
        if 'dataset' in locals():
            dataset.status = DatasetStatus.FAILED
        
        if 'etl_record' in locals():
            etl_record.status = DatasetStatus.FAILED
            etl_record.completed_at = datetime.utcnow()
            etl_record.error_details = {
                "error": str(e),
                "step": etl_record.step,
            }
        
        db.commit()
        raise
        
    finally:
        db.close()


def read_file(file_path: str, file_type: str) -> pd.DataFrame:
    """Leer archivo según tipo"""
    if file_type == "csv":
        return pd.read_csv(file_path)
    elif file_type in ["xlsx", "xls"]:
        return pd.read_excel(file_path)
    elif file_type == "json":
        return pd.read_json(file_path)
    else:
        raise ValueError(f"Tipo de archivo no soportado: {file_type}")


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Limpieza básica de dataframe"""
    # Eliminar duplicados completos
    df = df.drop_duplicates()
    
    # Eliminar filas completamente nulas
    df = df.dropna(how="all")
    
    # Normalizar nombres de columnas
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    
    # Convertir tipos de datos
    for col in df.columns:
        # Intentar convertir a numérico
        if df[col].dtype == "object":
            try:
                df[col] = pd.to_numeric(df[col], errors="ignore")
            except:
                pass
    
    return df


def validate_data_quality(df: pd.DataFrame) -> dict:
    """Validar calidad de datos"""
    report = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "duplicates": df.duplicated().sum(),
        "null_counts": df.isnull().sum().to_dict(),
        "null_percentage": (df.isnull().sum() / len(df) * 100).to_dict(),
    }
    
    return report


def create_client_table(df: pd.DataFrame, schema_name: str, table_name: str):
    """Crear tabla en esquema del cliente"""
    with engine.connect() as conn:
        # Crear esquema si no existe
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        conn.commit()
