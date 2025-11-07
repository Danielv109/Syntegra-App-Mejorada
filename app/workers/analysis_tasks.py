import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from typing import List, Dict, Any

from app.workers.celery_app import celery_app
from app.database import SessionLocal, engine
from app.models.dataset import Dataset
from app.models.analytics import AnalyticsSummary, Trend
from app.services.text_analysis import analyze_text_batch, generate_embedding, extract_keywords
from app.services.ollama_service import ollama_service
from app.logger import get_logger

logger = get_logger()


@celery_app.task(name="analysis.analyze_text_columns")
def analyze_text_columns_task(dataset_id: int, text_columns: List[str]):
    """
    Analizar columnas de texto de un dataset
    """
    db = SessionLocal()
    logger.info(f"Analizando columnas de texto del dataset {dataset_id}")
    
    try:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} no encontrado")
        
        # Leer datos del schema del cliente
        schema_name = dataset.client.schema_name
        table_name = f"dataset_{dataset_id}"
        
        query = f"SELECT * FROM {schema_name}.{table_name}"
        df = pd.read_sql(query, engine)
        
        results = []
        
        for col in text_columns:
            if col not in df.columns:
                logger.warning(f"Columna {col} no encontrada en dataset")
                continue
            
            logger.info(f"Analizando columna: {col}")
            
            # Obtener textos no nulos
            texts = df[col].dropna().astype(str).tolist()
            
            if not texts:
                continue
            
            # Analizar batch de textos
            analysis_results = analyze_text_batch(texts[:1000])  # Limitar a 1000
            
            # Calcular métricas agregadas
            avg_sentiment = {
                "positive": sum(r["sentiment"]["positive"] for r in analysis_results) / len(analysis_results),
                "negative": sum(r["sentiment"]["negative"] for r in analysis_results) / len(analysis_results),
                "neutral": sum(r["sentiment"]["neutral"] for r in analysis_results) / len(analysis_results),
            }
            
            # Extraer keywords más comunes
            all_keywords = []
            for r in analysis_results:
                all_keywords.extend(r["keywords"])
            
            from collections import Counter
            top_keywords = [k for k, v in Counter(all_keywords).most_common(20)]
            
            # Guardar métricas
            summary = AnalyticsSummary(
                client_id=dataset.client_id,
                dataset_id=dataset_id,
                date=datetime.utcnow().date(),
                metric_name=f"text_analysis_{col}",
                metric_value=avg_sentiment["positive"],
                metadata={
                    "column": col,
                    "avg_sentiment": avg_sentiment,
                    "top_keywords": top_keywords,
                    "texts_analyzed": len(texts),
                }
            )
            
            db.add(summary)
            results.append({
                "column": col,
                "avg_sentiment": avg_sentiment,
                "top_keywords": top_keywords,
            })
        
        db.commit()
        
        logger.info(f"Análisis de texto completado para dataset {dataset_id}")
        return {"status": "success", "results": results}
        
    except Exception as e:
        logger.error(f"Error analizando texto: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="analysis.calculate_kpis")
def calculate_kpis_task(dataset_id: int, numeric_columns: List[str]):
    """
    Calcular KPIs de columnas numéricas
    """
    db = SessionLocal()
    logger.info(f"Calculando KPIs del dataset {dataset_id}")
    
    try:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} no encontrado")
        
        schema_name = dataset.client.schema_name
        table_name = f"dataset_{dataset_id}"
        
        query = f"SELECT * FROM {schema_name}.{table_name}"
        df = pd.read_sql(query, engine)
        
        results = []
        
        for col in numeric_columns:
            if col not in df.columns:
                continue
            
            # Convertir a numérico
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Calcular estadísticas
            stats = {
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "q25": float(df[col].quantile(0.25)),
                "q75": float(df[col].quantile(0.75)),
            }
            
            # Detectar anomalías (valores fuera de 3 desviaciones estándar)
            mean = stats["mean"]
            std = stats["std"]
            anomalies = df[(df[col] < mean - 3*std) | (df[col] > mean + 3*std)][col].tolist()
            
            # Guardar métricas
            summary = AnalyticsSummary(
                client_id=dataset.client_id,
                dataset_id=dataset_id,
                date=datetime.utcnow().date(),
                metric_name=f"kpi_{col}",
                metric_value=stats["mean"],
                metadata={
                    "column": col,
                    "statistics": stats,
                    "anomalies_count": len(anomalies),
                }
            )
            
            db.add(summary)
            results.append({
                "column": col,
                "statistics": stats,
                "anomalies_count": len(anomalies),
            })
        
        db.commit()
        
        logger.info(f"KPIs calculados para dataset {dataset_id}")
        return {"status": "success", "results": results}
        
    except Exception as e:
        logger.error(f"Error calculando KPIs: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="analysis.detect_trends")
def detect_trends_task(client_id: int, days_back: int = 30):
    """
    Detectar tendencias emergentes en los datos del cliente
    """
    db = SessionLocal()
    logger.info(f"Detectando tendencias para cliente {client_id}")
    
    try:
        # Obtener datos de análisis recientes
        start_date = datetime.utcnow().date() - timedelta(days=days_back)
        
        summaries = db.query(AnalyticsSummary).filter(
            AnalyticsSummary.client_id == client_id,
            AnalyticsSummary.date >= start_date,
            AnalyticsSummary.metric_name.like("text_analysis_%")
        ).all()
        
        if not summaries:
            logger.warning(f"No hay datos suficientes para detectar tendencias")
            return {"status": "no_data"}
        
        # Extraer keywords de todas las métricas
        all_keywords = {}
        
        for summary in summaries:
            if summary.metadata and "top_keywords" in summary.metadata:
                for keyword in summary.metadata["top_keywords"]:
                    if keyword not in all_keywords:
                        all_keywords[keyword] = {
                            "count": 0,
                            "dates": []
                        }
                    all_keywords[keyword]["count"] += 1
                    all_keywords[keyword]["dates"].append(summary.date)
        
        # Calcular tendencias
        trends_data = []
        
        for keyword, data in all_keywords.items():
            if data["count"] < 3:  # Mínimo 3 apariciones
                continue
            
            # Calcular crecimiento
            dates = sorted(data["dates"])
            if len(dates) >= 2:
                days_diff = (dates[-1] - dates[0]).days
                if days_diff > 0:
                    growth_rate = (data["count"] / days_diff) * 100
                else:
                    growth_rate = 0
            else:
                growth_rate = 0
            
            # Clasificar tendencia
            if growth_rate > 5:
                trend_status = "emergente"
            elif growth_rate < -5:
                trend_status = "en descenso"
            else:
                trend_status = "estable"
            
            # Generar embedding
            try:
                embedding = generate_embedding(keyword)
            except:
                embedding = None
            
            # Guardar tendencia
            trend = Trend(
                client_id=client_id,
                keyword=keyword,
                frequency=data["count"],
                growth_rate=growth_rate,
                trend_status=trend_status,
                time_period_start=dates[0],
                time_period_end=dates[-1],
                embedding=embedding,
                metadata={
                    "dates": [str(d) for d in dates],
                }
            )
            
            db.add(trend)
            trends_data.append({
                "keyword": keyword,
                "frequency": data["count"],
                "growth_rate": growth_rate,
                "status": trend_status,
            })
        
        db.commit()
        
        logger.info(f"Detectadas {len(trends_data)} tendencias para cliente {client_id}")
        return {"status": "success", "trends": trends_data}
        
    except Exception as e:
        logger.error(f"Error detectando tendencias: {e}")
        db.rollback()
        raise
    finally:
        db.close()
