"""
Script de prueba para el Trend Engine
"""
import sys
sys.path.insert(0, '/app')

from app.data_insights.trend_tasks import detect_recent_trends
from app.db.session import SessionLocal
from sqlalchemy import text

def test_trend_engine():
    print('\n' + '='*60)
    print('TESTING TREND ENGINE')
    print('='*60 + '\n')
    
    # Test 1: Detectar tendencias
    print('Test 1: Detectar tendencias recientes...')
    result = detect_recent_trends(window_short=7, window_long=30)
    
    print(f'\nResultado:')
    print(f'  Sectores procesados: {result.get("processed_sectors", 0)}')
    print(f'  Tendencias detectadas: {result.get("total_trends", 0)}')
    
    if result.get("sectors_detail"):
        print(f'\n  Detalle por sector:')
        for sector_info in result["sectors_detail"]:
            print(f'    - {sector_info.get("sector")}: {sector_info.get("trends_detected", 0)} tendencias')
    
    # Test 2: Verificar datos en trend_signals
    print('\n' + '-'*60)
    print('Test 2: Verificar datos guardados en trend_signals...')
    
    db = SessionLocal()
    
    query = text("""
        SELECT
            sector,
            term,
            frequency,
            ROUND(delta_pct::numeric, 2) as delta,
            status,
            period_start
        FROM trend_signals
        ORDER BY period_start DESC, ABS(delta_pct) DESC
        LIMIT 10
    """)
    
    rows = db.execute(query).fetchall()
    
    if rows:
        print(f'\nEncontradas {len(rows)} tendencias en la base de datos:')
        for row in rows:
            print(f'  - {row[0]}: {row[1]} (freq={row[2]}, delta={row[3]}, status={row[4]})')
    else:
        print('\nNo se encontraron tendencias en la base de datos')
    
    db.close()
    
    print('\n' + '='*60)
    print('TESTS COMPLETADOS')
    print('='*60 + '\n')

if __name__ == "__main__":
    test_trend_engine()
