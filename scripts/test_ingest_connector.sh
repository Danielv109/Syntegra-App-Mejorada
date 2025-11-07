#!/bin/bash

# Script para probar ingesta de conector

set -e

API_URL="http://localhost:8000"
TOKEN=""

echo "=========================================="
echo "Test de Ingesta de Conector"
echo "=========================================="

# Paso 1: Login
echo ""
echo "1. Autenticando..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "Admin123!"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Error: No se pudo obtener token"
  exit 1
fi

echo "✅ Token obtenido"

# Paso 2: Crear cliente de prueba (si no existe)
echo ""
echo "2. Verificando cliente de prueba..."
CLIENT_ID=1  # Assuming first client exists

# Paso 3: Crear conector
echo ""
echo "3. Creando conector de prueba..."
CONNECTOR_RESPONSE=$(curl -s -X POST "$API_URL/connectors/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": '$CLIENT_ID',
    "name": "Test CSV Connector",
    "type": "simple_csv",
    "config_json": {
      "type": "simple_csv",
      "url": "http://example.com/data.csv",
      "delimiter": ",",
      "encoding": "utf-8",
      "columns": ["id", "name", "value", "date"]
    }
  }')

CONNECTOR_ID=$(echo $CONNECTOR_RESPONSE | jq -r '.id')

if [ "$CONNECTOR_ID" == "null" ] || [ -z "$CONNECTOR_ID" ]; then
  echo "❌ Error: No se pudo crear conector"
  echo $CONNECTOR_RESPONSE | jq
  exit 1
fi

echo "✅ Conector creado: ID $CONNECTOR_ID"

# Paso 4: Ejecutar conector
echo ""
echo "4. Ejecutando ingesta..."
RUN_RESPONSE=$(curl -s -X POST "$API_URL/connectors/$CONNECTOR_ID/run" \
  -H "Authorization: Bearer $TOKEN")

TASK_ID=$(echo $RUN_RESPONSE | jq -r '.task_id')

if [ "$TASK_ID" == "null" ] || [ -z "$TASK_ID" ]; then
  echo "❌ Error: No se pudo encolar tarea"
  echo $RUN_RESPONSE | jq
  exit 1
fi

echo "✅ Tarea encolada: $TASK_ID"

# Paso 5: Esperar a que termine (polling)
echo ""
echo "5. Esperando finalización de tarea..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  sleep 2
  ATTEMPT=$((ATTEMPT+1))
  
  # Verificar si el archivo fue creado
  if [ -d "dataset/raw/$CONNECTOR_ID" ]; then
    FILE_COUNT=$(ls -1 dataset/raw/$CONNECTOR_ID/*.csv 2>/dev/null | wc -l)
    if [ $FILE_COUNT -gt 0 ]; then
      echo "✅ Archivo creado exitosamente"
      
      # Mostrar contenido
      LATEST_FILE=$(ls -t dataset/raw/$CONNECTOR_ID/*.csv | head -1)
      echo ""
      echo "6. Contenido del archivo generado:"
      echo "-----------------------------------"
      cat "$LATEST_FILE"
      echo "-----------------------------------"
      
      echo ""
      echo "=========================================="
      echo "✅ TEST COMPLETADO EXITOSAMENTE"
      echo "=========================================="
      exit 0
    fi
  fi
  
  echo "  Intento $ATTEMPT/$MAX_ATTEMPTS..."
done

echo "❌ Timeout: El archivo no se generó en el tiempo esperado"
exit 1
