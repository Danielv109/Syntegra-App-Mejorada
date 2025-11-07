from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User, UserRole
from app.models.analytics import AnalyticsSummary, Trend
from app.services.auth import get_current_active_user
from app.workers.analysis_tasks import (
    analyze_text_columns_task,
    calculate_kpis_task,
    detect_trends_task,
)
from app.logger import get_logger

router = APIRouter(prefix="/analysis", tags=["Análisis"])
logger = get_logger()


@router.post("/datasets/{dataset_id}/analyze-text")
async def analyze_text(
    dataset_id: int,
    text_columns: List[str],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Analizar columnas de texto de un dataset"""
    
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    # Lanzar tarea asíncrona
    task = analyze_text_columns_task.delay(dataset_id, text_columns)
    
    logger.info(f"Análisis de texto iniciado para dataset {dataset_id}, tarea: {task.id}")
    
    return {
        "message": "Análisis de texto iniciado",
        "task_id": task.id,
        "dataset_id": dataset_id,
    }


@router.post("/datasets/{dataset_id}/calculate-kpis")
async def calculate_kpis(
    dataset_id: int,
    numeric_columns: List[str],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Calcular KPIs de columnas numéricas"""
    
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    # Lanzar tarea asíncrona
    task = calculate_kpis_task.delay(dataset_id, numeric_columns)
    
    logger.info(f"Cálculo de KPIs iniciado para dataset {dataset_id}, tarea: {task.id}")
    
    return {
        "message": "Cálculo de KPIs iniciado",
        "task_id": task.id,
        "dataset_id": dataset_id,
    }


@router.get("/metrics")
async def get_metrics(
    days_back: int = 30,
    metric_name: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtener métricas analíticas del cliente"""
    
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    start_date = datetime.utcnow().date() - timedelta(days=days_back)
    
    query = db.query(AnalyticsSummary).filter(
        AnalyticsSummary.client_id == current_user.client_id,
        AnalyticsSummary.date >= start_date,
    )
    
    if metric_name:
        query = query.filter(AnalyticsSummary.metric_name == metric_name)
    
    metrics = query.order_by(AnalyticsSummary.date.desc()).all()
    
    return {
        "total": len(metrics),
        "metrics": [
            {
                "id": m.id,
                "metric_name": m.metric_name,
                "metric_value": m.metric_value,
                "date": m.date.isoformat(),
                "metadata": m.metadata,
            }
            for m in metrics
        ]
    }


@router.post("/detect-trends")
async def detect_trends(
    days_back: int = 30,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Detectar tendencias emergentes"""
    
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    # Lanzar tarea asíncrona
    task = detect_trends_task.delay(current_user.client_id, days_back)
    
    logger.info(f"Detección de tendencias iniciada para cliente {current_user.client_id}")
    
    return {
        "message": "Detección de tendencias iniciada",
        "task_id": task.id,
    }


@router.get("/trends")
async def get_trends(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtener tendencias detectadas"""
    
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    query = db.query(Trend).filter(Trend.client_id == current_user.client_id)
    
    if status_filter:
        query = query.filter(Trend.trend_status == status_filter)
    
    trends = query.order_by(Trend.growth_rate.desc()).all()
    
    return {
        "total": len(trends),
        "trends": [
            {
                "id": t.id,
                "keyword": t.keyword,
                "frequency": t.frequency,
                "growth_rate": t.growth_rate,
                "status": t.trend_status,
                "period_start": t.time_period_start.isoformat(),
                "period_end": t.time_period_end.isoformat(),
            }
            for t in trends
        ]
    }
