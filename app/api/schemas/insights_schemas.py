"""
Schemas Pydantic para endpoints de Insights
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class InsightSummary(BaseModel):
    """Schema para resumen de insight"""
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
    delta_pct: Optional[float] = None
    status: str
    period_start: datetime


class TextAnalysisSummary(BaseModel):
    """Schema para análisis de texto"""
    sentiment: str
    sentiment_score: Optional[float] = None
    keywords: List[str]
    created_at: datetime


class ClientInsightDetail(BaseModel):
    """Schema para detalle completo de cliente con todos los análisis"""
    client_id: int
    insight: Optional[InsightDetail] = None
    kpis: List[KPISummary] = []
    trends: List[TrendSignal] = []
    text_analysis: List[TextAnalysisSummary] = []


class GlobalStats(BaseModel):
    """Schema para estadísticas globales"""
    total_clients: int
    total_insights: int
    total_kpis: int
    total_trends: int
    total_text_records: int
    risk_distribution: Dict[str, int]
    opportunity_distribution: Dict[str, int]
    last_update: datetime


class SearchResult(BaseModel):
    """Schema para resultados de búsqueda"""
    result_type: str  # "insight", "trend", "kpi"
    client_id: Optional[int] = None
    title: str
    description: str
    relevance_score: float
    date: datetime
