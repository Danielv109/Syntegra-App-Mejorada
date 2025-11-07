"""
Schemas Pydantic para endpoints de insights
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class InsightSummary(BaseModel):
    """Schema para listado de insights"""
    id: int
    client_id: int
    summary_text: str
    risk_level: str
    opportunity_level: str
    findings_count: int
    generated_at: datetime
    
    class Config:
        from_attributes = True


class InsightDetail(BaseModel):
    """Schema para detalle completo de insight"""
    id: int
    client_id: int
    summary_text: str
    key_findings: List[str]
    risk_level: str
    opportunity_level: str
    metrics: Optional[Dict[str, Any]] = None
    generated_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class KPISummary(BaseModel):
    """Schema para KPI"""
    kpi_name: str
    kpi_value: float
    period_start: datetime
    period_end: datetime
    calculated_at: datetime


class TrendSignal(BaseModel):
    """Schema para tendencia"""
    sector: str
    term: str
    frequency: int
    delta_pct: float
    status: str
    period_start: datetime


class TextAnalysisSummary(BaseModel):
    """Schema para análisis de texto"""
    sentiment: str
    sentiment_score: float
    keywords: List[str]
    created_at: datetime


class ClientInsightDetail(BaseModel):
    """Schema completo con todos los datos de un cliente"""
    client_id: int
    insight: Optional[InsightDetail] = None
    kpis: List[KPISummary] = []
    trends: List[TrendSignal] = []
    text_analysis: List[TextAnalysisSummary] = []
    
    class Config:
        from_attributes = True


class GlobalStats(BaseModel):
    """Schema para estadísticas globales"""
    total_clients: int
    total_insights: int
    total_kpis: int
    total_trends: int
    total_text_records: int
    high_risk_clients: int
    high_opportunity_clients: int
    emergent_trends_count: int


class SearchResult(BaseModel):
    """Schema para resultados de búsqueda"""
    type: str  # 'insight', 'trend', 'kpi'
    client_id: Optional[int] = None
    content: str
    relevance_score: float
    created_at: datetime
