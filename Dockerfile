FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Descargar modelo de spaCy
RUN python -m spacy download es_core_news_sm

# Crear directorios necesarios
RUN mkdir -p /app/dataset/raw /app/dataset/gold /app/dataset/processed /app/logs

# Copiar código de la aplicación
COPY ./app /app/app

# Exponer puerto
EXPOSE 8000

# Comando por defecto
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
