"""
Endpoints REST API para Insights
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from app.db.session import get_db
from app.api.schemas.insights_schemas import (
    InsightSummary,
    InsightDetail,
    ClientInsightDetail,
    GlobalStats,
    SearchResult,
    KPISummary,
    TrendSignal,
    TextAnalysisSummary
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/insights", tags=["Insights"])


@router.get("/", response_model=List[InsightSummary])
def list_insights(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    risk_level: Optional[str] = None,
    opportunity_level: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Listar insights más recientes con paginación
    
    Args:
        skip: Registros a saltar
        limit: Máximo de registros
        risk_level: Filtrar por nivel de riesgo
        opportunity_level: Filtrar por nivel de oportunidad
    """
    try:
        query = text("""
            SELECT 
                id,
                client_id,
                summary_text,
                risk_level,
                opportunity_level,
                jsonb_array_length(key_findings) as findings_count,
                generated_at
            FROM ai_insights
            WHERE 1=1
            {risk_filter}
            {opp_filter}
            ORDER BY generated_at DESC
            LIMIT :limit OFFSET :skip
        """.format(
            risk_filter="AND risk_level = :risk_level" if risk_level else "",
            opp_filter="AND opportunity_level = :opportunity_level" if opportunity_level else ""
        ))
        
        params = {"skip": skip, "limit": limit}
        if risk_level:
            params["risk_level"] = risk_level
        if opportunity_level:
            params["opportunity_level"] = opportunity_level
        
        result = db.execute(query, params)
        
        insights = []
        for row in result:
            insights.append(InsightSummary(
                id=row[0],
                client_id=row[1],
                summary_text=row[2],
                risk_level=row[3],
                opportunity_level=row[4],
                findings_count=row[5],
                generated_at=row[6]
            ))
        
        logger.info(f"Listados {len(insights)} insights")
        return insights
        
    except Exception as e:
        logger.error(f"Error listando insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/", response_model=List[SearchResult])
def search_insights(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Buscar en insights, tendencias y análisis de texto
    
    Args:
        q: Término de búsqueda
        limit: Máximo de resultados
    """
    try:
        results = []
        search_term = f"%{q.lower()}%"
        
        # 1. Buscar en insights (summary_text)
        insights_query = text("""
            SELECT 
                client_id,
                summary_text,
                risk_level,
                opportunity_level,
                generated_at
            FROM ai_insights
            WHERE LOWER(summary_text) LIKE :search_term
            ORDER BY generated_at DESC
            LIMIT :limit
        """)
        
        insight_rows = db.execute(insights_query, {
            "search_term": search_term,
            "limit": limit // 2
        }).fetchall()
        
        for row in insight_rows:
            results.append(SearchResult(
                result_type="insight",
                client_id=row[0],
                title=f"Insight - Cliente {row[0]}",
                description=row[1][:200],
                relevance_score=0.9,
                date=row[4]
            ))
        
        # 2. Buscar en tendencias (term)
        trends_query = text("""
            SELECT 
                sector,
                term,
                frequency,
                status,
                period_start
            FROM trend_signals
            WHERE LOWER(term) LIKE :search_term
            ORDER BY frequency DESC
            LIMIT :limit
        """)
        
        trend_rows = db.execute(trends_query, {
            "search_term": search_term,
            "limit": limit // 2
        }).fetchall()
        
        for row in trend_rows:
            results.append(SearchResult(
                result_type="trend",
                client_id=None,
                title=f"Tendencia: {row[1]}",
                description=f"Sector {row[0]}, frecuencia {row[2]}, estado {row[3]}",
                relevance_score=0.8,
                date=row[4]
            ))
        
        # Ordenar por relevancia y fecha
        results.sort(key=lambda x: (x.relevance_score, x.date), reverse=True)
        results = results[:limit]
        
        logger.info(f"Búsqueda '{q}': {len(results)} resultados")
        return results
        
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/global", response_model=GlobalStats)
def get_global_stats(db: Session = Depends(get_db)):
    """
    Obtener estadísticas globales del sistema
    """
    try:
        # Total de clientes con insights
        total_clients_query = text("""
            SELECT COUNT(DISTINCT client_id) FROM ai_insights
        """)
        total_clients = db.execute(total_clients_query).scalar() or 0
        
        # Total de insights
        total_insights_query = text("""
            SELECT COUNT(*) FROM ai_insights
        """)
        total_insights = db.execute(total_insights_query).scalar() or 0
        
        # Total de KPIs
        total_kpis_query = text("""
            SELECT COUNT(*) FROM kpi_summary
        """)
        total_kpis = db.execute(total_kpis_query).scalar() or 0
        
        # Total de tendencias
        total_trends_query = text("""
            SELECT COUNT(*) FROM trend_signals
        """)
        total_trends = db.execute(total_trends_query).scalar() or 0
        
        # Total de análisis de texto
        total_text_query = text("""
            SELECT COUNT(*) FROM text_summary
        """)
        total_text = db.execute(total_text_query).scalar() or 0
        
        # Distribución de riesgo
        risk_dist_query = text("""
            SELECT risk_level, COUNT(*) as count
            FROM ai_insights
            GROUP BY risk_level
        """)
        risk_rows = db.execute(risk_dist_query).fetchall()
        risk_distribution = {row[0]: row[1] for row in risk_rows}
        
        # Distribución de oportunidad
        opp_dist_query = text("""
            SELECT opportunity_level, COUNT(*) as count
            FROM ai_insights
            GROUP BY opportunity_level
        """)
        opp_rows = db.execute(opp_dist_query).fetchall()
        opportunity_distribution = {row[0]: row[1] for row in opp_rows}
        
        # Última actualización
        last_update_query = text("""
            SELECT MAX(generated_at) FROM ai_insights
        """)
        last_update = db.execute(last_update_query).scalar() or datetime.utcnow()
        
        stats = GlobalStats(
            total_clients=total_clients,
            total_insights=total_insights,
            total_kpis=total_kpis,
            total_trends=total_trends,
            total_text_records=total_text,
            risk_distribution=risk_distribution,
            opportunity_distribution=opportunity_distribution,
            last_update=last_update
        )
        
        logger.info("Estadísticas globales obtenidas")
        return stats
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{client_id}", response_model=ClientInsightDetail)
def get_client_insights(
    client_id: int,
    days_back: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Obtener detalle completo de insights para un cliente
    
    Incluye:
    - Insight más reciente
    - KPIs históricos
    - Tendencias detectadas
    - Resumen de análisis de texto
    """
    try:
        # 1. Obtener insight más reciente
        insight_query = text("""
            SELECT 
                id, client_id, summary_text, key_findings,
                risk_level, opportunity_level, metrics,
                generated_at, created_at
            FROM ai_insights
            WHERE client_id = :client_id
            ORDER BY generated_at DESC
            LIMIT 1
        """)
        
        insight_row = db.execute(insight_query, {"client_id": client_id}).fetchone()
        
        insight_detail = None
        if insight_row:
            insight_detail = InsightDetail(
                id=insight_row[0],
                client_id=insight_row[1],
                summary_text=insight_row[2],
                key_findings=insight_row[3] if insight_row[3] else [],
                risk_level=insight_row[4],
                opportunity_level=insight_row[5],
                metrics=insight_row[6],
                generated_at=insight_row[7],
                created_at=insight_row[8]
            )
        
        # 2. Obtener KPIs
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        kpi_query = text("""
            SELECT 
                kpi_name, kpi_value,
                period_start, period_end, calculated_at
            FROM kpi_summary
            WHERE client_id = :client_id
            AND calculated_at >= :cutoff_date
            ORDER BY calculated_at DESC
            LIMIT 50
        """)
        
        kpi_rows = db.execute(kpi_query, {
            "client_id": client_id,
            "cutoff_date": cutoff_date
        }).fetchall()
        
        kpis = [
            KPISummary(
                kpi_name=row[0],
                kpi_value=float(row[1]),
                period_start=row[2],
                period_end=row[3],
                calculated_at=row[4]
            )
            for row in kpi_rows
        ]
        
        # 3. Obtener tendencias (generales, no filtradas por cliente)
        trend_query = text("""
            SELECT 
                sector, term, frequency, delta_pct,
                status, period_start
            FROM trend_signals
            WHERE created_at >= :cutoff_date
            ORDER BY frequency DESC
            LIMIT 20
        """)
        
        trend_rows = db.execute(trend_query, {
            "cutoff_date": cutoff_date
        }).fetchall()
        
        trends = [
            TrendSignal(
                sector=row[0],
                term=row[1],
                frequency=row[2],
                delta_pct=float(row[3]) if row[3] else None,
                status=row[4],
                period_start=row[5]
            )
            for row in trend_rows
        ]
        
        # 4. Obtener resumen de análisis de texto
        text_query = text("""
            SELECT 
                sentiment, sentiment_score, keywords, created_at
            FROM text_summary
            WHERE client_id = :client_id
            AND created_at >= :cutoff_date
            ORDER BY created_at DESC
            LIMIT 20
        """)
        
        text_rows = db.execute(text_query, {
            "client_id": client_id,
            "cutoff_date": cutoff_date
        }).fetchall()
        
        text_analysis = [
            TextAnalysisSummary(
                sentiment=row[0],
                sentiment_score=float(row[1]) if row[1] else None,
                keywords=row[2] if row[2] else [],
                created_at=row[3]
            )
            for row in text_rows
        ]
        
        # 5. Construir respuesta completa
        result = ClientInsightDetail(
            client_id=client_id,
            insight=insight_detail,
            kpis=kpis,
            trends=trends,
            text_analysis=text_analysis
        )
        
        logger.info(f"Detalle obtenido para cliente {client_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error obteniendo insights de cliente {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recompute/{client_id}")
def recompute_client_insights(
    client_id: int,
    days_back: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Recalcular insights para un cliente específico
    
    (Endpoint interno - recomendado solo para admin)
    """
    try:
        from app.data_insights.insight_tasks import generate_insight_for_client_task
        
        # Ejecutar tarea asíncrona
        task = generate_insight_for_client_task.delay(client_id, days_back)
        
        logger.info(f"Tarea de recalculo iniciada para cliente {client_id}: {task.id}")
        
        return {
            "message": "Recálculo iniciado",
            "client_id": client_id,
            "task_id": task.id,
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error iniciando recálculo: {e}")
        raise HTTPException(status_code=500, detail=str(e))
