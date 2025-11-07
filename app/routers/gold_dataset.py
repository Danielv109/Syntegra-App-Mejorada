from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.gold_dataset import GoldDataset
from app.services.auth import get_current_active_user
from app.logger import get_logger

router = APIRouter(prefix="/gold-dataset", tags=["Gold Dataset"])
logger = get_logger()


class GoldDatasetCreate(BaseModel):
    text: str
    predicted_label: Optional[str] = None
    human_label: str
    confidence_score: Optional[int] = None
    context: Optional[dict] = None


@router.post("/corrections", status_code=status.HTTP_201_CREATED)
async def create_correction(
    correction: GoldDatasetCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Guardar corrección humana para entrenamiento futuro"""
    
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    gold_entry = GoldDataset(
        client_id=current_user.client_id,
        text=correction.text,
        predicted_label=correction.predicted_label,
        human_label=correction.human_label,
        confidence_score=correction.confidence_score,
        context=correction.context,
        corrected_by=current_user.id,
    )
    
    db.add(gold_entry)
    db.commit()
    db.refresh(gold_entry)
    
    logger.info(f"Corrección guardada en gold dataset por usuario {current_user.username}")
    
    return {
        "message": "Corrección guardada exitosamente",
        "id": gold_entry.id,
    }


@router.get("/corrections")
async def list_corrections(
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Listar correcciones del gold dataset"""
    
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    corrections = db.query(GoldDataset).filter(
        GoldDataset.client_id == current_user.client_id
    ).order_by(GoldDataset.corrected_at.desc()).limit(limit).all()
    
    return {
        "total": len(corrections),
        "corrections": [
            {
                "id": c.id,
                "text": c.text[:200],
                "predicted_label": c.predicted_label,
                "human_label": c.human_label,
                "confidence_score": c.confidence_score,
                "corrected_at": c.corrected_at.isoformat(),
            }
            for c in corrections
        ]
    }


@router.get("/stats")
async def get_gold_dataset_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtener estadísticas del gold dataset"""
    
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    total_corrections = db.query(GoldDataset).filter(
        GoldDataset.client_id == current_user.client_id
    ).count()
    
    # Contar por etiqueta
    from sqlalchemy import func
    labels_count = db.query(
        GoldDataset.human_label,
        func.count(GoldDataset.id).label('count')
    ).filter(
        GoldDataset.client_id == current_user.client_id
    ).group_by(GoldDataset.human_label).all()
    
    return {
        "total_corrections": total_corrections,
        "labels_distribution": {label: count for label, count in labels_count},
    }
