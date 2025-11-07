# Data Connectors - SYNTEGRA

## Descripción

El módulo Data Connectors permite configurar y ejecutar ingestas de datos desde fuentes externas de forma automatizada.

## Tabla `data_sources`

### Estructura

```sql
CREATE TABLE data_sources (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    config_json JSONB NOT NULL,
    last_run_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR NOT NULL DEFAULT 'idle',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### Campos

- `id`: Identificador único
- `client_id`: ID del cliente propietario
- `name`: Nombre del conector
- `type`: Tipo de conector (simple_csv, api_rest, etc.)
- `config_json`: Configuración en formato JSON
- `last_run_at`: Última ejecución exitosa
- `status`: Estado actual (idle, processing, error)
- `created_at`: Fecha de creación
- `updated_at`: Última actualización

## Endpoints API

### POST /connectors/

Crear un nuevo conector.

**Request:**

```json
{
  "client_id": 1,
  "name": "Mi Conector CSV",
  "type": "simple_csv",
  "config_json": {
    "type": "simple_csv",
    "url": "http://example.com/data.csv",
    "delimiter": ",",
    "encoding": "utf-8",
    "columns": ["id", "name", "value"]
  }
}
```

**Response:** 201 Created

```json
{
  "id": 1,
  "client_id": 1,
  "name": "Mi Conector CSV",
  "type": "simple_csv",
  "config_json": {...},
  "status": "idle",
  "created_at": "2024-01-15T10:00:00Z"
}
```

### GET /connectors/

Listar conectores del cliente (paginado).

**Query Parameters:**

- `skip`: Offset (default: 0)
- `limit`: Límite (default: 100, max: 1000)

**Response:** 200 OK

```json
[
  {
    "id": 1,
    "name": "Mi Conector CSV",
    "type": "simple_csv",
    "status": "idle",
    ...
  }
]
```

### GET /connectors/{id}

Obtener detalles de un conector.

**Response:** 200 OK

```json
{
  "id": 1,
  "client_id": 1,
  "name": "Mi Conector CSV",
  "type": "simple_csv",
  "config_json": {...},
  "last_run_at": "2024-01-15T12:00:00Z",
  "status": "idle"
}
```

### POST /connectors/{id}/run

Ejecutar ingesta del conector.

**Response:** 202 Accepted

```json
{
  "message": "Ingesta iniciada",
  "task_id": "abc123-task-id",
  "source_id": 1
}
```

## Tipos de Conectores Soportados

### simple_csv

Configuración:

```yaml
required_fields:
  - url
  - delimiter
  - encoding

optional_fields:
  - columns
  - skip_rows
```

### api_rest

Configuración:

```yaml
required_fields:
  - endpoint
  - method

optional_fields:
  - headers
  - auth_type
  - api_key
```

## Ejecutar Tests

### Tests Unitarios

```bash
# Todos los tests de conectores
make test-connectors

# O directamente con pytest
docker-compose exec api pytest tests/test_connectors.py -v
```

### Test de Ingesta End-to-End

```bash
# Usando el script de shell
make test-ingest

# O directamente
bash scripts/test_ingest_connector.sh
```

## Flujo de Trabajo

1. **Crear Conector**: POST /connectors/ con configuración válida
2. **Validar**: Sistema valida config_json contra plantilla del tipo
3. **Ejecutar**: POST /connectors/{id}/run encola tarea Celery
4. **Procesar**: Worker ejecuta ingesta (actualmente simulada)
5. **Resultado**: Archivo CSV generado en dataset/raw/{source_id}/
6. **Historial**: Registro creado en etl_history

## Archivos Generados

Los archivos se guardan en:
