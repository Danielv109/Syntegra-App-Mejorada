# SYNTEGRA - Plataforma de Inteligencia de Clientes

## 🚀 Descripción

SYNTEGRA es una plataforma completa de inteligencia de datos empresariales que funciona completamente **offline** o en entornos locales, sin depender de servicios externos.

## ✨ Características Principales

- **ETL Automatizado**: Ingesta y limpieza de datos estructurados (CSV, Excel, JSON)
- **Data Connectors**: Sistema de conectores para fuentes externas
- **Data Processing**: Limpieza y normalización automática de datos
- **Análisis de Texto con IA Local**: Análisis de sentimiento y extracción de keywords usando Ollama
- **Detección de Tendencias**: Identificación automática de patrones emergentes
- **Detección de Anomalías**: Usando IsolationForest de scikit-learn
- **Clustering de Clientes**: Agrupación inteligente de empresas similares
- **Generación de Reportes**: Informes PDF automáticos con métricas clave
- **Gold Dataset**: Sistema de aprendizaje continuo con correcciones humanas
- **Multi-tenant**: Soporte para múltiples clientes con aislamiento de datos
- **Procesamiento Asíncrono**: Workers con Celery para tareas pesadas

## 📊 Módulos Principales

### 1. Data Connectors

- Configuración de fuentes de datos externas
- Validación basada en templates YAML
- Ejecución asíncrona de ingestas
- Historial completo de operaciones

### 2. Data Processing

- Limpieza automática de texto (HTML, emojis, caracteres especiales)
- Normalización de fechas (múltiples formatos)
- Normalizadores específicos por tipo (restaurant, retail, service)
- Almacenamiento en tabla `processed_data`

### 3. Text Analysis

- Análisis de sentimiento con Ollama (IA local)
- Extracción de keywords con spaCy
- Generación de embeddings
- Detección de entidades

### 4. Anomaly Detection

- IsolationForest (método principal)
- EllipticEnvelope (multivariado)
- LocalOutlierFactor (densidad local)
- Ensemble de métodos

## 🛠️ Stack Tecnológico

- **Backend**: Python 3.11 + FastAPI
- **Base de Datos**: PostgreSQL + pgvector
- **Cache/Queue**: Redis
- **IA Local**: Ollama (phi3:mini, mistral, llama3)
- **NLP**: spaCy + sentence-transformers
- **ML**: scikit-learn + pandas
- **Async**: Celery
- **Reports**: ReportLab
- **Container**: Docker + Docker Compose

## 📋 Requisitos

- Docker y Docker Compose
- Python 3.11+
- Ollama instalado localmente
- RAM mínima: 8 GB
- Espacio en disco: 20 GB

## 🔧 Instalación

### 1. Clonar repositorio

```bash
git clone <repository-url>
cd Syntegra-App-Mejorada
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus valores
```

### 3. Instalar Ollama (si no está instalado)

```bash
# Linux/Mac
curl -fsSL https://ollama.com/install.sh | sh

# Windows: Descargar desde https://ollama.com/download
```

### 4. Descargar modelo de Ollama

```bash
ollama pull phi3:mini
```

### 5. Iniciar servicios con Docker

```bash
docker-compose up -d
```

### 6. Crear usuario administrador

```bash
docker-compose exec api python scripts/init_admin.py
```

### 7. (Opcional) Crear datos de ejemplo

```bash
docker-compose exec api python scripts/create_sample_data.py
```

## 📚 Documentación API

Una vez iniciada la aplicación, visita:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Documentación Detallada

- [Data Connectors](DOCS/CONNECTORS.md)
- [Data Processing](DOCS/DATA_PROCESSING.md)

## 🔐 Autenticación

### Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "Admin123!"
  }'
```

### Usar Token

```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer <your-token>"
```

## 📊 Flujo de Trabajo Básico

### 1. Crear Cliente

```bash
curl -X POST http://localhost:8000/auth/clients \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Empresa Demo",
    "industry": "Tecnología"
  }'
```

### 2. Subir Dataset

```bash
curl -X POST http://localhost:8000/datasets/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@ventas.csv" \
  -F "name=Ventas Q1" \
  -F "description=Datos de ventas primer trimestre"
```

### 3. Analizar Texto

```bash
curl -X POST http://localhost:8000/analysis/datasets/1/analyze-text \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "text_columns": ["comentarios", "descripcion"]
  }'
```

### 4. Generar Reporte

```bash
curl -X POST http://localhost:8000/reports/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "weights": {
      "satisfaccion": 1.5,
      "ventas": 1.2,
      "retencion": 1.0
    }
  }'
```

## 🧪 Testing

```bash
# Todos los tests
pytest

# Tests por módulo
make test-connectors
make test-processing

# Con coverage
make test-processing-coverage

# Demos interactivos
make demo-processing
```

## 📁 Estructura del Proyecto

```bash
app/
├── api.py               # Archivo principal de la API
├── models.py            # Modelos de datos y esquemas Pydantic
├── services.py         # Lógica de negocio y servicios
├── tasks.py             # Tareas de Celery
├── connectors/          # Módulo de Data Connectors
│   ├── __init__.py
│   ├── models.py        # Modelos específicos de conectores
│   ├── schemas.py       # Esquemas Pydantic para validación
│   └── tasks.py         # Tareas de ingesta y conexión
├── processing/          # Módulo de Data Processing
│   ├── __init__.py
│   ├── models.py        # Modelos para procesamiento de datos
│   ├── schemas.py       # Esquemas Pydantic para validación
│   └── tasks.py         # Tareas de procesamiento y normalización
├── analysis/            # Módulo de Análisis de Datos
│   ├── __init__.py
│   ├── models.py        # Modelos para análisis de datos
│   ├── schemas.py       # Esquemas Pydantic para validación
│   └── tasks.py         # Tareas de análisis y generación de reportes
├── db.py                # Configuración de la base de datos y modelos SQLAlchemy
├── main.py              # Punto de entrada de la aplicación
└── settings.py          # Configuración general de la aplicación
```
