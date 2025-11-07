# Data Processing - SYNTEGRA

## Descripción

El módulo Data Processing se encarga de limpiar, normalizar y transformar datos crudos provenientes de diferentes fuentes externas antes de almacenarlos en la base de datos.

## Tabla `processed_data`

### Estructura

```sql
CREATE TABLE processed_data (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Campos

- `id`: Identificador único
- `source_type`: Tipo de fuente (restaurant, retail, service)
- `data`: Datos normalizados en formato JSON
- `created_at`: Fecha de procesamiento

### Índices

- `idx_processed_data_source_type`: Índice en source_type
- `idx_processed_data_created_at`: Índice en created_at

## Funciones Principales

### clean_text(text: str) -> str

Limpia texto eliminando HTML, emojis, saltos de línea y caracteres especiales.

**Ejemplo:**

```python
from app.data_processing.utils.clean_text import clean_text

text = "<p>Hola <b>mundo</b> 😊</p>"
cleaned = clean_text(text)
# Resultado: "Hola mundo"
```

**Características:**

- Elimina tags HTML y entidades
- Remueve emojis y caracteres especiales
- Normaliza espacios y saltos de línea
- Preserva puntuación básica y acentos

### standardize_date(date_str: str) -> datetime

Convierte fechas en distintos formatos a objetos datetime.

**Ejemplo:**

```python
from app.data_processing.utils.standardize_dates import standardize_date

date1 = standardize_date("2024-01-15")
date2 = standardize_date("15/01/2024")
date3 = standardize_date("January 15, 2024")
# Todos devuelven: datetime(2024, 1, 15)
```

**Formatos soportados:**

- ISO 8601: `2024-01-15`, `2024-01-15T10:30:00`
- DD/MM/YYYY: `15/01/2024`
- MM/DD/YYYY: `01/15/2024`
- Con nombre de mes: `15 January 2024`, `January 15, 2024`

### normalize_data(data: dict, source_type: str) -> dict

Mapea campos a formato estándar según tipo de fuente.

**Ejemplo:**

```python
from app.data_processing.normalizers import normalize_data

raw_data = {
    'name': 'Restaurante Demo',
    'phone': '555-1234',
    'rating': 4.5
}

normalized = normalize_data(raw_data, 'restaurant')
```

**Tipos soportados:**

- `restaurant`: Restaurantes y establecimientos de comida
- `retail`: Tiendas y comercios
- `service`: Servicios (peluquerías, talleres, etc.)

### process_incoming_data(raw_data: list, source_type: str, db: Session)

Procesa batch de datos: limpia, normaliza y guarda en base de datos.

**Ejemplo:**

```python
from app.data_processing.processor import process_incoming_data
from app.database import SessionLocal

raw_data = [
    {'name': 'Restaurant 1', 'rating': 4.0},
    {'name': 'Restaurant 2', 'rating': 4.5},
]

db = SessionLocal()
result = process_incoming_data(raw_data, 'restaurant', db)

print(f"Procesados: {result['processed_successfully']}")
print(f"Fallidos: {result['failed']}")
```

**Retorna:**

```python
{
    'total_records': 2,
    'processed_successfully': 2,
    'failed': 0,
    'errors': []
}
```

## Normalizadores por Tipo

### Restaurant Normalizer

Campos extraídos:

- name, address, phone, email
- rating, reviews_count, price_range
- cuisine_type, opening_hours, services
- location (lat/lng, city, state)
- reviews, menu_items
- metadata adicional

### Retail Normalizer

Campos extraídos:

- name, address, phone, email
- rating, reviews_count, category
- products, opening_hours, payment_methods
- delivery_available
- location, reviews
- metadata adicional

### Service Normalizer

Campos extraídos:

- name, address, phone, email
- rating, reviews_count, service_type
- services_offered, pricing, opening_hours
- booking_available
- location, staff, reviews
- metadata adicional

## Integración con Data Connectors

El módulo se integra automáticamente con Data Connectors:

1. **Data Connector** ejecuta ingesta y genera archivo CSV
2. **Data Processing** lee los datos del CSV
3. Aplica limpieza y normalización
4. Guarda en tabla `processed_data`

**Flujo automático:**
