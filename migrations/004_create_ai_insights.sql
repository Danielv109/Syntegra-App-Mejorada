-- Migración 004: Tabla de insights generados por IA
-- Fecha: 2025-11-07

-- Crear tabla ai_insights
CREATE TABLE IF NOT EXISTS ai_insights (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Contenido del insight
    summary_text TEXT NOT NULL,
    key_findings JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Niveles de riesgo y oportunidad
    risk_level VARCHAR(20) NOT NULL DEFAULT 'low',
    opportunity_level VARCHAR(20) NOT NULL DEFAULT 'medium',
    
    -- Métricas de soporte
    metrics JSONB,
    
    -- Timestamps
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Crear índices
CREATE INDEX idx_ai_insights_client_id ON ai_insights(client_id);
CREATE INDEX idx_ai_insights_generated_at ON ai_insights(generated_at DESC);
CREATE INDEX idx_ai_insights_risk_level ON ai_insights(risk_level);
CREATE INDEX idx_ai_insights_opportunity_level ON ai_insights(opportunity_level);
CREATE INDEX idx_ai_insights_key_findings ON ai_insights USING gin(key_findings);

-- Índice único para evitar duplicados por día (usando expresión)
CREATE UNIQUE INDEX unique_client_insight_day 
ON ai_insights (client_id, DATE(generated_at));

-- Comentarios
COMMENT ON TABLE ai_insights IS 'Insights automáticos generados por IA combinando análisis de texto, KPIs y tendencias';
COMMENT ON COLUMN ai_insights.summary_text IS 'Resumen ejecutivo del análisis';
COMMENT ON COLUMN ai_insights.key_findings IS 'Array JSON con hallazgos principales';
COMMENT ON COLUMN ai_insights.risk_level IS 'Nivel de riesgo: low, medium, high, critical';
COMMENT ON COLUMN ai_insights.opportunity_level IS 'Nivel de oportunidad: low, medium, high';
