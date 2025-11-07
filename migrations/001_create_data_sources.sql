-- Migration: Create data_sources table
-- Date: 2024-01-15

-- UP Migration
CREATE TABLE IF NOT EXISTS data_sources (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    config_json JSONB NOT NULL,
    last_run_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR NOT NULL DEFAULT 'idle',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes
CREATE INDEX idx_data_sources_client_id ON data_sources(client_id);
CREATE INDEX idx_data_sources_status ON data_sources(status);

-- Add comment
COMMENT ON TABLE data_sources IS 'External data connectors for ETL ingestion';

-- DOWN Migration (for rollback)
-- DROP INDEX IF EXISTS idx_data_sources_status;
-- DROP INDEX IF EXISTS idx_data_sources_client_id;
-- DROP TABLE IF EXISTS data_sources;
