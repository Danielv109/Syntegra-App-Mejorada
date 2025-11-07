#!/bin/bash

# Script para ejecutar la migración 003 (Analytics Tables)

set -e

echo "=========================================="
echo "Ejecutando Migración 003: Analytics Tables"
echo "=========================================="

# Variables de entorno desde .env
DB_HOST=${POSTGRES_HOST:-postgres}
DB_PORT=${POSTGRES_PORT:-5432}
DB_NAME=${POSTGRES_DB:-syntegra_db}
DB_USER=${POSTGRES_USER:-syntegra_user}
DB_PASSWORD=${POSTGRES_PASSWORD:-syntegra_secure_password}

# Función para ejecutar SQL
run_sql() {
    docker-compose exec -T postgres psql -U $DB_USER -d $DB_NAME "$@"
}

# Verificar que pgvector esté instalado
echo ""
echo "1. Verificando extensión pgvector..."
run_sql -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';" || {
    echo "⚠️  pgvector no encontrado, intentando instalar..."
    run_sql -c "CREATE EXTENSION IF NOT EXISTS vector;"
}

# Ejecutar migración
echo ""
echo "2. Ejecutando migración..."
cat migrations/003_create_analytics_tables.sql | run_sql

# Verificar tablas creadas
echo ""
echo "3. Verificando tablas creadas..."
run_sql -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('kpi_summary', 'text_summary', 'trend_signals', 'clusters', 'anomaly_log');"

# Verificar índices
echo ""
echo "4. Verificando índices..."
run_sql -c "SELECT COUNT(*) as total_indices FROM pg_indexes WHERE schemaname = 'public' AND tablename IN ('kpi_summary', 'text_summary', 'trend_signals', 'clusters', 'anomaly_log');"

echo ""
echo "=========================================="
echo "✅ Migración 003 completada exitosamente"
echo "=========================================="
echo ""
echo "Para verificar detalles, ejecute:"
echo "  docker-compose exec postgres psql -U $DB_USER -d $DB_NAME -f /scripts/verify_analytics_tables.sql"
echo ""
echo "Para rollback, ejecute:"
echo "  cat migrations/003_rollback_analytics_tables.sql | docker-compose exec -T postgres psql -U $DB_USER -d $DB_NAME"
