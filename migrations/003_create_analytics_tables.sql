-- Migration: Create analytics tables (kpi_summary, text_summary, trend_signals, clusters, anomaly_log)
-- Date: 2024-01-16
-- Author: SYNTEGRA Team

-- UP Migration
BEGIN;

-- ============================================================================
-- 1. kpi_summary - Resumen de KPIs calculados
-- ============================================================================
CREATE TABLE IF NOT EXISTS kpi_summary (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    source_id INTEGER REFERENCES data_sources(id) ON DELETE SET NULL,
    kpi_name VARCHAR(255) NOT NULL,
    kpi_value NUMERIC NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

-- Índices para kpi_summary
CREATE INDEX idx_kpi_summary_client_kpi_period 
    ON kpi_summary(client_id, kpi_name, period_start);
CREATE INDEX idx_kpi_summary_client_id 
    ON kpi_summary(client_id);
CREATE INDEX idx_kpi_summary_kpi_name 
    ON kpi_summary(kpi_name);
CREATE INDEX idx_kpi_summary_period_start 
    ON kpi_summary(period_start);

COMMENT ON TABLE kpi_summary IS 'Calculated KPIs with time periods';
COMMENT ON COLUMN kpi_summary.kpi_name IS 'KPI identifier (e.g., sales_mom, avg_ticket)';
COMMENT ON COLUMN kpi_summary.kpi_value IS 'Calculated numeric value';

-- ============================================================================
-- 2. text_summary - Análisis de texto con embeddings
-- ============================================================================
CREATE TABLE IF NOT EXISTS text_summary (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    source_id INTEGER REFERENCES data_sources(id) ON DELETE SET NULL,
    text_field TEXT NOT NULL,
    sentiment VARCHAR(50),
    sentiment_score NUMERIC,
    keywords JSONB,
    embedding VECTOR(384),
    language VARCHAR(10) DEFAULT 'es',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para text_summary
CREATE INDEX idx_text_summary_client_id 
    ON text_summary(client_id);
CREATE INDEX idx_text_summary_source_id 
    ON text_summary(source_id);
CREATE INDEX idx_text_summary_sentiment 
    ON text_summary(sentiment);
CREATE INDEX idx_text_summary_created_at 
    ON text_summary(created_at);
CREATE INDEX idx_text_summary_keywords 
    ON text_summary USING GIN(keywords);

-- Índice vectorial para búsqueda de similitud
CREATE INDEX idx_text_summary_embedding 
    ON text_summary USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

COMMENT ON TABLE text_summary IS 'Text analysis with sentiment and embeddings';
COMMENT ON COLUMN text_summary.embedding IS 'Vector embedding (384 dimensions)';
COMMENT ON COLUMN text_summary.keywords IS 'Extracted keywords in JSON format';

-- ============================================================================
-- 3. trend_signals - Señales de tendencias
-- ============================================================================
CREATE TYPE trend_status AS ENUM ('emergent', 'stable', 'declining');

CREATE TABLE IF NOT EXISTS trend_signals (
    id SERIAL PRIMARY KEY,
    sector VARCHAR(255) NOT NULL,
    term VARCHAR(255) NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    frequency INTEGER NOT NULL DEFAULT 0,
    delta_pct NUMERIC,
    status trend_status NOT NULL DEFAULT 'stable',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para trend_signals
CREATE INDEX idx_trend_signals_sector 
    ON trend_signals(sector);
CREATE INDEX idx_trend_signals_term 
    ON trend_signals(term);
CREATE INDEX idx_trend_signals_status 
    ON trend_signals(status);
CREATE INDEX idx_trend_signals_period 
    ON trend_signals(period_start, period_end);
CREATE INDEX idx_trend_signals_sector_term 
    ON trend_signals(sector, term);
CREATE INDEX idx_trend_signals_delta_pct 
    ON trend_signals(delta_pct);

COMMENT ON TABLE trend_signals IS 'Detected trends and signals by sector';
COMMENT ON COLUMN trend_signals.delta_pct IS 'Percentage change (growth or decline)';
COMMENT ON COLUMN trend_signals.status IS 'Trend status: emergent, stable, or declining';

-- ============================================================================
-- 4. clusters - Agrupaciones de clientes
-- ============================================================================
CREATE TABLE IF NOT EXISTS clusters (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    cluster_id INTEGER NOT NULL,
    cluster_name VARCHAR(255),
    features_json JSONB NOT NULL,
    centroid JSONB,
    distance_to_centroid NUMERIC,
    silhouette_score NUMERIC,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Índices para clusters
CREATE INDEX idx_clusters_client_id 
    ON clusters(client_id);
CREATE INDEX idx_clusters_cluster_id 
    ON clusters(cluster_id);
CREATE INDEX idx_clusters_client_cluster 
    ON clusters(client_id, cluster_id);
CREATE INDEX idx_clusters_features 
    ON clusters USING GIN(features_json);

COMMENT ON TABLE clusters IS 'Client clustering with features and centroids';
COMMENT ON COLUMN clusters.features_json IS 'Features used for clustering';
COMMENT ON COLUMN clusters.centroid IS 'Cluster centroid coordinates';

-- ============================================================================
-- 5. anomaly_log - Registro de anomalías detectadas
-- ============================================================================
CREATE TYPE anomaly_severity AS ENUM ('low', 'medium', 'high', 'critical');

CREATE TABLE IF NOT EXISTS anomaly_log (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    source_id INTEGER REFERENCES data_sources(id) ON DELETE SET NULL,
    kpi_name VARCHAR(255) NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    value NUMERIC NOT NULL,
    expected_value NUMERIC,
    deviation NUMERIC,
    reason TEXT,
    severity anomaly_severity NOT NULL DEFAULT 'medium',
    method VARCHAR(100),
    metadata JSONB
);

-- Índices para anomaly_log
CREATE INDEX idx_anomaly_log_client_id 
    ON anomaly_log(client_id);
CREATE INDEX idx_anomaly_log_source_id 
    ON anomaly_log(source_id);
CREATE INDEX idx_anomaly_log_kpi_name 
    ON anomaly_log(kpi_name);
CREATE INDEX idx_anomaly_log_detected_at 
    ON anomaly_log(detected_at);
CREATE INDEX idx_anomaly_log_severity 
    ON anomaly_log(severity);
CREATE INDEX idx_anomaly_log_client_kpi 
    ON anomaly_log(client_id, kpi_name);

COMMENT ON TABLE anomaly_log IS 'Log of detected anomalies with severity';
COMMENT ON COLUMN anomaly_log.method IS 'Detection method used (e.g., isolation_forest)';
COMMENT ON COLUMN anomaly_log.deviation IS 'Standard deviations from expected value';

COMMIT;

-- ============================================================================
-- DOWN Migration (Rollback)
-- ============================================================================
-- To rollback, run the following commands:

-- DROP INDEX IF EXISTS idx_anomaly_log_client_kpi;
-- DROP INDEX IF EXISTS idx_anomaly_log_severity;
-- DROP INDEX IF EXISTS idx_anomaly_log_detected_at;
-- DROP INDEX IF EXISTS idx_anomaly_log_kpi_name;
-- DROP INDEX IF EXISTS idx_anomaly_log_source_id;
-- DROP INDEX IF EXISTS idx_anomaly_log_client_id;
-- DROP TABLE IF EXISTS anomaly_log;
-- DROP TYPE IF EXISTS anomaly_severity;

-- DROP INDEX IF EXISTS idx_clusters_features;
-- DROP INDEX IF EXISTS idx_clusters_client_cluster;
-- DROP INDEX IF EXISTS idx_clusters_cluster_id;
-- DROP INDEX IF EXISTS idx_clusters_client_id;
-- DROP TABLE IF EXISTS clusters;

-- DROP INDEX IF EXISTS idx_trend_signals_delta_pct;
-- DROP INDEX IF EXISTS idx_trend_signals_sector_term;
-- DROP INDEX IF EXISTS idx_trend_signals_period;
-- DROP INDEX IF EXISTS idx_trend_signals_status;
-- DROP INDEX IF EXISTS idx_trend_signals_term;
-- DROP INDEX IF EXISTS idx_trend_signals_sector;
-- DROP TABLE IF EXISTS trend_signals;
-- DROP TYPE IF EXISTS trend_status;

-- DROP INDEX IF EXISTS idx_text_summary_embedding;
-- DROP INDEX IF EXISTS idx_text_summary_keywords;
-- DROP INDEX IF EXISTS idx_text_summary_created_at;
-- DROP INDEX IF EXISTS idx_text_summary_sentiment;
-- DROP INDEX IF EXISTS idx_text_summary_source_id;
-- DROP INDEX IF EXISTS idx_text_summary_client_id;
-- DROP TABLE IF EXISTS text_summary;

-- DROP INDEX IF EXISTS idx_kpi_summary_period_start;
-- DROP INDEX IF EXISTS idx_kpi_summary_kpi_name;
-- DROP INDEX IF EXISTS idx_kpi_summary_client_id;
-- DROP INDEX IF EXISTS idx_kpi_summary_client_kpi_period;
-- DROP TABLE IF EXISTS kpi_summary;
