from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pathlib import Path

from app.database import get_db
from app.models.user import User
from app.models.report import ReportHistory
from app.services.auth import get_current_active_user
from app.workers.report_tasks import generate_client_report_task
from app.logger import get_logger

router = APIRouter(prefix="/reports", tags=["Reportes"])
logger = get_logger()


@router.post("/generate")
async def generate_report(
    config: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Generar reporte para el cliente"""
    
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    # Lanzar tarea asíncrona
    task = generate_client_report_task.delay(
        current_user.client_id,
        current_user.id,
        config
    )
    
    logger.info(f"Generación de reporte iniciada para cliente {current_user.client_id}")
    
    return {
        "message": "Generación de reporte iniciada",
        "task_id": task.id,
    }


@router.get("/")
async def list_reports(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Listar reportes del cliente"""
    
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    reports = db.query(ReportHistory).filter(
        ReportHistory.client_id == current_user.client_id
    ).order_by(ReportHistory.generated_at.desc()).all()
    
    return {
        "total": len(reports),
        "reports": [
            {
                "id": r.id,
                "report_name": r.report_name,
                "report_type": r.report_type,
                "final_score": r.final_score,
                "generated_at": r.generated_at.isoformat(),
            }
            for r in reports
        ]
    }


@router.get("/{report_id}")
async def get_report_details(
    report_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtener detalles de un reporte"""
    
    report = db.query(ReportHistory).filter(ReportHistory.id == report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reporte no encontrado"
        )
    
    if report.client_id != current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para ver este reporte"
        )
    
    return {
        "id": report.id,
        "report_name": report.report_name,
        "report_type": report.report_type,
        "parameters": report.parameters,
        "scores": report.scores,
        "final_score": report.final_score,
        "executive_summary": report.executive_summary,
        "generated_at": report.generated_at.isoformat(),
    }


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Descargar archivo PDF del reporte"""
    
    report = db.query(ReportHistory).filter(ReportHistory.id == report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reporte no encontrado"
        )
    
    if report.client_id != current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para descargar este reporte"
        )
    
    file_path = Path(report.file_path)
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo del reporte no encontrado"
        )
    
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=file_path.name,
    )
