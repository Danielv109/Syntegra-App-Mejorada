# Verificar tablas de analytics en Windows

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Verificando Tablas de Analytics" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Verificar tablas
Write-Host ""
Write-Host "Tablas creadas:" -ForegroundColor Yellow

$checkTables = @"
SELECT 
    table_name,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_name)::regclass)) as size
FROM information_schema.tables
WHERE table_schema = 'public' 
AND table_name IN ('kpi_summary', 'text_summary', 'trend_signals', 'clusters', 'anomaly_log')
ORDER BY table_name;
"@

$checkTables | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db

# Verificar índices
Write-Host ""
Write-Host "Índices creados:" -ForegroundColor Yellow

$checkIndices = @"
SELECT 
    tablename,
    COUNT(*) as num_indices
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename IN ('kpi_summary', 'text_summary', 'trend_signals', 'clusters', 'anomaly_log')
GROUP BY tablename
ORDER BY tablename;
"@

$checkIndices | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db

# Verificar tipos ENUM
Write-Host ""
Write-Host "Tipos ENUM creados:" -ForegroundColor Yellow

$checkEnums = @"
SELECT DISTINCT
    typname as enum_name
FROM pg_type
WHERE typname IN ('trend_status', 'anomaly_severity')
ORDER BY typname;
"@

$checkEnums | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "✓ Verificación completada" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
