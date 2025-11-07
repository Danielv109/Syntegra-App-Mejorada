import sys
sys.path.insert(0, '/app')

from app.data_insights.insight_tasks import generate_recent_insights
from app.db.session import SessionLocal
from sqlalchemy import text

print('\n' + '='*60)
print('TESTING INSIGHT GENERATOR')
print('='*60 + '\n')

# Test 1: Generar insights
print('Test 1: Generar insights para clientes activos...')
result = generate_recent_insights(days_back=7, hours_activity=168)

print(f'\nResultado:')
print(f'  Clientes procesados: {result.get("processed_clients", 0)}')
print(f'  Insights generados: {result.get("insights_generated", 0)}')

if result.get('results'):
    print(f'\n  Detalle:')
    for r in result['results'][:5]:
        if r.get('status') == 'success':
            print(f'    - Cliente {r["client_id"]}: {r["findings_count"]} hallazgos, '
                  f'riesgo={r["risk_level"]}, oportunidad={r["opportunity_level"]}')

# Test 2: Verificar en BD
print('\n' + '-'*60)
print('Test 2: Verificar datos en ai_insights...')

db = SessionLocal()

query = text("""
    SELECT 
        client_id,
        substring(summary_text, 1, 50) as summary,
        risk_level,
        opportunity_level,
        jsonb_array_length(key_findings) as findings_count,
        generated_at
    FROM ai_insights
    ORDER BY generated_at DESC
    LIMIT 10
""")

rows = db.execute(query).fetchall()

if rows:
    print(f'\nEncontrados {len(rows)} insights en la base de datos:')
    for row in rows:
        print(f'  - Cliente {row[0]}: {row[2]}/{row[3]}, {row[4]} hallazgos')
else:
    print('\nNo se encontraron insights en la base de datos')

db.close()

print('\n' + '='*60)
print('TESTS COMPLETADOS')
print('='*60 + '\n')
