import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from typing import List, Dict, Any
from collections import Counter

from app.workers.celery_app import celery_app
from app.database import SessionLocal, engine
from app.models.dataset import Dataset
from app.models.analytics import AnalyticsSummary, Trend
from app.services.text_analysis import analyze_text_batch, generate_embedding, extract_keywords
from app.services.ollama_service import ollama_service
from app.services.anomaly_detection import anomaly_detector
from app.logger import get_logger

logger = get_logger()


@celery_app.task(name="analysis.analyze_text_columns")
def analyze_text_columns_task(
    dataset_id: int,
    text_columns: List[str],
    use_ollama: bool = True,
    extract_entities: bool = False,
):
    """
    Analizar columnas de texto de un dataset usando Ollama para sentimiento
    
    Args:
        dataset_id: ID del dataset
        text_columns: Columnas de texto a analizar
        use_ollama: Si debe usar Ollama para análisis (True por defecto)
        extract_entities: Si debe extraer entidades nombradas
    """
    db = SessionLocal()
    logger.info(f"Analizando columnas de texto del dataset {dataset_id} (Ollama: {use_ollama})")
    
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
            
            # Limitar número de textos para análisis
            max_texts = 1000
            if len(texts) > max_texts:
                logger.info(f"Limitando análisis a {max_texts} textos de {len(texts)} totales")
                texts = texts[:max_texts]
            
            # Analizar batch de textos con Ollama
            analysis_results = analyze_text_batch(
                texts,
                use_ollama=use_ollama,
                extract_entities=extract_entities,
            )
            
            # Calcular métricas agregadas
            avg_sentiment = {
                "positive": sum(r["sentiment"]["positive"] for r in analysis_results) / len(analysis_results),
                "negative": sum(r["sentiment"]["negative"] for r in analysis_results) / len(analysis_results),
                "neutral": sum(r["sentiment"]["neutral"] for r in analysis_results) / len(analysis_results),
            }
            
            # Calcular confianza promedio
            avg_confidence = sum(r["sentiment_confidence"] for r in analysis_results) / len(analysis_results)
            
            # Contar métodos usados
            methods_used = Counter([r["sentiment_method"] for r in analysis_results])
            
            # Extraer keywords más comunes
            all_keywords = []
            for r in analysis_results:
                all_keywords.extend(r["keywords"])
            
            top_keywords = [k for k, v in Counter(all_keywords).most_common(20)]
            
            # Extraer entidades más comunes si están disponibles
            top_entities = []
            if extract_entities:
                all_entities = []
                for r in analysis_results:
                    if 'entities' in r:
                        all_entities.extend([e['text'] for e in r['entities']])
                
                if all_entities:
                    top_entities = [e for e, c in Counter(all_entities).most_common(10)]
            
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
                    "avg_confidence": round(avg_confidence, 3),
                    "methods_used": dict(methods_used),
                    "top_keywords": top_keywords,
                    "top_entities": top_entities,
                    "texts_analyzed": len(texts),
                    "ollama_enabled": use_ollama,
                }
            )
            
            db.add(summary)
            results.append({
                "column": col,
                "avg_sentiment": avg_sentiment,
                "avg_confidence": avg_confidence,
                "methods_used": dict(methods_used),
                "top_keywords": top_keywords,
                "top_entities": top_entities,
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
def calculate_kpis_task(
    dataset_id: int, 
    numeric_columns: List[str],
    detect_anomalies: bool = True,
    anomaly_method: str = 'isolation_forest',
    contamination: float = 0.1,
):
    """
    Calcular KPIs de columnas numéricas con detección de anomalías usando IsolationForest
    
    Args:
        dataset_id: ID del dataset a analizar
        numeric_columns: Lista de columnas numéricas
        detect_anomalies: Si se debe detectar anomalías
        anomaly_method: Método de detección ('isolation_forest', 'ensemble', 'multivariate', 'lof')
        contamination: Proporción esperada de anomalías (0.0 a 0.5)
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
        anomaly_reports = {}
        
        # Filtrar columnas válidas
        valid_columns = [col for col in numeric_columns if col in df.columns]
        
        if not valid_columns:
            raise ValueError("Ninguna de las columnas especificadas existe en el dataset")
        
        # Calcular estadísticas para cada columna
        for col in valid_columns:
            # Convertir a numérico
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Eliminar nulos para cálculos
            col_data = df[col].dropna()
            
            if len(col_data) == 0:
                logger.warning(f"Columna {col} no tiene datos numéricos válidos")
                continue
            
            # Calcular estadísticas descriptivas
            stats = {
                "mean": float(col_data.mean()),
                "median": float(col_data.median()),
                "std": float(col_data.std()),
                "min": float(col_data.min()),
                "max": float(col_data.max()),
                "q25": float(col_data.quantile(0.25)),
                "q50": float(col_data.quantile(0.50)),
                "q75": float(col_data.quantile(0.75)),
                "q90": float(col_data.quantile(0.90)),
                "q95": float(col_data.quantile(0.95)),
                "q99": float(col_data.quantile(0.99)),
                "iqr": float(col_data.quantile(0.75) - col_data.quantile(0.25)),
                "cv": float(col_data.std() / col_data.mean()) if col_data.mean() != 0 else 0,
                "skewness": float(col_data.skew()),
                "kurtosis": float(col_data.kurtosis()),
            }
            
            results.append({
                "column": col,
                "statistics": stats,
                "data_points": len(col_data),
            })
        
        # Detección de anomalías si está habilitada
        if detect_anomalies and len(valid_columns) > 0:
            logger.info(f"Detectando anomalías usando método: {anomaly_method}")
            
            try:
                if anomaly_method == 'isolation_forest':
                    # Método principal: IsolationForest
                    anomaly_report = anomaly_detector.detect_anomalies_isolation_forest(
                        df=df,
                        columns=valid_columns,
                        contamination=contamination,
                        n_estimators=100,
                        random_state=42,
                    )
                    
                elif anomaly_method == 'ensemble':
                    # Ensemble de múltiples métodos
                    anomaly_report = anomaly_detector.detect_anomalies_ensemble(
                        df=df,
                        columns=valid_columns,
                        contamination=contamination,
                    )
                    
                elif anomaly_method == 'multivariate':
                    # Elliptic Envelope (multivariado Gaussiano)
                    anomaly_report = anomaly_detector.detect_anomalies_multivariate(
                        df=df,
                        columns=valid_columns,
                        contamination=contamination,
                    )
                    
                elif anomaly_method == 'lof':
                    # Local Outlier Factor
                    anomaly_report = anomaly_detector.detect_anomalies_local_outlier_factor(
                        df=df,
                        columns=valid_columns,
                        contamination=contamination,
                    )
                    
                else:
                    logger.warning(f"Método desconocido: {anomaly_method}, usando isolation_forest")
                    anomaly_report = anomaly_detector.detect_anomalies_isolation_forest(
                        df=df,
                        columns=valid_columns,
                        contamination=contamination,
                    )
                
                anomaly_reports['main_report'] = anomaly_report
                
                # Guardar métricas de anomalías
                anomaly_summary = AnalyticsSummary(
                    client_id=dataset.client_id,
                    dataset_id=dataset_id,
                    date=datetime.utcnow().date(),
                    metric_name="anomaly_detection",
                    metric_value=anomaly_report['anomaly_percentage'],
                    metadata={
                        'method': anomaly_report['method'],
                        'total_anomalies': anomaly_report['total_anomalies'],
                        'contamination': contamination,
                        'columns_analyzed': valid_columns,
                        'severity_distribution': anomaly_report.get('severity_distribution', {}),
                    }
                )
                
                db.add(anomaly_summary)
                
                logger.info(
                    f"Anomalías detectadas: {anomaly_report['total_anomalies']} "
                    f"({anomaly_report['anomaly_percentage']}%)"
                )
                
            except Exception as e:
                logger.error(f"Error detectando anomalías: {e}")
                anomaly_reports['error'] = str(e)
        
        # Guardar KPIs en base de datos
        for result in results:
            col = result['column']
            stats = result['statistics']
            
            summary = AnalyticsSummary(
                client_id=dataset.client_id,
                dataset_id=dataset_id,
                date=datetime.utcnow().date(),
                metric_name=f"kpi_{col}",
                metric_value=stats["mean"],
                metadata={
                    "column": col,
                    "statistics": stats,
                    "data_points": result['data_points'],
                }
            )
            
            db.add(summary)
        
        db.commit()
        
        logger.info(f"KPIs calculados para dataset {dataset_id}")
        
        return {
            "status": "success",
            "kpi_results": results,
            "anomaly_detection": anomaly_reports if detect_anomalies else None,
        }
        
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
