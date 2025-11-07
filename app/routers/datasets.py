from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
import shutil
import json

from app.database import get_db
from app.models.user import User, UserRole
from app.models.dataset import Dataset, ETLHistory, DatasetStatus
from app.schemas.dataset import DatasetResponse, DatasetCreate, ETLHistoryResponse
from app.services.auth import get_current_active_user, RoleChecker
from app.workers.etl_tasks import process_dataset_task
from app.config import get_settings
from app.logger import get_logger

router = APIRouter(prefix="/datasets", tags=["Datasets"])
settings = get_settings()
logger = get_logger()

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}


@router.post("/upload", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Subir dataset para procesamiento"""
    
    # Verificar que el usuario tenga cliente asignado
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    # Validar extensión
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no soportado. Permitidos: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validar tamaño
    file.file.seek(0, 2)  # Ir al final del archivo
    file_size = file.file.tell()  # Obtener tamaño
    file.file.seek(0)  # Volver al inicio
    
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024  # Convertir a bytes
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Archivo muy grande. Máximo: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )
    
    # Guardar archivo
    raw_dir = Path("dataset/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = raw_dir / f"client_{current_user.client_id}_{name}_{Path(file.filename).name}"
    
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Crear registro en base de datos
    new_dataset = Dataset(
        client_id=current_user.client_id,
        name=name,
        description=description,
        file_path=str(file_path),
        file_type=file_extension.replace(".", ""),
        status=DatasetStatus.PENDING,
        uploaded_by=current_user.id,
    )
    
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)
    
    # Lanzar tarea asíncrona de procesamiento
    task = process_dataset_task.delay(new_dataset.id)
    
    logger.info(f"Dataset {new_dataset.id} subido. Tarea ETL: {task.id}")
    
    return new_dataset


@router.get("/", response_model=List[DatasetResponse])
async def list_datasets(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Listar datasets del cliente"""
    
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    datasets = db.query(Dataset).filter(
        Dataset.client_id == current_user.client_id
    ).order_by(Dataset.uploaded_at.desc()).all()
    
    return datasets


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtener detalles de un dataset"""
    
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset no encontrado"
        )
    
    # Verificar permisos
    if current_user.role != UserRole.ADMIN_GLOBAL and dataset.client_id != current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para ver este dataset"
        )
    
    return dataset


@router.get("/{dataset_id}/quality-report")
async def get_quality_report(
    dataset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtener reporte de calidad detallado del dataset"""
    
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset no encontrado"
        )
    
    # Verificar permisos
    if current_user.role != UserRole.ADMIN_GLOBAL and dataset.client_id != current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos"
        )
    
    # Obtener reporte de calidad
    if dataset.metadata and 'quality_report' in dataset.metadata:
        return dataset.metadata['quality_report']
    
    # Si no hay reporte en metadata, buscar archivo
    quality_report_path = f"dataset/processed/quality_report_{dataset_id}.json"
    if Path(quality_report_path).exists():
        with open(quality_report_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Reporte de calidad no disponible. El dataset debe ser procesado primero."
    )


@router.get("/{dataset_id}/quality-report/download")
async def download_quality_report(
    dataset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Descargar reporte de calidad en formato JSON"""
    
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset no encontrado"
        )
    
    # Verificar permisos
    if current_user.role != UserRole.ADMIN_GLOBAL and dataset.client_id != current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos"
        )
    
    quality_report_path = f"dataset/processed/quality_report_{dataset_id}.json"
    
    if not Path(quality_report_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reporte de calidad no encontrado"
        )
    
    return FileResponse(
        path=quality_report_path,
        media_type="application/json",
        filename=f"quality_report_dataset_{dataset_id}.json"
    )


@router.get("/{dataset_id}/etl-history", response_model=List[ETLHistoryResponse])
async def get_etl_history(
    dataset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtener historial de procesamiento ETL"""
    
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset no encontrado"
        )
    
    # Verificar permisos
    if current_user.role != UserRole.ADMIN_GLOBAL and dataset.client_id != current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos"
        )
    
    history = db.query(ETLHistory).filter(
        ETLHistory.dataset_id == dataset_id
    ).order_by(ETLHistory.started_at.desc()).all()
    
    return history


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: int,
    current_user: User = Depends(
        RoleChecker([UserRole.ADMIN_GLOBAL, UserRole.CLIENTE_ADMIN])
    ),
    db: Session = Depends(get_db),
):
    """Eliminar dataset"""
    
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset no encontrado"
        )
    
    # Verificar permisos
    if current_user.role != UserRole.ADMIN_GLOBAL and dataset.client_id != current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos"
        )
    
    # Eliminar archivo físico
    try:
        Path(dataset.file_path).unlink(missing_ok=True)
    except:
        pass
    
    # Eliminar de base de datos
    db.delete(dataset)
    db.commit()
    
    logger.info(f"Dataset {dataset_id} eliminado por {current_user.username}")
    
    return None
