Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Fix Dependencies & Deploy SYNTEGRA" -ForegroundColor Cyan
Write-Host "==========================================`n" -ForegroundColor Cyan

# 1. Limpiar contenedores anteriores
Write-Host "1. Limpiando contenedores anteriores..." -ForegroundColor Yellow
docker-compose down -v 2>&1 | Out-Null
Write-Host "   [OK] Limpieza completada`n" -ForegroundColor Green

# 2. Reconstruir imagenes
Write-Host "2. Reconstruyendo imagenes Docker..." -ForegroundColor Yellow
Write-Host "   (Esto puede tardar 3-5 minutos - Descargando modelo de spaCy...)..." -ForegroundColor Gray
Write-Host "   Warnings sobre 'version' o 'http2' son normales y pueden ignorarse" -ForegroundColor DarkGray

# Suprimir warnings conocidos y mostrar progreso
$env:COMPOSE_DOCKER_CLI_BUILD = "1"
$env:DOCKER_BUILDKIT = "1"

$buildOutput = docker-compose build --no-cache --progress=plain 2>&1 | Where-Object { 
    $_ -notmatch "version.*is obsolete" -and 
    $_ -notmatch "http2.*error reading preface"
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n   [ERROR] Error construyendo imagenes" -ForegroundColor Red
    Write-Host "`nOutput del error (ultimas 50 lineas):" -ForegroundColor Red
    $buildOutput | Select-Object -Last 50 | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
    
    Write-Host "`nSugerencias:" -ForegroundColor Yellow
    Write-Host "   1. Verifica tu conexion a Internet" -ForegroundColor White
    Write-Host "   2. Si persiste, intenta:" -ForegroundColor White
    Write-Host "      docker system prune -a" -ForegroundColor Cyan
    Write-Host "      docker-compose build --no-cache" -ForegroundColor Cyan
    exit 1
}

Write-Host "   [OK] Imagenes construidas correctamente`n" -ForegroundColor Green

# 3. Iniciar servicios
Write-Host "3. Iniciando servicios..." -ForegroundColor Yellow
Write-Host "   (Ignorando warnings de 'version' y 'http2')..." -ForegroundColor Gray

docker-compose up -d 2>&1 | Where-Object { 
    $_ -notmatch "version.*is obsolete" -and 
    $_ -notmatch "http2.*error reading preface" 
} | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "   [ERROR] Error iniciando servicios" -ForegroundColor Red
    exit 1
}

Write-Host "   [OK] Servicios iniciados`n" -ForegroundColor Green

# 4. Esperar a PostgreSQL
Write-Host "4. Esperando a que PostgreSQL este listo..." -ForegroundColor Yellow
$attempts = 0
$maxAttempts = 30

while ($attempts -lt $maxAttempts) {
    $testQuery = "SELECT 1;"
    $result = echo $testQuery | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   [OK] PostgreSQL esta listo`n" -ForegroundColor Green
        break
    }
    
    $attempts++
    Write-Host "   Intento $attempts/$maxAttempts..." -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

if ($attempts -eq $maxAttempts) {
    Write-Host "   [ERROR] Timeout esperando PostgreSQL" -ForegroundColor Red
    exit 1
}

# 5. Ejecutar migraciones
Write-Host "5. Ejecutando migraciones..." -ForegroundColor Yellow

# Obtener todos los archivos de migración (excepto rollbacks)
$migrations = Get-ChildItem migrations\*.sql | Where-Object { $_.Name -notmatch "rollback" } | Sort-Object Name

foreach ($migration in $migrations) {
    Write-Host "   Ejecutando $($migration.Name)..." -ForegroundColor Gray
    Get-Content $migration.FullName | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db 2>&1 | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   [ERROR] Error ejecutando $($migration.Name)" -ForegroundColor Red
        Write-Host "   Ejecute el rollback manualmente si es necesario" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "   [OK] Todas las migraciones ejecutadas correctamente`n" -ForegroundColor Green

# 6. Verificar tablas
Write-Host "6. Verificando tablas creadas..." -ForegroundColor Yellow

# Verificar tablas de analytics
$query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('kpi_summary', 'text_summary', 'trend_signals', 'clusters', 'anomaly_log') ORDER BY table_name;"

$tables = echo $query | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db -t

Write-Host "`n   Tablas de analytics creadas:" -ForegroundColor Green
Write-Host $tables -ForegroundColor White

# Mostrar TODAS las tablas
Write-Host "`n   Todas las tablas en la base de datos:" -ForegroundColor Cyan
docker-compose exec postgres psql -U syntegra_user -d syntegra_db -c "\dt" 2>&1 | Where-Object { $_ -notmatch "version.*is obsolete" }

# 7. Verificar servicios
Write-Host "`n7. Estado de servicios:" -ForegroundColor Yellow
docker-compose ps

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "[OK] Deployment completado exitosamente" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

Write-Host "`nAcceso a la aplicacion:" -ForegroundColor Cyan
Write-Host "  API: http://localhost:8000" -ForegroundColor White
Write-Host "  Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "`n"
