from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

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


class KPIAnalysisRequest(BaseModel):
    """Request para análisis de KPIs"""
    numeric_columns: List[str] = Field(..., description="Columnas numéricas a analizar")
    detect_anomalies: bool = Field(True, description="Detectar anomalías")
    anomaly_method: str = Field(
        'isolation_forest',
        description="Método de detección: isolation_forest, ensemble, multivariate, lof"
    )
    contamination: float = Field(
        0.1,
        ge=0.0,
        le=0.5,
        description="Proporción esperada de anomalías (0.0 a 0.5)"
    )


class TextAnalysisRequest(BaseModel):
    """Request para análisis de texto"""
    text_columns: List[str] = Field(..., description="Columnas de texto a analizar")
    use_ollama: bool = Field(True, description="Usar Ollama para análisis de sentimiento")
    extract_entities: bool = Field(False, description="Extraer entidades nombradas")


@router.post("/datasets/{dataset_id}/analyze-text")
async def analyze_text(
    dataset_id: int,
    request: TextAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Analizar columnas de texto de un dataset usando IA local (Ollama)
    
    El análisis incluye:
    - Sentimiento (positivo, negativo, neutral) usando Ollama
    - Extracción de palabras clave
    - Extracción de entidades nombradas (opcional)
    - Métricas de confianza
    
    Si Ollama no está disponible, usa método fallback basado en reglas.
    """
    
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    # Lanzar tarea asíncrona
    task = analyze_text_columns_task.delay(
        dataset_id,
        request.text_columns,
        request.use_ollama,
        request.extract_entities,
    )
    
    logger.info(
        f"Análisis de texto iniciado para dataset {dataset_id}, "
        f"Ollama: {request.use_ollama}, tarea: {task.id}"
    )
    
    return {
        "message": "Análisis de texto iniciado",
        "task_id": task.id,
        "dataset_id": dataset_id,
        "use_ollama": request.use_ollama,
        "extract_entities": request.extract_entities,
    }


@router.post("/datasets/{dataset_id}/calculate-kpis")
async def calculate_kpis(
    dataset_id: int,
    request: KPIAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Calcular KPIs de columnas numéricas con detección de anomalías
    
    Métodos de detección disponibles:
    - isolation_forest: IsolationForest (recomendado, robusto)
    - ensemble: Combina múltiples métodos
    - multivariate: Elliptic Envelope (asume distribución Gaussiana)
    - lof: Local Outlier Factor (densidad local)
    """
    
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    # Validar método
    valid_methods = ['isolation_forest', 'ensemble', 'multivariate', 'lof']
    if request.anomaly_method not in valid_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Método inválido. Debe ser uno de: {', '.join(valid_methods)}"
        )
    
    # Lanzar tarea asíncrona
    task = calculate_kpis_task.delay(
        dataset_id,
        request.numeric_columns,
        request.detect_anomalies,
        request.anomaly_method,
        request.contamination,
    )
    
    logger.info(
        f"Cálculo de KPIs iniciado para dataset {dataset_id}, "
        f"método: {request.anomaly_method}, tarea: {task.id}"
    )
    
    return {
        "message": "Cálculo de KPIs y detección de anomalías iniciado",
        "task_id": task.id,
        "dataset_id": dataset_id,
        "anomaly_method": request.anomaly_method,
        "contamination": request.contamination,
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


@router.get("/anomalies")
async def get_anomalies(
    days_back: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtener resumen de anomalías detectadas"""
    
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    start_date = datetime.utcnow().date() - timedelta(days=days_back)
    
    # Buscar métricas de detección de anomalías
    anomaly_metrics = db.query(AnalyticsSummary).filter(
        AnalyticsSummary.client_id == current_user.client_id,
        AnalyticsSummary.date >= start_date,
        AnalyticsSummary.metric_name == "anomaly_detection"
    ).order_by(AnalyticsSummary.date.desc()).all()
    
    if not anomaly_metrics:
        return {
            "message": "No se encontraron análisis de anomalías",
            "total": 0,
            "anomalies": []
        }
    
    return {
        "total": len(anomaly_metrics),
        "anomalies": [
            {
                "id": m.id,
                "date": m.date.isoformat(),
                "anomaly_percentage": m.metric_value,
                "method": m.metadata.get('method') if m.metadata else None,
                "total_anomalies": m.metadata.get('total_anomalies') if m.metadata else None,
                "severity_distribution": m.metadata.get('severity_distribution') if m.metadata else None,
                "columns_analyzed": m.metadata.get('columns_analyzed') if m.metadata else None,
            }
            for m in anomaly_metrics
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
