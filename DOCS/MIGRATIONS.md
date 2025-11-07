# Database Migrations - SYNTEGRA

## Migraciones Disponibles

### 001 - Data Sources

- **Archivo**: `migrations/001_create_data_sources.sql`
- **Descripción**: Crea tabla `data_sources` para conectores externos
- **Fecha**: 2024-01-15

### 002 - Processed Data

- **Archivo**: `migrations/002_create_processed_data.sql`
- **Descripción**: Crea tabla `processed_data` para datos normalizados
- **Fecha**: 2024-01-15

### 003 - Analytics Tables

- **Archivo**: `migrations/003_create_analytics_tables.sql`
- **Descripción**: Crea tablas de analytics (kpi_summary, text_summary, trend_signals, clusters, anomaly_log)
- **Fecha**: 2024-01-16
- **Dependencias**: Requiere extensión `pgvector`

## Tablas Creadas en Migración 003

### 1. kpi_summary

Almacena KPIs calculados con períodos temporales.

**Columnas:**

- `id`: Primary key
- `client_id`: Referencia a cliente
- `source_id`: Referencia a fuente de datos (nullable)
- `kpi_name`: Nombre del KPI (ej: sales_mom, avg_ticket)
- `kpi_value`: Valor numérico calculado
- `period_start`, `period_end`: Período del KPI
- `calculated_at`: Fecha de cálculo
- `metadata`: Información adicional en JSON

**Índices:**

- Compuesto: (client_id, kpi_name, period_start)
- Individual: client_id, kpi_name, period_start

### 2. text_summary

Análisis de texto con embeddings vectoriales.

**Columnas:**

- `id`: Primary key
- `client_id`: Referencia a cliente
- `source_id`: Referencia a fuente de datos (nullable)
- `text_field`: Texto analizado
- `sentiment`: Sentimiento detectado
- `sentiment_score`: Score numérico del sentimiento
- `keywords`: Keywords extraídos (JSON)
- `embedding`: Vector de 384 dimensiones (pgvector)
- `language`: Idioma (default: 'es')
- `created_at`: Fecha de creación

**Índices:**

- GIN en `keywords` para búsqueda rápida
- IVFFlat en `embedding` para búsqueda vectorial
- Individual: client_id, source_id, sentiment, created_at

### 3. trend_signals

Señales y tendencias detectadas por sector.

**Columnas:**

- `id`: Primary key
- `sector`: Sector de negocio
- `term`: Término o palabra clave
- `period_start`, `period_end`: Período analizado
- `frequency`: Frecuencia de aparición
- `delta_pct`: Cambio porcentual
- `status`: Estado (ENUM: emergent, stable, declining)
- `metadata`: Información adicional
- `created_at`: Fecha de detección

**Índices:**

- Compuesto: (sector, term), (period_start, period_end)
- Individual: sector, term, status, delta_pct

### 4. clusters

Agrupaciones de clientes basadas en características.

**Columnas:**

- `id`: Primary key
- `client_id`: Referencia a cliente
- `cluster_id`: ID del cluster asignado
- `cluster_name`: Nombre descriptivo (nullable)
- `features_json`: Características usadas para clustering
- `centroid`: Coordenadas del centroide
- `distance_to_centroid`: Distancia al centroide
- `silhouette_score`: Score de calidad del clustering
- `created_at`, `updated_at`: Fechas de registro

**Índices:**

- Compuesto: (client_id, cluster_id)
- GIN en `features_json`
- Individual: client_id, cluster_id

### 5. anomaly_log

Registro de anomalías detectadas en KPIs.

**Columnas:**

- `id`: Primary key
- `client_id`: Referencia a cliente
- `source_id`: Referencia a fuente de datos (nullable)
- `kpi_name`: Nombre del KPI con anomalía
- `detected_at`: Fecha de detección
- `value`: Valor anómalo
- `expected_value`: Valor esperado
- `deviation`: Desviación estándar
- `reason`: Descripción de la anomalía
- `severity`: Severidad (ENUM: low, medium, high, critical)
- `method`: Método de detección usado
- `metadata`: Información adicional

**Índices:**

- Compuesto: (client_id, kpi_name)
- Individual: client_id, source_id, kpi_name, detected_at, severity

## Ejecutar Migraciones

### Migración 003

```bash
# Usando Makefile
make migrate-003

# O directamente
bash scripts/run_migration_003.sh

# O manualmente con Docker
cat migrations/003_create_analytics_tables.sql | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db
```

### Verificar Migración

```bash
# Usando Makefile
make verify-analytics-tables

# O directamente
docker-compose exec postgres psql -U syntegra_user -d syntegra_db -f /scripts/verify_analytics_tables.sql
```

### Rollback

```bash
# Usando Makefile
make rollback-003

# O directamente
bash scripts/rollback_migration_003.sh

# O manualmente
cat migrations/003_rollback_analytics_tables.sql | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db
```

## Requisitos Previos

### Extensión pgvector

La migración 003 requiere la extensión `pgvector` para columnas tipo VECTOR.

**Verificar si está instalada:**

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

**Instalar (ya incluido en docker-compose con imagen ankane/pgvector):**

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Orden de Ejecución

1. Migración 001 (data_sources)
2. Migración 002 (processed_data)
3. Migración 003 (analytics tables) ← **Requiere pgvector**

## Troubleshooting

### Error: "type 'vector' does not exist"

**Solución:**

```bash
docker-compose exec postgres psql -U syntegra_user -d syntegra_db -c "CREATE EXTENSION vector;"
```

### Error: "relation already exists"

La tabla ya fue creada. Para recrear:

```bash
make rollback-003
make migrate-003
```

### Verificar estado de migraciones

```bash
docker-compose exec postgres psql -U syntegra_user -d syntegra_db -c "\dt"
```

## Backup antes de Migración

```bash
# Crear backup
docker-compose exec postgres pg_dump -U syntegra_user syntegra_db > backup_before_migration_003.sql

# Restaurar si es necesario
cat backup_before_migration_003.sql | docker-compose exec -T postgres psql -U syntegra_user -d syntegra_db
```
