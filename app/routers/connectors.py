from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User, UserRole
from app.models.data_source import DataSource
from app.schemas.data_source import DataSourceCreate, DataSourceResponse, ConnectorRunResponse
from app.services.auth import get_current_active_user
from app.services.data_connectors import (
    create_connector,
    get_connector,
    run_connector,
    validate_connector_config,
)
from app.logger import get_logger

router = APIRouter(prefix="/connectors", tags=["Data Connectors"])
logger = get_logger()


@router.post("/", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_data_connector(
    connector_data: DataSourceCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Crear un nuevo conector de datos"""
    
    # Verificar permisos
    if current_user.role != UserRole.ADMIN_GLOBAL:
        if current_user.client_id != connector_data.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para crear conectores para este cliente"
            )
    
    # Validar configuración
    is_valid, error_msg = validate_connector_config(connector_data.config_json)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuración inválida: {error_msg}"
        )
    
    # Crear conector
    connector = create_connector(db, connector_data.dict())
    
    logger.info(f"Conector creado: {connector.id} por usuario {current_user.username}")
    
    return connector


@router.get("/", response_model=List[DataSourceResponse])
async def list_connectors(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Listar conectores del cliente"""
    
    query = db.query(DataSource)
    
    # Filtrar por cliente si no es admin global
    if current_user.role != UserRole.ADMIN_GLOBAL:
        if not current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no tiene cliente asignado"
            )
        query = query.filter(DataSource.client_id == current_user.client_id)
    
    connectors = query.offset(skip).limit(limit).all()
    
    return connectors


@router.get("/{connector_id}", response_model=DataSourceResponse)
async def get_data_connector(
    connector_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtener detalles de un conector"""
    
    connector = get_connector(db, connector_id)
    
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conector no encontrado"
        )
    
    # Verificar permisos
    if current_user.role != UserRole.ADMIN_GLOBAL:
        if connector.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para ver este conector"
            )
    
    return connector


@router.post("/{connector_id}/run", response_model=ConnectorRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_data_connector(
    connector_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Ejecutar ingesta de un conector"""
    
    connector = get_connector(db, connector_id)
    
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conector no encontrado"
        )
    
    # Verificar permisos
    if current_user.role != UserRole.ADMIN_GLOBAL:
        if connector.client_id != current_user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para ejecutar este conector"
            )
    
    # Verificar que no esté corriendo
    if connector.status == 'processing':
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El conector ya está en ejecución"
        )
    
    # Encolar tarea
    task_id = run_connector(connector_id)
    
    logger.info(f"Conector {connector_id} encolado por usuario {current_user.username}")
    
    return ConnectorRunResponse(
        message="Ingesta iniciada",
        task_id=task_id,
        source_id=connector_id,
    )
