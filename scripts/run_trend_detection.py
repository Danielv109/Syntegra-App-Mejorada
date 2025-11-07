import sys
sys.path.insert(0, '/app')

from app.data_insights.trend_tasks import detect_recent_trends

print('\n' + '='*60)
print('DETECCION AUTOMATICA DE TENDENCIAS')
print('='*60 + '\n')

result = detect_recent_trends(window_short=1, window_long=7)

print(f'Sectores procesados: {result.get("processed_sectors", 0)}')
print(f'Tendencias detectadas: {result.get("total_trends", 0)}')

print('\nDetalle por sector:')
for sector in result.get('sectors_detail', []):
    print(f'  - {sector.get("sector")}: {sector.get("trends_detected", 0)} tendencias')

print('\n' + '='*60)
print('COMPLETADO')
print('='*60 + '\n')
