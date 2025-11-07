-- Verification script for analytics tables
-- Usage: psql -U syntegra_user -d syntegra_db -f verify_analytics_tables.sql

\echo '=========================================='
\echo 'Verificando Tablas de Analytics'
\echo '=========================================='

-- Verificar tablas existentes
\echo ''
\echo 'Tablas creadas:'
SELECT 
    table_name,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_name)::regclass)) as size
FROM information_schema.tables
WHERE table_schema = 'public' 
AND table_name IN ('kpi_summary', 'text_summary', 'trend_signals', 'clusters', 'anomaly_log')
ORDER BY table_name;

-- Verificar índices
\echo ''
\echo 'Índices creados:'
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename IN ('kpi_summary', 'text_summary', 'trend_signals', 'clusters', 'anomaly_log')
ORDER BY tablename, indexname;

-- Verificar tipos ENUM
\echo ''
\echo 'Tipos ENUM creados:'
SELECT 
    typname as enum_name,
    enumlabel as enum_value
FROM pg_type
JOIN pg_enum ON pg_type.oid = pg_enum.enumtypid
WHERE typname IN ('trend_status', 'anomaly_severity')
ORDER BY typname, enumsortorder;

-- Verificar extensión pgvector
\echo ''
\echo 'Verificando pgvector:'
SELECT 
    extname as extension_name,
    extversion as version
FROM pg_extension
WHERE extname = 'vector';

-- Estructura de cada tabla
\echo ''
\echo '=========================================='
\echo 'Estructura de kpi_summary:'
\echo '=========================================='
\d kpi_summary

\echo ''
\echo '=========================================='
\echo 'Estructura de text_summary:'
\echo '=========================================='
\d text_summary

\echo ''
\echo '=========================================='
\echo 'Estructura de trend_signals:'
\echo '=========================================='
\d trend_signals

\echo ''
\echo '=========================================='
\echo 'Estructura de clusters:'
\echo '=========================================='
\d clusters

\echo ''
\echo '=========================================='
\echo 'Estructura de anomaly_log:'
\echo '=========================================='
\d anomaly_log

\echo ''
\echo '=========================================='
\echo '✅ Verificación completada'
\echo '=========================================='
