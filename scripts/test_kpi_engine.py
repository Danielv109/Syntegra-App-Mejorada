"""
Script de prueba para el KPI Engine
"""
import sys
sys.path.insert(0, '/app')

from app.data_insights.insights_tasks import compute_kpis_for_recent
from app.db.session import SessionLocal
from sqlalchemy import text

print('\n' + '='*60)
print('TESTING KPI ENGINE')
print('='*60 + '\n')

print('Test 1: Calcular KPIs para ultimos 7 dias...')
result = compute_kpis_for_recent(hours_back=168, days_period=30)

print('\nResultado:')
print(f'  Clientes procesados: {result.get("processed_clients", 0)}')
print(f'  Clientes exitosos: {result.get("successful_clients", 0)}')
print(f'  KPIs totales: {result.get("total_kpis", 0)}')

print('\n' + '-'*60)
print('Test 2: Verificar datos guardados en kpi_summary...')

db = SessionLocal()

query = text("""
    SELECT
        client_id,
        kpi_name,
        ROUND(kpi_value::numeric, 2) as value,
        calculated_at
    FROM kpi_summary
    ORDER BY calculated_at DESC
    LIMIT 10
""")

rows = db.execute(query).fetchall()

if rows:
    print(f'\nEncontrados {len(rows)} KPIs en la base de datos:')
    for row in rows:
        print(f'  - Cliente {row[0]}: {row[1]} = {row[2]}')
else:
    print('\nNo se encontraron KPIs en la base de datos')

db.close()

print('\n' + '='*60)
print('TESTS COMPLETADOS')
print('='*60 + '\n')
