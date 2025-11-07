# PowerShell script para ejecutar migración 003 en Windows

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Ejecutando Migración 003: Analytics Tables" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Variables de entorno desde .env
$env:POSTGRES_HOST = "postgres"
$env:POSTGRES_PORT = "5432"
$env:POSTGRES_DB = "syntegra_db"
$env:POSTGRES_USER = "syntegra_user"

Write-Host ""
Write-Host "1. Verificando extensión pgvector..." -ForegroundColor Yellow

# Verificar pgvector
$checkVector = @"
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
"@

$result = $checkVector | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db -t

if ([string]::IsNullOrWhiteSpace($result)) {
    Write-Host "   Instalando pgvector..." -ForegroundColor Yellow
    "CREATE EXTENSION IF NOT EXISTS vector;" | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db
} else {
    Write-Host "   ✓ pgvector ya está instalado" -ForegroundColor Green
}

# Ejecutar migración
Write-Host ""
Write-Host "2. Ejecutando migración..." -ForegroundColor Yellow

Get-Content migrations\003_create_analytics_tables.sql | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ Migración ejecutada correctamente" -ForegroundColor Green
} else {
    Write-Host "   ✗ Error ejecutando migración" -ForegroundColor Red
    exit 1
}

# Verificar tablas creadas
Write-Host ""
Write-Host "3. Verificando tablas creadas..." -ForegroundColor Yellow

$verifyTables = @"
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('kpi_summary', 'text_summary', 'trend_signals', 'clusters', 'anomaly_log')
ORDER BY table_name;
"@

$verifyTables | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db

# Verificar índices
Write-Host ""
Write-Host "4. Verificando índices creados..." -ForegroundColor Yellow

$verifyIndices = @"
SELECT COUNT(*) as total_indices 
FROM pg_indexes 
WHERE schemaname = 'public' 
AND tablename IN ('kpi_summary', 'text_summary', 'trend_signals', 'clusters', 'anomaly_log');
"@

$verifyIndices | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "✓ Migración 003 completada exitosamente" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para ver detalles completos:" -ForegroundColor Cyan
Write-Host "  .\scripts\verify_analytics_tables.ps1" -ForegroundColor White
