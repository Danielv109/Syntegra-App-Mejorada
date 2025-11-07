"""
Trend Engine - Detección de tendencias emergentes y señales de mercado
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from collections import Counter
import json

logger = logging.getLogger(__name__)


class TrendEngine:
    """Motor de detección de tendencias desde análisis de texto"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def detect_trends_for_sector(
        self,
        sector: Optional[str] = None,
        window_short: int = 7,
        window_long: int = 30
    ) -> pd.DataFrame:
        """
        Detectar tendencias para un sector específico
        
        Args:
            sector: Sector a analizar (None = todos)
            window_short: Días para período reciente
            window_long: Días para período completo
            
        Returns:
            DataFrame con tendencias detectadas
        """
        logger.info(
            f"Detectando tendencias - Sector: {sector or 'Todos'}, "
            f"Ventanas: {window_short}/{window_long} días"
        )
        
        # 1. Definir períodos
        date_end = datetime.utcnow()
        date_long_start = date_end - timedelta(days=window_long)
        date_short_start = date_end - timedelta(days=window_short)
        
        # 2. Consultar datos de text_summary
        query = text("""
            SELECT 
                id,
                text_field,
                keywords,
                sentiment,
                created_at
            FROM text_summary
            WHERE created_at >= :start_date
            AND created_at <= :end_date
            ORDER BY created_at DESC
        """)
        
        result = self.db.execute(query, {
            "start_date": date_long_start,
            "end_date": date_end
        })
        
        rows = result.fetchall()
        
        if not rows:
            logger.warning(f"No hay datos para análisis de tendencias")
            return pd.DataFrame()
        
        # 3. Convertir a DataFrame
        data = []
        for row in rows:
            keywords = row[2] if row[2] else []
            if isinstance(keywords, str):
                keywords = json.loads(keywords)
            
            data.append({
                'id': row[0],
                'text_field': row[1],
                'keywords': keywords,
                'sentiment': row[3],
                'created_at': row[4]
            })
        
        df = pd.DataFrame(data)
        
        logger.info(f"DataFrame creado con {len(df)} registros")
        
        # 4. Extraer todas las keywords
        all_keywords = []
        for keywords in df['keywords']:
            if isinstance(keywords, list):
                all_keywords.extend(keywords)
            elif isinstance(keywords, str):
                try:
                    kw_list = json.loads(keywords)
                    all_keywords.extend(kw_list)
                except:
                    pass
        
        if not all_keywords:
            logger.warning("No se encontraron keywords para análisis")
            return pd.DataFrame()
        
        # 5. Analizar período largo (30 días)
        df_long = df[df['created_at'] >= date_long_start]
        keywords_long = []
        for keywords in df_long['keywords']:
            if isinstance(keywords, list):
                keywords_long.extend(keywords)
        
        freq_long = Counter(keywords_long)
        
        # 6. Analizar período corto (7 días)
        df_short = df[df['created_at'] >= date_short_start]
        keywords_short = []
        for keywords in df_short['keywords']:
            if isinstance(keywords, list):
                keywords_short.extend(keywords)
        
        freq_short = Counter(keywords_short)
        
        # 7. Calcular tendencias
        trends = []
        
        for term in set(list(freq_long.keys()) + list(freq_short.keys())):
            count_long = freq_long.get(term, 0)
            count_short = freq_short.get(term, 0)
            
            # Ignorar términos muy raros
            if count_long < 2:
                continue
            
            # Calcular frecuencia normalizada
            freq_long_norm = count_long / max(len(df_long), 1)
            freq_short_norm = count_short / max(len(df_short), 1)
            
            # Calcular delta porcentual
            if freq_long_norm > 0:
                delta_pct = ((freq_short_norm - freq_long_norm) / freq_long_norm) * 100
            else:
                delta_pct = 100.0 if freq_short_norm > 0 else 0.0
            
            # Clasificar tendencia
            if delta_pct >= 50:  # 50% o más de aumento
                trend_label = "rising"
            elif delta_pct <= -30:  # 30% o más de caída
                trend_label = "falling"
            else:
                trend_label = "stable"
            
            # Solo guardar tendencias significativas
            if trend_label in ["rising", "falling"]:
                trends.append({
                    'sector': sector or 'general',
                    'term': term,
                    'count_short': count_short,
                    'count_long': count_long,
                    'freq_short': round(freq_short_norm, 4),
                    'freq_long': round(freq_long_norm, 4),
                    'delta_pct': round(delta_pct, 2),
                    'trend_label': trend_label,
                    'period_start': date_long_start,
                    'period_end': date_end
                })
        
        df_trends = pd.DataFrame(trends)
        
        if not df_trends.empty:
            # Ordenar por delta más significativo
            df_trends = df_trends.sort_values('delta_pct', ascending=False)
            logger.info(f"Detectadas {len(df_trends)} tendencias significativas")
        else:
            logger.warning("No se detectaron tendencias significativas")
        
        return df_trends
    
    def persist_trends(self, df: pd.DataFrame) -> int:
        """
        Guardar tendencias en la base de datos
        
        Args:
            df: DataFrame con tendencias
            
        Returns:
            Número de tendencias guardadas
        """
        if df.empty:
            logger.info("No hay tendencias para guardar")
            return 0
        
        persisted = 0
        
        for _, row in df.iterrows():
            try:
                # Verificar si ya existe
                check_query = text("""
                    SELECT id FROM trend_signals
                    WHERE sector = :sector
                    AND term = :term
                    AND period_end >= :recent_date
                """)
                
                # Considerar duplicado si fue detectado en los últimos 3 días
                recent_date = datetime.utcnow() - timedelta(days=3)
                
                existing = self.db.execute(check_query, {
                    "sector": row['sector'],
                    "term": row['term'],
                    "recent_date": recent_date
                }).fetchone()
                
                if existing:
                    # Actualizar registro existente
                    update_query = text("""
                        UPDATE trend_signals
                        SET delta_pct = :delta_pct,
                            trend_status = :trend_status,
                            frequency = :frequency,
                            detected_at = :detected_at,
                            metadata = :metadata
                        WHERE id = :id
                    """)
                    
                    self.db.execute(update_query, {
                        "delta_pct": float(row['delta_pct']),
                        "trend_status": row['trend_label'],
                        "frequency": int(row['count_short']),
                        "detected_at": datetime.utcnow(),
                        "metadata": json.dumps({
                            "count_short": int(row['count_short']),
                            "count_long": int(row['count_long']),
                            "freq_short": float(row['freq_short']),
                            "freq_long": float(row['freq_long'])
                        }),
                        "id": existing[0]
                    })
                    
                    logger.debug(f"Tendencia actualizada: {row['term']}")
                else:
                    # Insertar nueva tendencia
                    insert_query = text("""
                        INSERT INTO trend_signals (
                            sector, term, frequency, delta_pct,
                            trend_status, period_start, period_end,
                            detected_at, metadata
                        )
                        VALUES (
                            :sector, :term, :frequency, :delta_pct,
                            :trend_status, :period_start, :period_end,
                            :detected_at, :metadata
                        )
                    """)
                    
                    self.db.execute(insert_query, {
                        "sector": row['sector'],
                        "term": row['term'],
                        "frequency": int(row['count_short']),
                        "delta_pct": float(row['delta_pct']),
                        "trend_status": row['trend_label'],
                        "period_start": row['period_start'],
                        "period_end": row['period_end'],
                        "detected_at": datetime.utcnow(),
                        "metadata": json.dumps({
                            "count_short": int(row['count_short']),
                            "count_long": int(row['count_long']),
                            "freq_short": float(row['freq_short']),
                            "freq_long": float(row['freq_long'])
                        })
                    })
                    
                    logger.debug(f"Tendencia insertada: {row['term']}")
                
                persisted += 1
                
            except Exception as e:
                logger.error(f"Error guardando tendencia {row.get('term')}: {e}")
                continue
        
        self.db.commit()
        logger.info(f"Guardadas {persisted}/{len(df)} tendencias")
        
        return persisted
    
    def get_recent_trends(
        self,
        sector: Optional[str] = None,
        trend_type: Optional[str] = None,
        limit: int = 20
    ) -> pd.DataFrame:
        """
        Obtener tendencias recientes
        
        Args:
            sector: Filtrar por sector
            trend_type: Filtrar por tipo (rising/falling/stable)
            limit: Número máximo de resultados
            
        Returns:
            DataFrame con tendencias
        """
        conditions = ["1=1"]
        params = {"limit": limit}
        
        if sector:
            conditions.append("sector = :sector")
            params["sector"] = sector
        
        if trend_type:
            conditions.append("trend_status = :trend_type")
            params["trend_type"] = trend_type
        
        where_clause = " AND ".join(conditions)
        
        query = text(f"""
            SELECT 
                sector,
                term,
                frequency,
                delta_pct,
                trend_status,
                detected_at
            FROM trend_signals
            WHERE {where_clause}
            ORDER BY detected_at DESC, ABS(delta_pct) DESC
            LIMIT :limit
        """)
        
        result = self.db.execute(query, params)
        rows = result.fetchall()
        
        if not rows:
            return pd.DataFrame()
        
        data = [{
            'sector': r[0],
            'term': r[1],
            'frequency': r[2],
            'delta_pct': r[3],
            'trend_status': r[4],
            'detected_at': r[5]
        } for r in rows]
        
        return pd.DataFrame(data)
