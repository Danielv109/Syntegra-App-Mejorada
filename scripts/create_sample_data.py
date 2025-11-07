"""
Script para crear datos de ejemplo
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
from pathlib import Path
import random
from datetime import datetime, timedelta

def create_sample_datasets():
    """Crear datasets de ejemplo"""
    
    # Dataset 1: Ventas
    ventas_data = []
    for i in range(200):
        fecha = datetime.now() - timedelta(days=random.randint(0, 90))
        ventas_data.append({
            "fecha": fecha.strftime("%Y-%m-%d"),
            "producto": random.choice(["Producto A", "Producto B", "Producto C", "Producto D"]),
            "cantidad": random.randint(1, 50),
            "precio_unitario": round(random.uniform(10, 500), 2),
            "total": 0,  # Se calculará
            "region": random.choice(["Norte", "Sur", "Este", "Oeste"]),
        })
    
    df_ventas = pd.DataFrame(ventas_data)
    df_ventas["total"] = df_ventas["cantidad"] * df_ventas["precio_unitario"]
    
    # Dataset 2: Reseñas
    reseñas_positivas = [
        "Excelente producto, muy recomendado",
        "Superó mis expectativas, calidad increíble",
        "Muy buena compra, llegó rápido",
        "Producto de alta calidad, vale la pena",
        "Fantástico, lo volvería a comprar",
    ]
    
    reseñas_negativas = [
        "Producto defectuoso, no sirve",
        "Mala calidad, no lo recomiendo",
        "Decepcionante, esperaba más",
        "No vale el precio, muy caro",
        "Llegó dañado, mal servicio",
    ]
    
    reseñas_data = []
    for i in range(150):
        es_positiva = random.random() > 0.3
        reseñas_data.append({
            "fecha": (datetime.now() - timedelta(days=random.randint(0, 60))).strftime("%Y-%m-%d"),
            "producto": random.choice(["Producto A", "Producto B", "Producto C"]),
            "calificacion": random.randint(4, 5) if es_positiva else random.randint(1, 3),
            "comentario": random.choice(reseñas_positivas if es_positiva else reseñas_negativas),
            "usuario": f"Usuario{random.randint(1, 100)}",
        })
    
    df_reseñas = pd.DataFrame(reseñas_data)
    
    # Guardar archivos
    raw_dir = Path("dataset/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    df_ventas.to_csv(raw_dir / "ventas_ejemplo.csv", index=False)
    df_reseñas.to_csv(raw_dir / "reseñas_ejemplo.csv", index=False)
    
    print("✅ Datasets de ejemplo creados:")
    print(f"  - ventas_ejemplo.csv ({len(df_ventas)} registros)")
    print(f"  - reseñas_ejemplo.csv ({len(df_reseñas)} registros)")


if __name__ == "__main__":
    create_sample_datasets()
