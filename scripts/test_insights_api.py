import requests
import json

BASE_URL = "http://localhost:8000"

print('\n' + '='*60)
print('TESTING INSIGHTS API')
print('='*60 + '\n')

# Test 1: Listar insights
print('Test 1: GET /api/v1/insights')
response = requests.get(f"{BASE_URL}/api/v1/insights?limit=10")
print(f'Status: {response.status_code}')
if response.status_code == 200:
    data = response.json()
    print(f'Total insights: {len(data)}')
    if data:
        print(f'Primer insight: Cliente {data[0]["client_id"]}, Riesgo {data[0]["risk_level"]}')
else:
    print(f'Error: {response.text}')

print('\n' + '-'*60 + '\n')

# Test 2: Detalle de cliente
print('Test 2: GET /api/v1/insights/{client_id}')
response = requests.get(f"{BASE_URL}/api/v1/insights/2")
print(f'Status: {response.status_code}')
if response.status_code == 200:
    data = response.json()
    print(f'Cliente: {data["client_id"]}')
    print(f'KPIs: {len(data["kpis"])}')
    print(f'Tendencias: {len(data["trends"])}')
    print(f'Análisis de texto: {len(data["text_analysis"])}')
else:
    print(f'Error: {response.text}')

print('\n' + '-'*60 + '\n')

# Test 3: Estadísticas globales
print('Test 3: GET /api/v1/insights/stats/global')
response = requests.get(f"{BASE_URL}/api/v1/insights/stats/global")
print(f'Status: {response.status_code}')
if response.status_code == 200:
    data = response.json()
    print(f'Total clientes: {data["total_clients"]}')
    print(f'Total insights: {data["total_insights"]}')
    print(f'Total KPIs: {data["total_kpis"]}')
    print(f'Total tendencias: {data["total_trends"]}')
    print(f'Distribución riesgo: {data["risk_distribution"]}')
else:
    print(f'Error: {response.text}')

print('\n' + '-'*60 + '\n')

# Test 4: Búsqueda
print('Test 4: GET /api/v1/insights/search/?q=machine')
response = requests.get(f"{BASE_URL}/api/v1/insights/search/?q=machine")
print(f'Status: {response.status_code}')
if response.status_code == 200:
    data = response.json()
    print(f'Resultados encontrados: {len(data)}')
    for i, result in enumerate(data[:3], 1):
        print(f'  {i}. {result["result_type"]}: {result["title"]}')
else:
    print(f'Error: {response.text}')

print('\n' + '='*60)
print('TESTS COMPLETADOS')
print('='*60 + '\n')
