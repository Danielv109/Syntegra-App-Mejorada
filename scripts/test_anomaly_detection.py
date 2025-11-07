"""
Script para probar detección de anomalías con datos de ejemplo
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from app.services.anomaly_detection import anomaly_detector

def test_anomaly_detection():
    print("🔍 Probando detección de anomalías...\n")
    
    # Crear dataset de ejemplo con anomalías intencionadas
    np.random.seed(42)
    
    # Datos normales
    normal_data = {
        'ventas': np.random.normal(1000, 200, 200),
        'visitas': np.random.normal(500, 100, 200),
        'conversion': np.random.normal(0.05, 0.01, 200),
    }
    
    df = pd.DataFrame(normal_data)
    
    # Inyectar anomalías
    anomaly_indices = [10, 25, 50, 75, 100, 150]
    df.loc[anomaly_indices, 'ventas'] = [5000, 8000, 100, 50, 10000, 7500]
    df.loc[anomaly_indices, 'visitas'] = [2000, 3000, 50, 10, 5000, 4000]
    df.loc[anomaly_indices, 'conversion'] = [0.15, 0.20, 0.005, 0.001, 0.25, 0.18]
    
    print(f"Dataset creado: {len(df)} registros")
    print(f"Anomalías inyectadas en índices: {anomaly_indices}\n")
    
    # Método 1: IsolationForest
    print("=" * 60)
    print("MÉTODO 1: ISOLATION FOREST")
    print("=" * 60)
    
    try:
        result = anomaly_detector.detect_anomalies_isolation_forest(
            df=df,
            columns=['ventas', 'visitas', 'conversion'],
            contamination=0.05,
        )
        
        print(f"✅ Total registros: {result['total_records']}")
        print(f"✅ Anomalías detectadas: {result['total_anomalies']} ({result['anomaly_percentage']}%)")
        print(f"✅ Distribución de severidad:")
        for severity, count in result['severity_distribution'].items():
            print(f"   - {severity}: {count}")
        
        print(f"\n📊 Top 5 anomalías más severas:")
        for i, anomaly in enumerate(result['anomaly_details'][:5], 1):
            print(f"   {i}. Índice {anomaly['index']}: {anomaly['values']}")
            print(f"      Score: {anomaly['anomaly_score']:.4f} | Severidad: {anomaly['severity']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Método 2: Ensemble
    print("\n" + "=" * 60)
    print("MÉTODO 2: ENSEMBLE (IsolationForest + EllipticEnvelope + LOF)")
    print("=" * 60)
    
    try:
        result = anomaly_detector.detect_anomalies_ensemble(
            df=df,
            columns=['ventas', 'visitas', 'conversion'],
            contamination=0.05,
        )
        
        print(f"✅ Métodos combinados: {', '.join(result['methods_used'])}")
        
        iso_result = result['isolation_forest_results']
        print(f"\n📈 IsolationForest: {iso_result['total_anomalies']} anomalías")
        
        if result.get('elliptic_envelope_results'):
            elliptic_result = result['elliptic_envelope_results']
            print(f"📈 EllipticEnvelope: {elliptic_result['total_anomalies']} anomalías")
        
        if result.get('lof_results'):
            lof_result = result['lof_results']
            print(f"📈 LOF: {lof_result['total_anomalies']} anomalías")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Pruebas completadas")
    print("=" * 60)


if __name__ == "__main__":
    test_anomaly_detection()
