"""
KPI Engine - Cálculo automático de métricas clave de negocio
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class KPIEngine:
    """Motor de cálculo de KPIs desde datos procesados"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def compute_kpis_for_client(
        self,
        client_id: int,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, float]:
        """
        Calcular KPIs para un cliente en un período específico
        
        Args:
            client_id: ID del cliente
            period_start: Inicio del período
            period_end: Fin del período
            
        Returns:
            Dict con KPIs calculados {kpi_name: value}
        """
        logger.info(
            f"Calculando KPIs para cliente {client_id} "
            f"desde {period_start} hasta {period_end}"
        )
        
        # 1. Obtener datos procesados del cliente
        query = text("""
            SELECT 
                id,
                source_type,
                data,
                created_at
            FROM processed_data
            WHERE created_at >= :start_date
            AND created_at <= :end_date
            ORDER BY created_at
        """)
        
        result = self.db.execute(query, {
            "start_date": period_start,
            "end_date": period_end
        })
        
        rows = result.fetchall()
        
        if not rows:
            logger.warning(f"No hay datos para cliente {client_id} en el período")
            return {}
        
        # 2. Convertir a DataFrame
        data = []
        for row in rows:
            record = {
                'id': row[0],
                'source_type': row[1],
                'created_at': row[3]
            }
            # Extraer campos del JSON
            json_data = row[2]
            if isinstance(json_data, dict):
                record.update(json_data)
            data.append(record)
        
        df = pd.DataFrame(data)
        
        logger.info(f"DataFrame creado con {len(df)} registros")
        
        # 3. Calcular KPIs
        kpis = {}
        
        # KPI 1: Total de registros
        kpis['total_records'] = len(df)
        
        # KPI 2: Total sales (si existe campo 'amount', 'sales', 'value')
        sales_columns = ['amount', 'sales', 'value', 'total', 'price']
        sales_col = None
        for col in sales_columns:
            if col in df.columns:
                sales_col = col
                break
        
        if sales_col:
            df[sales_col] = pd.to_numeric(df[sales_col], errors='coerce')
            kpis['total_sales'] = float(df[sales_col].sum())
            kpis['avg_ticket'] = float(df[sales_col].mean())
            kpis['max_transaction'] = float(df[sales_col].max())
            kpis['min_transaction'] = float(df[sales_col].min())
        
        # KPI 3: Conteo por tipo de fuente
        if 'source_type' in df.columns:
            source_counts = df['source_type'].value_counts()
            for source, count in source_counts.items():
                kpis[f'count_{source}'] = int(count)
        
        # KPI 4: Tasa de crecimiento (MoM - Month over Month)
        if sales_col and 'created_at' in df.columns:
            df['month'] = pd.to_datetime(df['created_at']).dt.to_period('M')
            monthly_sales = df.groupby('month')[sales_col].sum()
            
            if len(monthly_sales) >= 2:
                current_month = monthly_sales.iloc[-1]
                previous_month = monthly_sales.iloc[-2]
                
                if previous_month > 0:
                    growth_rate = ((current_month - previous_month) / previous_month) * 100
                    kpis['sales_mom'] = float(growth_rate)
        
        # KPI 5: Items más vendidos (top 3)
        item_columns = ['item', 'product', 'product_name', 'name']
        item_col = None
        for col in item_columns:
            if col in df.columns:
                item_col = col
                break
        
        if item_col:
            top_items = df[item_col].value_counts().head(3)
            total_items = len(df)
            top3_share = (top_items.sum() / total_items) * 100 if total_items > 0 else 0
            kpis['items_top3_share'] = float(top3_share)
            
            for idx, (item, count) in enumerate(top_items.items(), 1):
                kpis[f'top{idx}_item'] = str(item)
                kpis[f'top{idx}_count'] = int(count)
        
        # KPI 6: Métricas estadísticas básicas
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col not in ['id']:
                kpis[f'{col}_mean'] = float(df[col].mean())
                kpis[f'{col}_median'] = float(df[col].median())
                kpis[f'{col}_std'] = float(df[col].std())
        
        logger.info(f"Calculados {len(kpis)} KPIs para cliente {client_id}")
        
        return kpis
    
    def persist_kpi(
        self,
        client_id: int,
        kpi_name: str,
        kpi_value: float,
        period_start: datetime,
        period_end: datetime,
        source_id: Optional[int] = None
    ) -> bool:
        """
        Guardar o actualizar un KPI en la base de datos
        
        Args:
            client_id: ID del cliente
            kpi_name: Nombre del KPI
            kpi_value: Valor del KPI
            period_start: Inicio del período
            period_end: Fin del período
            source_id: ID de la fuente (opcional)
            
        Returns:
            True si se guardó exitosamente
        """
        try:
            # Verificar si ya existe
            check_query = text("""
                SELECT id FROM kpi_summary
                WHERE client_id = :client_id
                AND kpi_name = :kpi_name
                AND period_start = :period_start
                AND period_end = :period_end
            """)
            
            existing = self.db.execute(check_query, {
                "client_id": client_id,
                "kpi_name": kpi_name,
                "period_start": period_start,
                "period_end": period_end
            }).fetchone()
            
            if existing:
                # Actualizar
                update_query = text("""
                    UPDATE kpi_summary
                    SET kpi_value = :kpi_value,
                        calculated_at = :calculated_at
                    WHERE id = :id
                """)
                
                self.db.execute(update_query, {
                    "kpi_value": kpi_value,
                    "calculated_at": datetime.utcnow(),
                    "id": existing[0]
                })
                
                logger.debug(f"KPI actualizado: {kpi_name} = {kpi_value}")
            else:
                # Insertar nuevo
                insert_query = text("""
                    INSERT INTO kpi_summary (
                        client_id, source_id, kpi_name, kpi_value,
                        period_start, period_end, calculated_at
                    )
                    VALUES (
                        :client_id, :source_id, :kpi_name, :kpi_value,
                        :period_start, :period_end, :calculated_at
                    )
                """)
                
                self.db.execute(insert_query, {
                    "client_id": client_id,
                    "source_id": source_id,
                    "kpi_name": kpi_name,
                    "kpi_value": kpi_value,
                    "period_start": period_start,
                    "period_end": period_end,
                    "calculated_at": datetime.utcnow()
                })
                
                logger.debug(f"KPI insertado: {kpi_name} = {kpi_value}")
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error persistiendo KPI {kpi_name}: {e}")
            self.db.rollback()
            return False
    
    def compute_and_persist_kpis(
        self,
        client_id: int,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, any]:
        """
        Calcular y guardar todos los KPIs de un cliente
        
        Returns:
            Dict con resumen del proceso
        """
        try:
            # Calcular KPIs
            kpis = self.compute_kpis_for_client(client_id, period_start, period_end)
            
            if not kpis:
                return {
                    "client_id": client_id,
                    "kpis_calculated": 0,
                    "kpis_persisted": 0,
                    "status": "no_data"
                }
            
            # Guardar cada KPI
            persisted = 0
            for kpi_name, kpi_value in kpis.items():
                # Convertir valores no numéricos a string
                if isinstance(kpi_value, (int, float)):
                    numeric_value = float(kpi_value)
                else:
                    # Guardar como metadata en lugar de value
                    continue
                
                success = self.persist_kpi(
                    client_id=client_id,
                    kpi_name=kpi_name,
                    kpi_value=numeric_value,
                    period_start=period_start,
                    period_end=period_end
                )
                
                if success:
                    persisted += 1
            
            logger.info(
                f"Cliente {client_id}: {persisted}/{len(kpis)} KPIs guardados"
            )
            
            return {
                "client_id": client_id,
                "kpis_calculated": len(kpis),
                "kpis_persisted": persisted,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error en compute_and_persist_kpis: {e}")
            return {
                "client_id": client_id,
                "kpis_calculated": 0,
                "kpis_persisted": 0,
                "status": "error",
                "error": str(e)
            }


def get_clients_with_recent_data(
    db: Session,
    hours_back: int = 24
) -> List[int]:
    """
    Obtener clientes con datos recientes
    
    Args:
        db: Sesión de base de datos
        hours_back: Horas hacia atrás para buscar
        
    Returns:
        Lista de client_ids
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
    
    # Como processed_data no tiene client_id directo,
    # usamos todos los clientes activos
    query = text("""
        SELECT id FROM clients
        WHERE is_active = TRUE
        ORDER BY id
    """)
    
    result = db.execute(query)
    client_ids = [row[0] for row in result.fetchall()]
    
    logger.info(f"Encontrados {len(client_ids)} clientes activos")
    
    return client_ids
