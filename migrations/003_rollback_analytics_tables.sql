-- Rollback Migration: Drop analytics tables
-- Date: 2024-01-16

BEGIN;

-- Drop anomaly_log
DROP INDEX IF EXISTS idx_anomaly_log_client_kpi;
DROP INDEX IF EXISTS idx_anomaly_log_severity;
DROP INDEX IF EXISTS idx_anomaly_log_detected_at;
DROP INDEX IF EXISTS idx_anomaly_log_kpi_name;
DROP INDEX IF EXISTS idx_anomaly_log_source_id;
DROP INDEX IF EXISTS idx_anomaly_log_client_id;
DROP TABLE IF EXISTS anomaly_log CASCADE;
DROP TYPE IF EXISTS anomaly_severity;

-- Drop clusters
DROP INDEX IF EXISTS idx_clusters_features;
DROP INDEX IF EXISTS idx_clusters_client_cluster;
DROP INDEX IF EXISTS idx_clusters_cluster_id;
DROP INDEX IF EXISTS idx_clusters_client_id;
DROP TABLE IF EXISTS clusters CASCADE;

-- Drop trend_signals
DROP INDEX IF EXISTS idx_trend_signals_delta_pct;
DROP INDEX IF EXISTS idx_trend_signals_sector_term;
DROP INDEX IF EXISTS idx_trend_signals_period;
DROP INDEX IF EXISTS idx_trend_signals_status;
DROP INDEX IF EXISTS idx_trend_signals_term;
DROP INDEX IF EXISTS idx_trend_signals_sector;
DROP TABLE IF EXISTS trend_signals CASCADE;
DROP TYPE IF EXISTS trend_status;

-- Drop text_summary
DROP INDEX IF EXISTS idx_text_summary_embedding;
DROP INDEX IF EXISTS idx_text_summary_keywords;
DROP INDEX IF EXISTS idx_text_summary_created_at;
DROP INDEX IF EXISTS idx_text_summary_sentiment;
DROP INDEX IF EXISTS idx_text_summary_source_id;
DROP INDEX IF EXISTS idx_text_summary_client_id;
DROP TABLE IF EXISTS text_summary CASCADE;

-- Drop kpi_summary
DROP INDEX IF EXISTS idx_kpi_summary_period_start;
DROP INDEX IF EXISTS idx_kpi_summary_kpi_name;
DROP INDEX IF EXISTS idx_kpi_summary_client_id;
DROP INDEX IF EXISTS idx_kpi_summary_client_kpi_period;
DROP TABLE IF EXISTS kpi_summary CASCADE;

COMMIT;

-- Confirmation message
DO $$ 
BEGIN 
    RAISE NOTICE 'Analytics tables rolled back successfully';
END $$;
