"""
Insight Generator - Generación automática de insights combinando múltiples fuentes
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class InsightGenerator:
    """Generador de insights automáticos desde múltiples fuentes de datos"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def generate_insights_for_client(self, client_id: int, days_back: int = 7) -> Dict:
        """
        Generar insights completos para un cliente
        
        Args:
            client_id: ID del cliente
            days_back: Días hacia atrás para análisis
            
        Returns:
            Dict con insights generados
        """
        logger.info(f"Generando insights para cliente {client_id}")
        
        try:
            # 1. Obtener datos de todas las fuentes
            text_data = self._get_text_analysis(client_id, days_back)
            kpi_data = self._get_kpi_summary(client_id, days_back)
            trend_data = self._get_trends(client_id, days_back)
            
            # 2. Validar que haya datos
            if not any([text_data, kpi_data, trend_data]):
                logger.warning(f"No hay datos suficientes para cliente {client_id}")
                return {
                    "client_id": client_id,
                    "summary_text": "Datos insuficientes para generar insights",
                    "key_findings": [],
                    "risk_level": "unknown",
                    "opportunity_level": "unknown",
                    "generated_at": datetime.utcnow()
                }
            
            # 3. Analizar patrones
            key_findings = []
            risk_indicators = []
            opportunity_indicators = []
            
            # Análisis de sentimiento
            if text_data:
                sentiment_insight = self._analyze_sentiment_pattern(text_data)
                if sentiment_insight:
                    key_findings.append(sentiment_insight['finding'])
                    if sentiment_insight.get('is_risk'):
                        risk_indicators.append(sentiment_insight['severity'])
                    if sentiment_insight.get('is_opportunity'):
                        opportunity_indicators.append(sentiment_insight['strength'])
            
            # Análisis de KPIs
            if kpi_data:
                kpi_insight = self._analyze_kpi_trend(kpi_data)
                if kpi_insight:
                    key_findings.append(kpi_insight['finding'])
                    if kpi_insight.get('is_risk'):
                        risk_indicators.append(kpi_insight['severity'])
                    if kpi_insight.get('is_opportunity'):
                        opportunity_indicators.append(kpi_insight['strength'])
            
            # Análisis de tendencias
            if trend_data:
                trend_insight = self._analyze_emerging_trends(trend_data)
                if trend_insight:
                    key_findings.append(trend_insight['finding'])
                    if trend_insight.get('is_opportunity'):
                        opportunity_indicators.append(trend_insight['strength'])
            
            # 4. Calcular niveles de riesgo y oportunidad
            risk_level = self._calculate_risk_level(risk_indicators)
            opportunity_level = self._calculate_opportunity_level(opportunity_indicators)
            
            # 5. Generar resumen ejecutivo
            summary_text = self._generate_executive_summary(
                client_id,
                text_data,
                kpi_data,
                trend_data,
                risk_level,
                opportunity_level
            )
            
            # 6. Construir resultado
            insight = {
                "client_id": client_id,
                "summary_text": summary_text,
                "key_findings": key_findings,
                "risk_level": risk_level,
                "opportunity_level": opportunity_level,
                "metrics": {
                    "text_records": len(text_data) if text_data else 0,
                    "kpis_analyzed": len(kpi_data) if kpi_data else 0,
                    "trends_detected": len(trend_data) if trend_data else 0,
                    "analysis_period_days": days_back
                },
                "generated_at": datetime.utcnow()
            }
            
            logger.info(f"Insights generados para cliente {client_id}: {len(key_findings)} hallazgos")
            
            return insight
            
        except Exception as e:
            logger.error(f"Error generando insights para cliente {client_id}: {e}")
            raise
    
    def _get_text_analysis(self, client_id: int, days_back: int) -> List[Dict]:
        """Obtener análisis de texto del cliente"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            query = text("""
                SELECT 
                    id,
                    text_field,
                    sentiment,
                    sentiment_score,
                    keywords,
                    created_at
                FROM text_summary
                WHERE client_id = :client_id
                AND created_at >= :cutoff_date
                ORDER BY created_at DESC
            """)
            
            result = self.db.execute(query, {
                "client_id": client_id,
                "cutoff_date": cutoff_date
            })
            
            data = []
            for row in result:
                data.append({
                    "id": row[0],
                    "text": row[1],
                    "sentiment": row[2],
                    "sentiment_score": float(row[3]) if row[3] else 0.0,
                    "keywords": row[4] if row[4] else [],
                    "created_at": row[5]
                })
            
            return data
            
        except Exception as e:
            logger.error(f"Error obteniendo text_analysis: {e}")
            return []
    
    def _get_kpi_summary(self, client_id: int, days_back: int) -> List[Dict]:
        """Obtener KPIs del cliente"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            query = text("""
                SELECT 
                    kpi_name,
                    kpi_value,
                    period_start,
                    period_end,
                    calculated_at
                FROM kpi_summary
                WHERE client_id = :client_id
                AND calculated_at >= :cutoff_date
                ORDER BY calculated_at DESC
            """)
            
            result = self.db.execute(query, {
                "client_id": client_id,
                "cutoff_date": cutoff_date
            })
            
            data = []
            for row in result:
                data.append({
                    "kpi_name": row[0],
                    "kpi_value": float(row[1]),
                    "period_start": row[2],
                    "period_end": row[3],
                    "calculated_at": row[4]
                })
            
            return data
            
        except Exception as e:
            logger.error(f"Error obteniendo kpi_summary: {e}")
            return []
    
    def _get_trends(self, client_id: int, days_back: int) -> List[Dict]:
        """Obtener tendencias del cliente o generales"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Como trend_signals no tiene client_id directo, obtener todos los recientes
            query = text("""
                SELECT 
                    sector,
                    term,
                    frequency,
                    delta_pct,
                    status,
                    period_start,
                    created_at
                FROM trend_signals
                WHERE created_at >= :cutoff_date
                ORDER BY frequency DESC
                LIMIT 20
            """)
            
            result = self.db.execute(query, {"cutoff_date": cutoff_date})
            
            data = []
            for row in result:
                data.append({
                    "sector": row[0],
                    "term": row[1],
                    "frequency": row[2],
                    "delta_pct": float(row[3]) if row[3] else 0.0,
                    "status": row[4],
                    "period_start": row[5],
                    "created_at": row[6]
                })
            
            return data
            
        except Exception as e:
            logger.error(f"Error obteniendo trends: {e}")
            return []
    
    def _analyze_sentiment_pattern(self, text_data: List[Dict]) -> Optional[Dict]:
        """Analizar patrones de sentimiento"""
        if not text_data:
            return None
        
        # Contar sentimientos
        sentiments = [d['sentiment'] for d in text_data if d.get('sentiment')]
        
        if not sentiments:
            return None
        
        from collections import Counter
        sentiment_counts = Counter(sentiments)
        total = len(sentiments)
        
        positive_pct = (sentiment_counts.get('positive', 0) / total) * 100
        negative_pct = (sentiment_counts.get('negative', 0) / total) * 100
        
        # Generar insight
        if negative_pct > 50:
            return {
                "finding": f"⚠️ Alto nivel de sentimiento negativo ({negative_pct:.0f}% de menciones)",
                "is_risk": True,
                "severity": 3 if negative_pct > 70 else 2
            }
        elif positive_pct > 60:
            return {
                "finding": f"✅ Sentimiento mayormente positivo ({positive_pct:.0f}% de menciones)",
                "is_opportunity": True,
                "strength": 3 if positive_pct > 80 else 2
            }
        else:
            return {
                "finding": f"Sentimiento mixto: {positive_pct:.0f}% positivo, {negative_pct:.0f}% negativo"
            }
    
    def _analyze_kpi_trend(self, kpi_data: List[Dict]) -> Optional[Dict]:
        """Analizar tendencias en KPIs"""
        if not kpi_data:
            return None
        
        # Agrupar por KPI name
        from collections import defaultdict
        kpi_groups = defaultdict(list)
        
        for kpi in kpi_data:
            kpi_groups[kpi['kpi_name']].append(kpi['kpi_value'])
        
        # Analizar el KPI más relevante (con más datos)
        if not kpi_groups:
            return None
        
        main_kpi = max(kpi_groups.items(), key=lambda x: len(x[1]))
        kpi_name, values = main_kpi
        
        if len(values) >= 2:
            # Comparar último valor con promedio
            current = values[0]
            avg = sum(values) / len(values)
            change_pct = ((current - avg) / avg * 100) if avg != 0 else 0
            
            if change_pct > 20:
                return {
                    "finding": f"📈 {kpi_name} aumentó {change_pct:.1f}% respecto al promedio",
                    "is_opportunity": True,
                    "strength": 3 if change_pct > 50 else 2
                }
            elif change_pct < -20:
                return {
                    "finding": f"📉 {kpi_name} disminuyó {abs(change_pct):.1f}% respecto al promedio",
                    "is_risk": True,
                    "severity": 3 if change_pct < -50 else 2
                }
        
        return {
            "finding": f"KPI principal: {kpi_name} = {values[0]:.2f}"
        }
    
    def _analyze_emerging_trends(self, trend_data: List[Dict]) -> Optional[Dict]:
        """Analizar tendencias emergentes"""
        if not trend_data:
            return None
        
        # Filtrar tendencias emergentes
        emergent = [t for t in trend_data if t.get('status') == 'emergent']
        
        if emergent:
            top_trend = emergent[0]
            return {
                "finding": f"🔥 Tendencia emergente detectada: '{top_trend['term']}' ({top_trend['frequency']} menciones)",
                "is_opportunity": True,
                "strength": 3 if top_trend['frequency'] > 5 else 2
            }
        
        # Si no hay emergentes, mencionar la más frecuente
        if trend_data:
            top_trend = trend_data[0]
            return {
                "finding": f"Término más frecuente: '{top_trend['term']}' ({top_trend['frequency']} menciones)"
            }
        
        return None
    
    def _calculate_risk_level(self, indicators: List[int]) -> str:
        """Calcular nivel de riesgo basado en indicadores"""
        if not indicators:
            return "low"
        
        avg_severity = sum(indicators) / len(indicators)
        
        if avg_severity >= 3:
            return "critical"
        elif avg_severity >= 2.5:
            return "high"
        elif avg_severity >= 1.5:
            return "medium"
        else:
            return "low"
    
    def _calculate_opportunity_level(self, indicators: List[int]) -> str:
        """Calcular nivel de oportunidad basado en indicadores"""
        if not indicators:
            return "low"
        
        avg_strength = sum(indicators) / len(indicators)
        
        if avg_strength >= 3:
            return "high"
        elif avg_strength >= 2:
            return "medium"
        else:
            return "low"
    
    def _generate_executive_summary(
        self,
        client_id: int,
        text_data: List,
        kpi_data: List,
        trend_data: List,
        risk_level: str,
        opportunity_level: str
    ) -> str:
        """Generar resumen ejecutivo"""
        summary_parts = []
        
        summary_parts.append(f"Análisis automático generado para cliente #{client_id}.")
        
        # Resumen de datos
        data_summary = []
        if text_data:
            data_summary.append(f"{len(text_data)} análisis de texto")
        if kpi_data:
            data_summary.append(f"{len(kpi_data)} KPIs")
        if trend_data:
            data_summary.append(f"{len(trend_data)} tendencias")
        
        if data_summary:
            summary_parts.append(f"Procesados: {', '.join(data_summary)}.")
        
        # Niveles
        summary_parts.append(f"Nivel de riesgo: {risk_level.upper()}.")
        summary_parts.append(f"Nivel de oportunidad: {opportunity_level.upper()}.")
        
        return " ".join(summary_parts)
    
    def persist_insight(self, insight_data: Dict) -> bool:
        """
        Guardar insight en la base de datos
        
        Args:
            insight_data: Dict con datos del insight
            
        Returns:
            True si se guardó exitosamente
        """
        try:
            # Verificar si ya existe para hoy
            check_query = text("""
                SELECT id FROM ai_insights
                WHERE client_id = :client_id
                AND DATE(generated_at) = DATE(:generated_at)
            """)
            
            existing = self.db.execute(check_query, {
                "client_id": insight_data['client_id'],
                "generated_at": insight_data['generated_at']
            }).fetchone()
            
            if existing:
                # Actualizar
                update_query = text("""
                    UPDATE ai_insights
                    SET summary_text = :summary_text,
                        key_findings = CAST(:key_findings AS jsonb),
                        risk_level = :risk_level,
                        opportunity_level = :opportunity_level,
                        metrics = CAST(:metrics AS jsonb)
                    WHERE id = :id
                """)
                
                self.db.execute(update_query, {
                    "summary_text": insight_data['summary_text'],
                    "key_findings": json.dumps(insight_data['key_findings']),
                    "risk_level": insight_data['risk_level'],
                    "opportunity_level": insight_data['opportunity_level'],
                    "metrics": json.dumps(insight_data.get('metrics', {})),
                    "id": existing[0]
                })
                
                logger.debug(f"Insight actualizado para cliente {insight_data['client_id']}")
            else:
                # Insertar - USAR TODOS LOS PARÁMETROS CON :
                insert_query = text("""
                    INSERT INTO ai_insights (
                        client_id, summary_text, key_findings,
                        risk_level, opportunity_level, metrics, generated_at
                    )
                    VALUES (
                        :client_id, :summary_text, CAST(:key_findings AS jsonb),
                        :risk_level, :opportunity_level, CAST(:metrics AS jsonb), :generated_at
                    )
                """)
                
                self.db.execute(insert_query, {
                    "client_id": insight_data['client_id'],
                    "summary_text": insight_data['summary_text'],
                    "key_findings": json.dumps(insight_data['key_findings']),
                    "risk_level": insight_data['risk_level'],
                    "opportunity_level": insight_data['opportunity_level'],
                    "metrics": json.dumps(insight_data.get('metrics', {})),
                    "generated_at": insight_data['generated_at']
                })
                
                logger.debug(f"Insight insertado para cliente {insight_data['client_id']}")
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error persistiendo insight: {e}")
            self.db.rollback()
            return False


def get_active_clients(db: Session, hours_back: int = 168) -> List[int]:
    """
    Obtener clientes con actividad reciente
    
    Args:
        db: Sesión de base de datos
        hours_back: Horas hacia atrás para buscar actividad
        
    Returns:
        Lista de client_ids
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
    
    query = text("""
        SELECT DISTINCT client_id
        FROM text_summary
        WHERE created_at >= :cutoff_time
        
        UNION
        
        SELECT DISTINCT client_id
        FROM kpi_summary
        WHERE calculated_at >= :cutoff_time
        
        ORDER BY client_id
    """)
    
    result = db.execute(query, {"cutoff_time": cutoff_time})
    client_ids = [row[0] for row in result.fetchall()]
    
    logger.info(f"Encontrados {len(client_ids)} clientes activos")
    
    return client_ids
