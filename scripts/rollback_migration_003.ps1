# Rollback de migración 003 en Windows

Write-Host "==========================================" -ForegroundColor Red
Write-Host "Rollback Migración 003: Analytics Tables" -ForegroundColor Red
Write-Host "==========================================" -ForegroundColor Red
Write-Host ""
Write-Host "ADVERTENCIA: Esto eliminará todas las tablas de analytics:" -ForegroundColor Yellow
Write-Host "  - kpi_summary" -ForegroundColor White
Write-Host "  - text_summary" -ForegroundColor White
Write-Host "  - trend_signals" -ForegroundColor White
Write-Host "  - clusters" -ForegroundColor White
Write-Host "  - anomaly_log" -ForegroundColor White
Write-Host ""

$confirm = Read-Host "¿Está seguro? (escriba 'SI' para continuar)"

if ($confirm -ne "SI") {
    Write-Host "Rollback cancelado" -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "Ejecutando rollback..." -ForegroundColor Yellow

Get-Content migrations\003_rollback_analytics_tables.sql | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "✓ Rollback completado" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "✗ Error en rollback" -ForegroundColor Red
}
