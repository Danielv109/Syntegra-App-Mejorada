# Changelog

## [1.2.0] - 2024-01-16

### Added

- **Data Processing Module**: Sistema completo de procesamiento de datos
  - Tabla `processed_data` para almacenar datos normalizados
  - Utilidades de limpieza: `clean_text()`, `clean_text_advanced()`
  - Utilidades de fechas: `standardize_date()`, `parse_relative_date()`
  - Normalizadores específicos: restaurant, retail, service
  - Función principal: `process_incoming_data()`
  - Integración automática con data_connectors
  - Tests unitarios completos
  - Documentación en DOCS/DATA_PROCESSING.md
  - Script de prueba: `scripts/test_data_processing.py`

### Changed

- Actualizado `app/workers/connector_tasks.py` para integrar procesamiento automático
- Agregado modelo `ProcessedData` en `app/models/`

## [1.1.0] - 2024-01-15

### Added

- **Data Connectors Module**: Sistema completo de conectores de datos externos
  - Tabla `data_sources` para almacenar configuración de conectores
  - Endpoints CRUD para gestión de conectores (`/connectors/`)
  - Tarea Celery `ingest_source` para ejecución de ingestas
  - Validación de configuración basada en templates YAML
  - Soporte para tipos: `simple_csv` y `api_rest`
  - Generación de datos simulados para testing
  - Scripts de prueba end-to-end
  - Tests unitarios completos
  - Documentación en DOCS/CONNECTORS.md

### Changed

- Actualizado `app/main.py` para incluir router de conectores
- Actualizado `app/workers/celery_app.py` para incluir tareas de conectores
- Agregados comandos `test-connectors` y `test-ingest` al Makefile

## [1.0.0] - 2024-01-10

### Added

- Implementación inicial de SYNTEGRA
- Autenticación JWT y multi-tenant
- ETL Engine con Great Expectations
- Análisis de texto con Ollama
- Detección de anomalías con IsolationForest
- Generación de reportes PDF
- Clustering de clientes
- Gold Dataset para correcciones humanas
