"""
Celery tasks para generación de insights automáticos
"""
import logging
from datetime import datetime
from typing import Dict
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.data_insights.insight_generator import InsightGenerator, get_active_clients

logger = logging.getLogger(__name__)


@celery_app.task(name="generate_recent_insights")
def generate_recent_insights(days_back: int = 7, hours_activity: int = 168) -> Dict:
    """
    Generar insights para clientes con actividad reciente
    
    Args:
        days_back: Días hacia atrás para análisis
        hours_activity: Horas para detectar actividad reciente
        
    Returns:
        Dict con resumen del procesamiento
    """
    db = SessionLocal()
    logger.info(f"Iniciando generación de insights ({days_back} días)")
    
    try:
        # 1. Obtener clientes activos
        client_ids = get_active_clients(db, hours_activity)
        
        if not client_ids:
            logger.info("No hay clientes con actividad reciente")
            return {
                "processed_clients": 0,
                "insights_generated": 0,
                "status": "no_clients",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # 2. Generar insights para cada cliente
        generator = InsightGenerator(db)
        results = []
        insights_generated = 0
        
        for client_id in client_ids:
            try:
                logger.info(f"Generando insights para cliente {client_id}")
                
                # Generar insight
                insight = generator.generate_insights_for_client(
                    client_id=client_id,
                    days_back=days_back
                )
                
                # Persistir
                success = generator.persist_insight(insight)
                
                if success:
                    insights_generated += 1
                    results.append({
                        "client_id": client_id,
                        "status": "success",
                        "findings_count": len(insight['key_findings']),
                        "risk_level": insight['risk_level'],
                        "opportunity_level": insight['opportunity_level']
                    })
                else:
                    results.append({
                        "client_id": client_id,
                        "status": "failed_to_persist"
                    })
                
            except Exception as e:
                logger.error(f"Error generando insights para cliente {client_id}: {e}")
                results.append({
                    "client_id": client_id,
                    "status": "error",
                    "error": str(e)
                })
        
        # 3. Resumen final
        summary = {
            "processed_clients": len(client_ids),
            "insights_generated": insights_generated,
            "results": results,
            "days_back": days_back,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(
            f"✓ Insights generados: {insights_generated}/{len(client_ids)} clientes"
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Error crítico en generate_recent_insights: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="generate_insight_for_client_task")
def generate_insight_for_client_task(client_id: int, days_back: int = 7) -> Dict:
    """
    Generar insight para un cliente específico
    
    Args:
        client_id: ID del cliente
        days_back: Días hacia atrás para análisis
        
    Returns:
        Dict con resultado
    """
    db = SessionLocal()
    
    try:
        generator = InsightGenerator(db)
        
        # Generar insight
        insight = generator.generate_insights_for_client(
            client_id=client_id,
            days_back=days_back
        )
        
        # Persistir
        success = generator.persist_insight(insight)
        
        if success:
            result = {
                "client_id": client_id,
                "status": "success",
                "findings_count": len(insight['key_findings']),
                "risk_level": insight['risk_level'],
                "opportunity_level": insight['opportunity_level'],
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            result = {
                "client_id": client_id,
                "status": "failed_to_persist",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        logger.info(f"Insight generado para cliente {client_id}: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error en generate_insight_for_client_task: {e}")
        db.rollback()
        raise
    finally:
        db.close()
