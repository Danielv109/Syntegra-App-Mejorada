import logging
import subprocess
import json
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache del modelo local
_local_model: Optional[SentenceTransformer] = None


def _get_local_model() -> SentenceTransformer:
    """Obtener modelo Sentence Transformers cacheado"""
    global _local_model
    if _local_model is None:
        logger.info("Cargando modelo Sentence Transformers: paraphrase-MiniLM-L6-v2")
        _local_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
    return _local_model


def _try_ollama_embedding(text: str, model: str = "nomic-embed-text") -> Optional[List[float]]:
    """
    Intentar obtener embedding usando Ollama local
    
    Args:
        text: Texto a embedar
        model: Nombre del modelo Ollama
        
    Returns:
        Vector de embedding o None si falla
    """
    try:
        # Intentar llamar a Ollama via subprocess
        cmd = ["ollama", "run", model, "--embed", text]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Parsear salida JSON
            embedding = json.loads(result.stdout)
            if isinstance(embedding, list) and len(embedding) > 0:
                logger.debug(f"Embedding obtenido via Ollama: {len(embedding)} dims")
                return embedding
                
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Ollama no disponible o error: {e}")
    
    return None


def _normalize_vector(vector: List[float], target_dim: int) -> List[float]:
    """
    Normalizar vector a dimensión objetivo
    
    Args:
        vector: Vector original
        target_dim: Dimensión objetivo (de config)
        
    Returns:
        Vector normalizado
    """
    vec_array = np.array(vector)
    current_dim = len(vec_array)
    
    if current_dim == target_dim:
        return vector
    
    if current_dim > target_dim:
        # Truncar usando PCA simple (promedio de grupos)
        logger.debug(f"Reduciendo dimensión de {current_dim} a {target_dim}")
        step = current_dim / target_dim
        normalized = [
            float(np.mean(vec_array[int(i*step):int((i+1)*step)])) 
            for i in range(target_dim)
        ]
    else:
        # Padding con zeros
        logger.debug(f"Expandiendo dimensión de {current_dim} a {target_dim}")
        normalized = vector + [0.0] * (target_dim - current_dim)
    
    return normalized


def get_embedding(text: str) -> List[float]:
    """
    Obtener embedding para un texto
    
    Estrategia:
    1. Intentar Ollama local
    2. Fallback a Sentence Transformers
    3. Normalizar a dimensión configurada
    
    Args:
        text: Texto a embedar
        
    Returns:
        Vector de embedding normalizado
    """
    if not text or not text.strip():
        logger.warning("Texto vacío, retornando vector de zeros")
        return [0.0] * settings.PGVECTOR_DIM
    
    # Intentar Ollama primero
    embedding = _try_ollama_embedding(text)
    
    # Fallback a Sentence Transformers
    if embedding is None:
        logger.debug("Usando Sentence Transformers como fallback")
        model = _get_local_model()
        embedding = model.encode(text).tolist()
    
    # Normalizar a dimensión configurada
    normalized = _normalize_vector(embedding, settings.PGVECTOR_DIM)
    
    # Validar
    if len(normalized) != settings.PGVECTOR_DIM:
        raise ValueError(
            f"Vector dimension mismatch: {len(normalized)} != {settings.PGVECTOR_DIM}"
        )
    
    return normalized


def bulk_embed(texts: List[str]) -> List[List[float]]:
    """
    Embedar múltiples textos en batch
    
    Args:
        texts: Lista de textos
        
    Returns:
        Lista de vectores de embedding
    """
    if not texts:
        return []
    
    logger.info(f"Embeddando {len(texts)} textos en batch")
    
    # Sentence Transformers es más eficiente para batch
    model = _get_local_model()
    embeddings = model.encode(texts, show_progress_bar=len(texts) > 10)
    
    # Normalizar todos los vectores
    normalized = [
        _normalize_vector(emb.tolist(), settings.PGVECTOR_DIM)
        for emb in embeddings
    ]
    
    logger.info(f"Batch embedding completado: {len(normalized)} vectores")
    return normalized
