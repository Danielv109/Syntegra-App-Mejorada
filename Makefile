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

init-admin:
	docker-compose exec api python scripts/init_admin.py

sample-data:
	docker-compose exec api python scripts/create_sample_data.py
