"""
Celery tasks para detección de tendencias
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy import text
from sqlalchemy.orm import Session  # <-- AGREGAR ESTE IMPORT

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.data_insights.trend_engine import TrendEngine

logger = logging.getLogger(__name__)


@celery_app.task(name="detect_recent_trends")
def detect_recent_trends(
    window_short: int = 7,
    window_long: int = 30
) -> Dict[str, any]:
    """
    Detectar tendencias recientes en todos los sectores
    
    Args:
        window_short: Días para período reciente
        window_long: Días para período completo
        
    Returns:
        Dict con resumen del procesamiento
    """
    db = SessionLocal()
    logger.info(f"Iniciando detección de tendencias ({window_short}/{window_long} días)")
    
    try:
        # 1. Obtener sectores disponibles (o usar categoría general)
        sectors = get_available_sectors(db)
        
        if not sectors:
            # Si no hay sectores definidos, analizar todo como "general"
            sectors = ["general"]
            logger.info("No hay sectores específicos, analizando categoría general")
        
        # 2. Procesar cada sector
        trend_engine = TrendEngine(db)
        all_trends = []
        total_trends = 0
        
        for sector in sectors:
            try:
                logger.info(f"Analizando sector: {sector}")
                
                # Detectar tendencias
                df_trends = trend_engine.detect_trends_for_sector(
                    sector=sector,
                    window_short=window_short,
                    window_long=window_long
                )
                
                if not df_trends.empty:
                    # Guardar tendencias
                    persisted = trend_engine.persist_trends(df_trends)
                    total_trends += persisted
                    
                    all_trends.append({
                        "sector": sector,
                        "trends_detected": len(df_trends),
                        "trends_persisted": persisted
                    })
                else:
                    logger.info(f"No se detectaron tendencias para sector {sector}")
                    all_trends.append({
                        "sector": sector,
                        "trends_detected": 0,
                        "trends_persisted": 0
                    })
                
            except Exception as e:
                logger.error(f"Error procesando sector {sector}: {e}")
                all_trends.append({
                    "sector": sector,
                    "status": "error",
                    "error": str(e)
                })
        
        # 3. Resumen final
        summary = {
            "processed_sectors": len(sectors),
            "total_trends": total_trends,
            "sectors_detail": all_trends,
            "window_short": window_short,
            "window_long": window_long,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(
            f"✓ Tendencias detectadas: {total_trends} en {len(sectors)} sectores"
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Error crítico en detect_recent_trends: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="detect_trends_for_sector_task")
def detect_trends_for_sector_task(
    sector: str,
    window_short: int = 7,
    window_long: int = 30
) -> Dict[str, any]:
    """
    Detectar tendencias para un sector específico
    
    Args:
        sector: Sector a analizar
        window_short: Días para período reciente
        window_long: Días para período completo
        
    Returns:
        Dict con resultado del análisis
    """
    db = SessionLocal()
    
    try:
        trend_engine = TrendEngine(db)
        
        # Detectar tendencias
        df_trends = trend_engine.detect_trends_for_sector(
            sector=sector,
            window_short=window_short,
            window_long=window_long
        )
        
        if not df_trends.empty:
            # Guardar tendencias
            persisted = trend_engine.persist_trends(df_trends)
            
            result = {
                "sector": sector,
                "trends_detected": len(df_trends),
                "trends_persisted": persisted,
                "status": "success",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            result = {
                "sector": sector,
                "trends_detected": 0,
                "trends_persisted": 0,
                "status": "no_trends",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        logger.info(f"Tendencias detectadas para sector {sector}: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error en detect_trends_for_sector_task: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def get_available_sectors(db: Session) -> List[str]:
    """
    Obtener lista de sectores disponibles
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Lista de sectores
    """
    try:
        # Intentar obtener sectores de processed_data
        query = text("""
            SELECT DISTINCT data->>'sector' as sector
            FROM processed_data
            WHERE data->>'sector' IS NOT NULL
            LIMIT 20
        """)
        
        result = db.execute(query)
        sectors = [row[0] for row in result.fetchall() if row[0]]
        
        if sectors:
            logger.info(f"Encontrados {len(sectors)} sectores")
            return sectors
        
    except Exception as e:
        logger.warning(f"No se pudieron obtener sectores: {e}")
    
    return []


def detect_trends_for_sector(
    db: Session,
    sector: str,
    days_back: int = 30,
    min_frequency: int = 3
) -> List[Dict[str, any]]:
    """
    Detectar tendencias emergentes en un sector específico
    """
    try:
        logger.info(f"Detectando tendencias para sector: {sector}")
        
        # Obtener período con timezone-aware datetime
        from datetime import timezone
        period_end = datetime.now(timezone.utc)
        period_start = period_end - timedelta(days=days_back)
        
        logger.debug(f"Período: {period_start} a {period_end}")
        
        # Obtener keywords del sector
        query = text("""
            SELECT keywords, created_at
            FROM text_summary
            WHERE created_at >= :period_start
            AND created_at <= :period_end
            ORDER BY created_at
        """)
        
        result = db.execute(query, {
            "period_start": period_start,
            "period_end": period_end
        })
        data = [{"keywords": row[0], "created_at": row[1]} for row in result.fetchall()]
        
        if not data:
            logger.info(f"No se encontraron datos para el sector {sector} en el período dado")
            return []
        
        # Agrupar por día y contar frecuencias
        daily_trends = {}
        
        for entry in data:
            date_key = entry["created_at"].date()
            keywords = entry["keywords"]
            
            if date_key not in daily_trends:
                daily_trends[date_key] = {}
            
            for keyword in keywords:
                if keyword not in daily_trends[date_key]:
                    daily_trends[date_key][keyword] = 0
                daily_trends[date_key][keyword] += 1
        
        # Filtrar tendencias por frecuencia mínima
        filtered_trends = {
            date: {kw: count for kw, count in trends.items() if count >= min_frequency}
            for date, trends in daily_trends.items()
        }
        
        # Ordenar tendencias por fecha y frecuencia
        sorted_trends = sorted(
            ((date, kw, count) for date, trends in filtered_trends.items() for kw, count in trends.items()),
            key=lambda x: (x[0], -x[2])
        )
        
        # Limitar a las principales 10 tendencias por día
        from collections import defaultdict
        
        top_trends = defaultdict(list)
        
        for date, kw, count in sorted_trends:
            if len(top_trends[date]) < 10:
                top_trends[date].append({"keyword": kw, "count": count})
        
        # Convertir a lista final
        final_trends = []
        
        for date, trends in top_trends.items():
            final_trends.append({
                "date": date,
                "trends": trends
            })
        
        logger.info(f"Tendencias detectadas para el sector {sector}: {len(final_trends)} entradas")
        
        return final_trends
    
    except Exception as e:
        logger.error(f"Error detectando tendencias para el sector {sector}: {e}")
        raise
