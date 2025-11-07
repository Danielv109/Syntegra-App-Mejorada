-- Migration: Create processed_data table
-- Date: 2024-01-15

-- UP Migration
CREATE TABLE IF NOT EXISTS processed_data (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index
CREATE INDEX idx_processed_data_source_type ON processed_data(source_type);
CREATE INDEX idx_processed_data_created_at ON processed_data(created_at);

-- Add comment
COMMENT ON TABLE processed_data IS 'Cleaned and normalized data from external sources';

-- DOWN Migration (for rollback)
-- DROP INDEX IF EXISTS idx_processed_data_created_at;
-- DROP INDEX IF EXISTS idx_processed_data_source_type;
-- DROP TABLE IF EXISTS processed_data;
