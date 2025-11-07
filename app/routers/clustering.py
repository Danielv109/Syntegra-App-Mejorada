from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np

from app.database import get_db, engine
from app.models.user import User
from app.models.client import Client
from app.models.analytics import Cluster
from app.services.auth import get_current_active_user
from app.logger import get_logger

router = APIRouter(prefix="/clustering", tags=["Clustering"])
logger = get_logger()


@router.post("/clients/similar")
async def find_similar_clients(
    features: List[str],
    n_clusters: int = 5,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Agrupar clientes similares usando clustering"""
    
    if not current_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no tiene cliente asignado"
        )
    
    try:
        # Obtener datos de todos los clientes (simulación)
        # En producción, esto vendría de tablas consolidadas
        clients = db.query(Client).filter(Client.is_active == True).all()
        
        if len(clients) < n_clusters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No hay suficientes clientes para {n_clusters} clusters"
            )
        
        # Preparar datos para clustering (ejemplo simplificado)
        data = []
        client_ids = []
        
        for client in clients:
            # Aquí deberías obtener métricas reales del cliente
            # Por ahora, generamos datos de ejemplo
            client_data = {
                "ventas_promedio": np.random.uniform(1000, 10000),
                "satisfaccion": np.random.uniform(0, 10),
                "retencion": np.random.uniform(0, 1),
            }
            data.append(list(client_data.values()))
            client_ids.append(client.id)
        
        # Crear DataFrame
        df = pd.DataFrame(data, columns=["ventas_promedio", "satisfaccion", "retencion"])
        
        # Normalizar datos
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(df)
        
        # Aplicar KMeans
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(X_scaled)
        
        # Guardar resultados
        for i, client_id in enumerate(client_ids):
            cluster = Cluster(
                client_id=client_id,
                cluster_id=int(cluster_labels[i]),
                features_used=features,
                centroid=kmeans.cluster_centers_[cluster_labels[i]].tolist(),
                size=int(np.sum(cluster_labels == cluster_labels[i])),
            )
            
            # Actualizar si ya existe
            existing = db.query(Cluster).filter(
                Cluster.client_id == client_id
            ).first()
            
            if existing:
                existing.cluster_id = cluster.cluster_id
                existing.features_used = cluster.features_used
                existing.centroid = cluster.centroid
                existing.size = cluster.size
            else:
                db.add(cluster)
        
        db.commit()
        
        # Encontrar clientes similares al cliente actual
        current_cluster = cluster_labels[client_ids.index(current_user.client_id)]
        similar_indices = np.where(cluster_labels == current_cluster)[0]
        similar_client_ids = [client_ids[i] for i in similar_indices if client_ids[i] != current_user.client_id]
        
        similar_clients = db.query(Client).filter(Client.id.in_(similar_client_ids)).all()
        
        logger.info(f"Clustering completado. Cliente {current_user.client_id} en cluster {current_cluster}")
        
        return {
            "message": "Clustering completado",
            "current_cluster": int(current_cluster),
            "total_clusters": n_clusters,
            "similar_clients": [
                {
                    "id": c.id,
                    "name": c.name,
                    "industry": c.industry,
                }
                for c in similar_clients
            ]
        }
        
    except Exception as e:
        logger.error(f"Error en clustering: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en clustering: {str(e)}"
        )


@router.get("/clients/{client_id}/similar")
async def get_similar_clients(
    client_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Obtener clientes similares basados en clustering previo"""
    
    # Verificar que el cluster existe
    cluster_info = db.query(Cluster).filter(Cluster.client_id == client_id).first()
    
    if not cluster_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró información de clustering para este cliente"
        )
    
    # Buscar otros clientes en el mismo cluster
    similar_clusters = db.query(Cluster).filter(
        Cluster.cluster_id == cluster_info.cluster_id,
        Cluster.client_id != client_id,
    ).all()
    
    similar_clients = []
    for sc in similar_clusters:
        client = db.query(Client).filter(Client.id == sc.client_id).first()
        if client:
            similar_clients.append({
                "id": client.id,
                "name": client.name,
                "industry": client.industry,
            })
    
    return {
        "cluster_id": cluster_info.cluster_id,
        "cluster_size": cluster_info.size,
        "similar_clients": similar_clients,
    }
