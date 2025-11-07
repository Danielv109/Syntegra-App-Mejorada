#!/bin/bash

# Script para hacer rollback de la migración 003

set -e

echo "=========================================="
echo "Rollback Migración 003: Analytics Tables"
echo "=========================================="
echo ""
echo "⚠️  ADVERTENCIA: Esto eliminará todas las tablas de analytics"
echo "   - kpi_summary"
echo "   - text_summary"
echo "   - trend_signals"
echo "   - clusters"
echo "   - anomaly_log"
echo ""
read -p "¿Está seguro? (escriba 'SI' para continuar): " confirm

if [ "$confirm" != "SI" ]; then
    echo "Rollback cancelado"
    exit 0
fi

# Variables de entorno
DB_HOST=${POSTGRES_HOST:-postgres}
DB_USER=${POSTGRES_USER:-syntegra_user}
DB_NAME=${POSTGRES_DB:-syntegra_db}

echo ""
echo "Ejecutando rollback..."

cat migrations/003_rollback_analytics_tables.sql | docker-compose exec -T postgres psql -U $DB_USER -d $DB_NAME

echo ""
echo "=========================================="
echo "✅ Rollback completado"
echo "=========================================="
