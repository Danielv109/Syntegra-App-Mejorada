# Operations Guide - SYNTEGRA

## Nuevas Rutas (v1.1.0)

### Data Connectors

- `POST /connectors/` - Crear conector
- `GET /connectors/` - Listar conectores
- `GET /connectors/{id}` - Obtener conector
- `POST /connectors/{id}/run` - Ejecutar ingesta

## Scripts de Mantenimiento

### Test de Conectores

```bash
# Tests unitarios
make test-connectors

# Test end-to-end
make test-ingest
```

### Ejecución Manual de Ingesta

```bash
# Desde la API
curl -X POST http://localhost:8000/connectors/1/run \
  -H "Authorization: Bearer <token>"

# Verificar resultado
ls -la dataset/raw/1/
```

## Monitoreo

### Ver Tareas de Conectores

```bash
# Logs del worker
docker-compose logs -f worker | grep "ingest_source"

# Estado de conectores en DB
docker-compose exec postgres psql -U syntegra_user -d syntegra_db \
  -c "SELECT id, name, status, last_run_at FROM data_sources;"
```

### Historial ETL

```bash
docker-compose exec postgres psql -U syntegra_user -d syntegra_db \
  -c "SELECT * FROM etl_history ORDER BY started_at DESC LIMIT 10;"
```

## Troubleshooting

### Conector atascado en "processing"

```sql
-- Resetear manualmente
UPDATE data_sources SET status = 'idle' WHERE id = <connector_id>;
```

### Limpiar archivos de prueba

```bash
rm -rf dataset/raw/*/
```
