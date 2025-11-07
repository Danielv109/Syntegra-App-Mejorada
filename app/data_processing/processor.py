from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.processed_data import ProcessedData
from app.data_processing.normalizers import normalize_data
from app.logger import get_logger

logger = get_logger()


def process_incoming_data(
    raw_data: List[Dict[str, Any]],
    source_type: str,
    db: Session
) -> Dict[str, Any]:
    """
    Procesar datos entrantes: limpiar, normalizar y guardar
    
    Args:
        raw_data: Lista de registros crudos
        source_type: Tipo de fuente (restaurant, retail, service)
        db: Sesión de base de datos
        
    Returns:
        Resumen del procesamiento
    """
    logger.info(f"Procesando {len(raw_data)} registros de tipo '{source_type}'")
    
    processed_count = 0
    failed_count = 0
    errors = []
    
    for i, data in enumerate(raw_data):
        try:
            # Normalizar datos según tipo de fuente
            normalized = normalize_data(data, source_type)
            
            # Crear registro en base de datos
            processed_record = ProcessedData(
                source_type=source_type,
                data=normalized,
            )
            
            db.add(processed_record)
            processed_count += 1
            
        except Exception as e:
            failed_count += 1
            error_msg = f"Error procesando registro {i}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    # Commit en batch
    try:
        db.commit()
        logger.info(f"Procesamiento completado: {processed_count} exitosos, {failed_count} fallidos")
    except Exception as e:
        db.rollback()
        logger.error(f"Error guardando en base de datos: {e}")
        raise
    
    return {
        'total_records': len(raw_data),
        'processed_successfully': processed_count,
        'failed': failed_count,
        'errors': errors[:10],  # Primeros 10 errores
    }


def process_single_record(
    data: Dict[str, Any],
    source_type: str,
    db: Session
) -> ProcessedData:
    """
    Procesar un solo registro
    
    Args:
        data: Datos crudos
        source_type: Tipo de fuente
        db: Sesión de base de datos
        
    Returns:
        Registro procesado
    """
    # Normalizar
    normalized = normalize_data(data, source_type)
    
    # Guardar
    processed_record = ProcessedData(
        source_type=source_type,
        data=normalized,
    )
    
    db.add(processed_record)
    db.commit()
    db.refresh(processed_record)
    
    logger.info(f"Registro procesado: ID {processed_record.id}")
    
    return processed_record


def get_processed_data(
    db: Session,
    source_type: str = None,
    limit: int = 100,
    offset: int = 0
) -> List[ProcessedData]:
    """
    Obtener datos procesados de la base de datos
    
    Args:
        db: Sesión de base de datos
        source_type: Filtrar por tipo de fuente (opcional)
        limit: Límite de registros
        offset: Offset para paginación
        
    Returns:
        Lista de registros procesados
    """
    query = db.query(ProcessedData)
    
    if source_type:
        query = query.filter(ProcessedData.source_type == source_type)
    
    records = query.order_by(ProcessedData.created_at.desc()).offset(offset).limit(limit).all()
    
    return records


def delete_old_processed_data(db: Session, days_old: int = 90) -> int:
    """
    Eliminar datos procesados antiguos
    
    Args:
        db: Sesión de base de datos
        days_old: Días de antigüedad
        
    Returns:
        Número de registros eliminados
    """
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    deleted = db.query(ProcessedData).filter(
        ProcessedData.created_at < cutoff_date
    ).delete()
    
    db.commit()
    
    logger.info(f"Eliminados {deleted} registros antiguos (>{days_old} días)")
    
    return deleted
