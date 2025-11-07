Write-Host "🚀 Iniciando servicios y ejecutando migración..." -ForegroundColor Cyan

# 1. Iniciar Docker
Write-Host ""
Write-Host "1. Iniciando Docker Compose..." -ForegroundColor Yellow
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error iniciando Docker" -ForegroundColor Red
    exit 1
}

# 2. Esperar a que PostgreSQL esté listo
Write-Host ""
Write-Host "2. Esperando a que PostgreSQL esté listo..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# 3. Verificar conexión
Write-Host ""
Write-Host "3. Verificando conexión a PostgreSQL..." -ForegroundColor Yellow
$testQuery = "SELECT 1;"
$testResult = echo $testQuery | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ No se puede conectar a PostgreSQL" -ForegroundColor Red
    Write-Host "Esperando 10 segundos más..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}

# 4. Ejecutar migración
Write-Host ""
Write-Host "4. Ejecutando migración 003..." -ForegroundColor Yellow
Get-Content migrations\003_create_analytics_tables.sql | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Migración ejecutada correctamente" -ForegroundColor Green
} else {
    Write-Host "   ❌ Error ejecutando migración" -ForegroundColor Red
    exit 1
}

# 5. Verificar tablas
Write-Host ""
Write-Host "5. Verificando tablas creadas..." -ForegroundColor Yellow
$verifyQuery = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('kpi_summary', 'text_summary', 'trend_signals', 'clusters', 'anomaly_log') ORDER BY table_name;"
echo $verifyQuery | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db

Write-Host ""
Write-Host "✅ ¡Proceso completado!" -ForegroundColor Green
