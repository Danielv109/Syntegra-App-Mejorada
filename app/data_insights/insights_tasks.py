import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.data_insights.embeddings import get_embedding, bulk_embed
from app.data_insights.text_analysis import analyze_sentiment, extract_keywords
from app.data_insights.kpi_engine import KPIEngine, get_clients_with_recent_data

logger = logging.getLogger(__name__)


@celery_app.task(name="process_new_texts")
def process_new_texts(limit: int = 10) -> Dict[str, any]:
    """
    Procesar textos nuevos de processed_data
    
    Nota: processed_data tiene estructura: id, source_type, data (jsonb), created_at
    Los textos están dentro del campo 'data' como JSON
    """
    db = SessionLocal()
    processed_count = 0
    errors = []
    
    try:
        # 1. Obtener registros recientes de processed_data
        # Filtramos por los que no están ya en text_summary
        query = text("""
            SELECT pd.id, pd.source_type, pd.data, pd.created_at
            FROM processed_data pd
            WHERE NOT EXISTS (
                SELECT 1 FROM text_summary ts 
                WHERE ts.text_field = (pd.data->>'text')::text
            )
            ORDER BY pd.created_at DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, {"limit": limit})
        pending_records = result.fetchall()
        
        if not pending_records:
            logger.info("No hay registros pendientes de análisis textual")
            return {
                "processed": 0,
                "errors": 0,
                "message": "No pending records"
            }
        
        logger.info(f"Procesando {len(pending_records)} registros")
        
        # Obtener client_id por defecto (primer cliente)
        client_query = text("SELECT id FROM clients ORDER BY id LIMIT 1")
        client_result = db.execute(client_query).fetchone()
        default_client_id = client_result[0] if client_result else 1
        
        # Procesar cada registro
        for record in pending_records:
            try:
                record_id, source_type, data, created_at = record
                
                # Extraer texto del JSON
                text_field = data.get('text') or data.get('comment') or data.get('description')
                
                if not text_field or not text_field.strip():
                    logger.warning(f"Registro {record_id}: sin texto válido, saltando")
                    continue
                
                # 2. Generar embedding
                logger.debug(f"Registro {record_id}: generando embedding")
                embedding = get_embedding(text_field)
                
                # 3. Analizar sentiment
                logger.debug(f"Registro {record_id}: analizando sentiment")
                sentiment_result = analyze_sentiment(text_field)
                
                # 4. Extraer keywords
                logger.debug(f"Registro {record_id}: extrayendo keywords")
                keywords = extract_keywords(text_field)
                
                # 5. Insertar en text_summary - SIN CAST, dejar que psycopg2 lo maneje
                insert_query = text("""
                    INSERT INTO text_summary (
                        client_id, text_field, sentiment, sentiment_score,
                        keywords, embedding, created_at
                    )
                    VALUES (
                        :client_id, :text_field, :sentiment, :sentiment_score,
                        :keywords, :embedding, :created_at
                    )
                """)
                
                db.execute(insert_query, {
                    "client_id": default_client_id,
                    "text_field": text_field[:1000],
                    "sentiment": sentiment_result["label"],
                    "sentiment_score": sentiment_result["polarity"],
                    "keywords": json.dumps(keywords),  # Ya es string JSON
                    "embedding": str(embedding),  # Convertir lista a string
                    "created_at": datetime.utcnow()
                })
                
                # Commit individual
                db.commit()
                
                processed_count += 1
                logger.info(
                    f"Registro {record_id} procesado: "
                    f"sentiment={sentiment_result['label']}, "
                    f"keywords={len(keywords)}"
                )
                
            except Exception as e:
                error_msg = f"Error procesando registro {record_id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                db.rollback()  # Rollback individual
        
        # Generar reporte
        report = {
            "processed": processed_count,
            "errors": len(errors),
            "error_details": errors if errors else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if processed_count > 0:
            logger.info(
                f"✓ Embeddings y análisis de texto completados correctamente: "
                f"{processed_count} registros procesados"
            )
        
        return report
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error crítico en process_new_texts: {str(e)}")
        raise
    finally:
        db.close()


@celery_app.task(name="bulk_process_texts")
def bulk_process_texts(record_ids: List[int]) -> Dict[str, any]:
    """
    Procesar textos específicos en batch (más eficiente)
    
    Args:
        record_ids: Lista de IDs de processed_data
        
    Returns:
        Dict con estadísticas
    """
    db = SessionLocal()
    processed_count = 0
    
    try:
        # Obtener todos los registros
        query = text("""
            SELECT id, client_id, source_id, text_field
            FROM processed_data
            WHERE id = ANY(:ids)
        """)
        
        result = db.execute(query, {"ids": record_ids})
        records = result.fetchall()
        
        if not records:
            return {"processed": 0, "errors": 0}
        
        # Extraer textos para batch embedding
        texts = [r[3] for r in records if r[3]]
        
        # Batch embedding (más eficiente)
        logger.info(f"Generando embeddings en batch para {len(texts)} textos")
        embeddings = bulk_embed(texts)
        
        # Procesar individualmente sentiment y keywords
        for idx, record in enumerate(records):
            record_id, client_id, source_id, text_field = record
            
            if not text_field:
                continue
            
            sentiment = analyze_sentiment(text_field)
            keywords = extract_keywords(text_field)
            embedding = embeddings[idx]
            
            # Insertar
            insert_query = text("""
                INSERT INTO text_summary (
                    client_id, source_id, text_field,
                    sentiment, keywords, embedding, created_at
                )
                VALUES (
                    :client_id, :source_id, :text_field,
                    :sentiment, :keywords, :embedding, :created_at
                )
            """)
            
            db.execute(insert_query, {
                "client_id": client_id,
                "source_id": source_id,
                "text_field": text_field[:1000],
                "sentiment": sentiment["polarity"],
                "keywords": keywords,
                "embedding": embedding,
                "created_at": datetime.utcnow()
            })
            
            # Actualizar estado
            update_query = text("""
                UPDATE processed_data
                SET status = 'completed_text_analysis'
                WHERE id = :id
            """)
            
            db.execute(update_query, {"id": record_id})
            processed_count += 1
        
        db.commit()
        
        logger.info(f"Batch processing completado: {processed_count} registros")
        
        return {
            "processed": processed_count,
            "errors": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error en bulk_process_texts: {str(e)}")
        raise
    finally:
        db.close()


@celery_app.task(name="compute_kpis_for_recent")
def compute_kpis_for_recent(hours_back: int = 24, days_period: int = 30) -> Dict[str, any]:
    """
    Calcular KPIs para clientes con actividad reciente
    
    Args:
        hours_back: Horas hacia atrás para detectar actividad
        days_period: Días del período para calcular KPIs
        
    Returns:
        Dict con resumen del procesamiento
    """
    db = SessionLocal()
    logger.info(f"Iniciando cálculo de KPIs (últimas {hours_back}h)")
    
    try:
        # 1. Obtener clientes con datos recientes
        client_ids = get_clients_with_recent_data(db, hours_back)
        
        if not client_ids:
            logger.info("No hay clientes con datos recientes")
            return {
                "processed_clients": 0,
                "total_kpis": 0,
                "status": "no_clients",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # 2. Definir período de cálculo
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days_period)
        
        # 3. Procesar cada cliente
        kpi_engine = KPIEngine(db)
        results = []
        total_kpis = 0
        
        for client_id in client_ids:
            try:
                logger.info(f"Procesando cliente {client_id}")
                
                result = kpi_engine.compute_and_persist_kpis(
                    client_id=client_id,
                    period_start=period_start,
                    period_end=period_end
                )
                
                results.append(result)
                total_kpis += result.get("kpis_persisted", 0)
                
            except Exception as e:
                logger.error(f"Error procesando cliente {client_id}: {e}")
                results.append({
                    "client_id": client_id,
                    "status": "error",
                    "error": str(e)
                })
        
        # 4. Resumen final
        successful = sum(1 for r in results if r.get("status") == "success")
        
        summary = {
            "processed_clients": len(client_ids),
            "successful_clients": successful,
            "total_kpis": total_kpis,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(
            f"✓ KPIs calculados: {successful}/{len(client_ids)} clientes, "
            f"{total_kpis} KPIs totales"
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Error crítico en compute_kpis_for_recent: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="compute_kpis_for_client_task")
def compute_kpis_for_client_task(
    client_id: int,
    days_back: int = 30
) -> Dict[str, any]:
    """
    Calcular KPIs para un cliente específico
    
    Args:
        client_id: ID del cliente
        days_back: Días hacia atrás para el período
        
    Returns:
        Dict con resultado del cálculo
    """
    db = SessionLocal()
    
    try:
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days_back)
        
        kpi_engine = KPIEngine(db)
        result = kpi_engine.compute_and_persist_kpis(
            client_id=client_id,
            period_start=period_start,
            period_end=period_end
        )
        
        logger.info(f"KPIs calculados para cliente {client_id}: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error en compute_kpis_for_client_task: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# Script de prueba directo
if __name__ == "__main__":
    # Insertar datos de prueba en processed_data
    db = SessionLocal()
    
    try:
        # Verificar si ya hay client
        client_check = db.execute(text("SELECT id FROM clients LIMIT 1")).fetchone()
        if not client_check:
            # Crear client de prueba
            db.execute(text("""
                INSERT INTO clients (name, email) 
                VALUES ('Test Client', 'test@example.com')
            """))
            db.commit()
        
        # Insertar datos de prueba en processed_data
        test_texts = [
            "This product is excellent and I love it very much",
            "Terrible experience, very disappointed with the service",
            "The quality is good but the price is too high",
            "Amazing features and great customer support team",
            "Not recommended, poor quality and bad design",
        ]
        
        for text in test_texts:
            db.execute(text("""
                INSERT INTO processed_data (source_type, data)
                VALUES ('test', :data)
            """), {"data": {"text": text}})
        
        db.commit()
        print("✓ Datos de prueba insertados en processed_data")
        
        # Ejecutar procesamiento
        print("\n=== Ejecutando procesamiento ===")
        result = process_new_texts(10)
        print(f"\nResultado: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()
