"""
Router REST para endpoints de insights
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import List, Optional
import logging

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

router = APIRouter(prefix="/api/v1/insights", tags=["Insights"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[InsightSummary])
async def list_insights(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    risk_level: Optional[str] = None,
    opportunity_level: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Listar insights más recientes con paginación y filtros
    
    Query params:
    - skip: Offset para paginación
    - limit: Límite de resultados
    - risk_level: Filtrar por nivel de riesgo
    - opportunity_level: Filtrar por nivel de oportunidad
    """
    try:
        query = """
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
        """
        
        params = {"skip": skip, "limit": limit}
        
        if risk_level:
            query += " AND risk_level = :risk_level"
            params["risk_level"] = risk_level
        
        if opportunity_level:
            query += " AND opportunity_level = :opportunity_level"
            params["opportunity_level"] = opportunity_level
        
        query += " ORDER BY generated_at DESC OFFSET :skip LIMIT :limit"
        
        result = db.execute(text(query), params)
        
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
        
        return insights
        
    except Exception as e:
        logger.error(f"Error listando insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{client_id}", response_model=ClientInsightDetail)
async def get_client_insight(
    client_id: int,
    days_back: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Obtener detalle completo de análisis para un cliente
    
    Incluye:
    - Insight más reciente
    - KPIs del período
    - Tendencias detectadas
    - Análisis de texto
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
        
        insight_result = db.execute(insight_query, {"client_id": client_id}).fetchone()
        
        insight = None
        if insight_result:
            insight = InsightDetail(
                id=insight_result[0],
                client_id=insight_result[1],
                summary_text=insight_result[2],
                key_findings=insight_result[3] if insight_result[3] else [],
                risk_level=insight_result[4],
                opportunity_level=insight_result[5],
                metrics=insight_result[6] if insight_result[6] else {},
                generated_at=insight_result[7],
                created_at=insight_result[8]
            )
        
        # 2. Obtener KPIs
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        kpi_query = text("""
            SELECT 
                kpi_name, kpi_value, period_start, period_end, calculated_at
            FROM kpi_summary
            WHERE client_id = :client_id
            AND calculated_at >= :cutoff_date
            ORDER BY calculated_at DESC
        """)
        
        kpi_result = db.execute(kpi_query, {
            "client_id": client_id,
            "cutoff_date": cutoff_date
        })
        
        kpis = []
        for row in kpi_result:
            kpis.append(KPISummary(
                kpi_name=row[0],
                kpi_value=float(row[1]),
                period_start=row[2],
                period_end=row[3],
                calculated_at=row[4]
            ))
        
        # 3. Obtener tendencias (generales del período)
        trend_query = text("""
            SELECT 
                sector, term, frequency, delta_pct, status, period_start
            FROM trend_signals
            WHERE period_start >= :cutoff_date
            ORDER BY frequency DESC
            LIMIT 20
        """)
        
        trend_result = db.execute(trend_query, {"cutoff_date": cutoff_date})
        
        trends = []
        for row in trend_result:
            trends.append(TrendSignal(
                sector=row[0],
                term=row[1],
                frequency=row[2],
                delta_pct=float(row[3]) if row[3] else 0.0,
                status=row[4],
                period_start=row[5]
            ))
        
        # 4. Obtener análisis de texto
        text_query = text("""
            SELECT 
                sentiment, sentiment_score, keywords, created_at
            FROM text_summary
            WHERE client_id = :client_id
            AND created_at >= :cutoff_date
            ORDER BY created_at DESC
            LIMIT 20
        """)
        
        text_result = db.execute(text_query, {
            "client_id": client_id,
            "cutoff_date": cutoff_date
        })
        
        text_analysis = []
        for row in text_result:
            text_analysis.append(TextAnalysisSummary(
                sentiment=row[0] if row[0] else 'neutral',
                sentiment_score=float(row[1]) if row[1] else 0.0,
                keywords=row[2] if row[2] else [],
                created_at=row[3]
            ))
        
        # Construir respuesta
        return ClientInsightDetail(
            client_id=client_id,
            insight=insight,
            kpis=kpis,
            trends=trends,
            text_analysis=text_analysis
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo detalle de cliente {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/global", response_model=GlobalStats)
async def get_global_stats(db: Session = Depends(get_db)):
    """
    Obtener estadísticas globales del sistema
    """
    try:
        stats_query = text("""
            SELECT 
                (SELECT COUNT(DISTINCT client_id) FROM ai_insights) as total_clients,
                (SELECT COUNT(*) FROM ai_insights) as total_insights,
                (SELECT COUNT(*) FROM kpi_summary) as total_kpis,
                (SELECT COUNT(*) FROM trend_signals) as total_trends,
                (SELECT COUNT(*) FROM text_summary) as total_text_records,
                (SELECT COUNT(*) FROM ai_insights WHERE risk_level IN ('high', 'critical')) as high_risk_clients,
                (SELECT COUNT(*) FROM ai_insights WHERE opportunity_level = 'high') as high_opportunity_clients,
                (SELECT COUNT(*) FROM trend_signals WHERE status = 'emergent') as emergent_trends_count
        """)
        
        result = db.execute(stats_query).fetchone()
        
        return GlobalStats(
            total_clients=result[0] if result[0] else 0,
            total_insights=result[1] if result[1] else 0,
            total_kpis=result[2] if result[2] else 0,
            total_trends=result[3] if result[3] else 0,
            total_text_records=result[4] if result[4] else 0,
            high_risk_clients=result[5] if result[5] else 0,
            high_opportunity_clients=result[6] if result[6] else 0,
            emergent_trends_count=result[7] if result[7] else 0
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas globales: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/", response_model=List[SearchResult])
async def search_insights(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Buscar en insights, tendencias y KPIs por palabra clave
    
    Query params:
    - q: Término de búsqueda
    - limit: Límite de resultados
    """
    try:
        results = []
        search_term = f"%{q.lower()}%"
        
        # Buscar en insights
        insight_query = text("""
            SELECT 
                client_id,
                summary_text,
                generated_at
            FROM ai_insights
            WHERE LOWER(summary_text) LIKE :search_term
            OR EXISTS (
                SELECT 1 FROM jsonb_array_elements_text(key_findings) finding
                WHERE LOWER(finding) LIKE :search_term
            )
            ORDER BY generated_at DESC
            LIMIT :limit
        """)
        
        insight_result = db.execute(insight_query, {
            "search_term": search_term,
            "limit": limit
        })
        
        for row in insight_result:
            results.append(SearchResult(
                type="insight",
                client_id=row[0],
                content=row[1][:200],
                relevance_score=1.0,
                created_at=row[2]
            ))
        
        # Buscar en tendencias
        trend_query = text("""
            SELECT 
                term,
                sector,
                frequency,
                created_at
            FROM trend_signals
            WHERE LOWER(term) LIKE :search_term
            OR LOWER(sector) LIKE :search_term
            ORDER BY frequency DESC, created_at DESC
            LIMIT :limit
        """)
        
        trend_result = db.execute(trend_query, {
            "search_term": search_term,
            "limit": limit
        })
        
        for row in trend_result:
            results.append(SearchResult(
                type="trend",
                content=f"Tendencia: {row[0]} (sector: {row[1]}, freq: {row[2]})",
                relevance_score=0.8,
                created_at=row[3]
            ))
        
        # Buscar en KPIs
        kpi_query = text("""
            SELECT 
                client_id,
                kpi_name,
                kpi_value,
                calculated_at
            FROM kpi_summary
            WHERE LOWER(kpi_name) LIKE :search_term
            ORDER BY calculated_at DESC
            LIMIT :limit
        """)
        
        kpi_result = db.execute(kpi_query, {
            "search_term": search_term,
            "limit": limit
        })
        
        for row in kpi_result:
            results.append(SearchResult(
                type="kpi",
                client_id=row[0],
                content=f"KPI: {row[1]} = {row[2]:.2f}",
                relevance_score=0.7,
                created_at=row[3]
            ))
        
        # Ordenar por relevancia y fecha
        results.sort(key=lambda x: (x.relevance_score, x.created_at), reverse=True)
        
        return results[:limit]
        
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recompute/{client_id}")
async def recompute_insight(
    client_id: int,
    days_back: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Recalcular insights para un cliente específico
    
    Endpoint administrativo para regenerar análisis
    """
    try:
        from app.data_insights.insight_tasks import generate_insight_for_client_task
        
        # Ejecutar task asíncrono
        task = generate_insight_for_client_task.delay(client_id, days_back)
        
        return {
            "message": f"Recalculando insights para cliente {client_id}",
            "task_id": task.id,
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error recalculando insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest/", response_model=List[InsightDetail])
async def get_latest_insights(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    Obtener los insights más recientes del sistema
    """
    try:
        query = text("""
            SELECT 
                id, client_id, summary_text, key_findings,
                risk_level, opportunity_level, metrics,
                generated_at, created_at
            FROM ai_insights
            ORDER BY generated_at DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, {"limit": limit})
        
        insights = []
        for row in result:
            insights.append(InsightDetail(
                id=row[0],
                client_id=row[1],
                summary_text=row[2],
                key_findings=row[3] if row[3] else [],
                risk_level=row[4],
                opportunity_level=row[5],
                metrics=row[6] if row[6] else {},
                generated_at=row[7],
                created_at=row[8]
            ))
        
        return insights
        
    except Exception as e:
        logger.error(f"Error obteniendo insights recientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
