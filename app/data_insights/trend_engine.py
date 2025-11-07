"""
Trend Engine - Detección automática de tendencias emergentes
"""
import logging
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
from collections import Counter

logger = logging.getLogger(__name__)


class TrendEngine:
    """Motor de detección de tendencias basado en keywords"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def detect_trends_for_sector(
        self,
        sector: str,
        window_short: int = 7,
        window_long: int = 30,
        min_delta: float = 5.0
    ) -> pd.DataFrame:
        """
        Detectar tendencias emergentes - VERSIÓN SIMPLIFICADA
        """
        logger.info(f"Detectando tendencias para sector: {sector}")
        
        # Definir período
        from datetime import timezone
        end_date = datetime.now(timezone.utc)
        long_start = end_date - timedelta(days=window_long)
        
        # Obtener ALL keywords del período
        query = text("""
            SELECT keywords, created_at
            FROM text_summary
            WHERE created_at >= :start_date
            ORDER BY created_at
        """)
        
        result = self.db.execute(query, {"start_date": long_start})
        rows = result.fetchall()
        
        if not rows:
            logger.info("No hay datos en text_summary")
            return pd.DataFrame()
        
        logger.info(f"Encontrados {len(rows)} registros")
        
        # Extraer keywords
        all_keywords = []
        for row in rows:
            keywords = row[0]
            if isinstance(keywords, list):
                for kw in keywords:
                    all_keywords.append(kw.strip().lower())
        
        if not all_keywords:
            logger.info("No hay keywords")
            return pd.DataFrame()
        
        logger.info(f"Total keywords: {len(all_keywords)}")
        
        # Contar frecuencias
        freq_counter = Counter(all_keywords)
        
        # Filtrar keywords significativas (freq >= 2)
        significant = {k: v for k, v in freq_counter.items() if v >= 2}
        
        if not significant:
            logger.info("No hay keywords con frecuencia >= 2")
            return pd.DataFrame()
        
        logger.info(f"Keywords con freq >= 2: {len(significant)}")
        
        # Crear DataFrame
        df = pd.DataFrame([
            {
                'sector': sector,
                'term': term,
                'frequency': count,
                'freq_short': count,
                'freq_long': count,
                'delta_pct': (count / len(all_keywords) * 100),
                'status': 'emergent' if count >= 5 else 'stable',  # CAMBIAR: solo usar emergent/stable/declining
                'period_start': long_start,
                'period_end': end_date
            }
            for term, count in significant.items()
        ])
        
        # Ordenar por frecuencia
        df = df.sort_values('frequency', ascending=False)
        
        logger.info(f"✓ Detectadas {len(df)} tendencias")
        
        return df
    
    def persist_trends(self, df_trends: pd.DataFrame) -> int:
        """
        Guardar tendencias en la base de datos - CORREGIDO
        """
        if df_trends.empty:
            logger.warning("DataFrame vacío, nada que persistir")
            return 0
        
        persisted = 0
        
        for _, row in df_trends.iterrows():
            try:
                # Convertir Pandas Timestamp a datetime Python
                period_start = row['period_start']
                period_end = row['period_end']
                
                if hasattr(period_start, 'to_pydatetime'):
                    period_start = period_start.to_pydatetime()
                if hasattr(period_end, 'to_pydatetime'):
                    period_end = period_end.to_pydatetime()
                
                # Verificar si ya existe
                check_query = text("""
                    SELECT id FROM trend_signals
                    WHERE sector = :sector
                    AND term = :term
                    AND DATE(period_start) = DATE(:period_start)
                """)
                
                existing = self.db.execute(check_query, {
                    "sector": str(row['sector']),
                    "term": str(row['term']),
                    "period_start": period_start
                }).fetchone()
                
                if existing:
                    # Actualizar
                    update_query = text("""
                        UPDATE trend_signals
                        SET frequency = :frequency,
                            delta_pct = :delta_pct,
                            status = CAST(:status AS trend_status),
                            metadata = CAST(:metadata AS jsonb)
                        WHERE id = :id
                    """)
                    
                    self.db.execute(update_query, {
                        "frequency": int(row['frequency']),
                        "delta_pct": float(row['delta_pct']),
                        "status": str(row['status']),
                        "metadata": json.dumps({"method": "frequency"}),
                        "id": existing[0]
                    })
                    logger.debug(f"Actualizada tendencia: {row['term']}")
                else:
                    # Insertar - USAR TODOS LOS PARÁMETROS CON :
                    insert_query = text("""
                        INSERT INTO trend_signals (
                            sector, term, period_start, period_end,
                            frequency, delta_pct, status, metadata
                        )
                        VALUES (
                            :sector, :term, :period_start, :period_end,
                            :frequency, :delta_pct, CAST(:status AS trend_status), CAST(:metadata AS jsonb)
                        )
                    """)
                    
                    self.db.execute(insert_query, {
                        "sector": str(row['sector']),
                        "term": str(row['term']),
                        "period_start": period_start,
                        "period_end": period_end,
                        "frequency": int(row['frequency']),
                        "delta_pct": float(row['delta_pct']),
                        "status": str(row['status']),
                        "metadata": json.dumps({"method": "frequency"})
                    })
                    logger.debug(f"Insertada tendencia: {row['term']}")
                
                persisted += 1
                
            except Exception as e:
                logger.error(f"Error persistiendo '{row['term']}': {e}")
                self.db.rollback()  # IMPORTANTE: rollback después de error
                continue
        
        self.db.commit()
        logger.info(f"✓ Persistidas {persisted}/{len(df_trends)} tendencias")
        
        return persisted
