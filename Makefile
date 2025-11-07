.PHONY: help build up down logs clean test init-db init-admin sample-data

help:
	@echo "Comandos disponibles:"
	@echo "  make build        - Construir imágenes Docker"
	@echo "  make up           - Iniciar servicios"
	@echo "  make down         - Detener servicios"
	@echo "  make logs         - Ver logs"
	@echo "  make clean        - Limpiar contenedores y volúmenes"
	@echo "  make test         - Ejecutar tests"
	@echo "  make init-admin   - Crear usuario admin"
	@echo "  make sample-data  - Crear datos de ejemplo"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "✅ Servicios iniciados"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"

down:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	rm -rf logs/*.log
	rm -rf reports/*.pdf

test:
	docker-compose exec api pytest

test-connectors:
	docker-compose exec api pytest tests/test_connectors.py -v

test-ingest:
	bash scripts/test_ingest_connector.sh

init-admin:
	docker-compose exec api python scripts/init_admin.py

sample-data:
	docker-compose exec api python scripts/create_sample_data.py

test-processing:
	docker-compose exec api pytest tests/test_data_processing.py -v

test-processing-coverage:
	docker-compose exec api pytest tests/test_data_processing.py --cov=app.data_processing --cov-report=html

demo-processing:
	docker-compose exec api python scripts/test_data_processing.py

# Migrations
migrate-003:
	bash scripts/run_migration_003.sh

rollback-003:
	bash scripts/rollback_migration_003.sh

verify-analytics-tables:
	docker-compose exec postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -f /scripts/verify_analytics_tables.sql
