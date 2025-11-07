import spacy
from typing import List, Dict, Any
from collections import Counter
import re
from sentence_transformers import SentenceTransformer

from app.logger import get_logger

logger = get_logger()

# Cargar modelos (se cachean automáticamente)
try:
    nlp = spacy.load("es_core_news_sm")
    logger.info("Modelo de spaCy cargado correctamente")
except:
    logger.warning("Modelo de spaCy no encontrado, ejecute: python -m spacy download es_core_news_sm")
    nlp = None

# Modelo para embeddings
embedding_model = None


def get_embedding_model():
    """Obtener modelo de embeddings (lazy loading)"""
    global embedding_model
    if embedding_model is None:
        logger.info("Cargando modelo de embeddings...")
        embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    return embedding_model


def analyze_sentiment(text: str) -> Dict[str, float]:
    """
    Analizar sentimiento de texto (simplificado)
    En producción, usar modelo especializado o Ollama
    """
    # Palabras positivas y negativas básicas
    positive_words = {
        'excelente', 'bueno', 'genial', 'increíble', 'fantástico',
        'maravilloso', 'perfecto', 'satisfecho', 'feliz', 'contento'
    }
    negative_words = {
        'malo', 'pésimo', 'terrible', 'horrible', 'decepcionante',
        'insatisfecho', 'triste', 'enojado', 'frustrado', 'molesto'
    }
    
    text_lower = text.lower()
    words = re.findall(r'\w+', text_lower)
    
    positive_count = sum(1 for word in words if word in positive_words)
    negative_count = sum(1 for word in words if word in negative_words)
    
    total = positive_count + negative_count
    
    if total == 0:
        return {
            "positive": 0.5,
            "negative": 0.3,
            "neutral": 0.2,
        }
    
    positive_score = positive_count / total if total > 0 else 0
    negative_score = negative_count / total if total > 0 else 0
    neutral_score = 1 - (positive_score + negative_score)
    
    return {
        "positive": round(positive_score, 3),
        "negative": round(negative_score, 3),
        "neutral": round(neutral_score, 3),
    }


def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """Extraer palabras clave usando spaCy"""
    if not nlp:
        # Fallback simple
        words = re.findall(r'\w+', text.lower())
        return [word for word, count in Counter(words).most_common(top_n)]
    
    doc = nlp(text)
    
    # Extraer sustantivos y adjetivos
    keywords = [
        token.lemma_ for token in doc
        if token.pos_ in ["NOUN", "ADJ"] and not token.is_stop and len(token.text) > 3
    ]
    
    # Contar frecuencias
    keyword_counts = Counter(keywords)
    
    return [word for word, count in keyword_counts.most_common(top_n)]


def generate_embedding(text: str) -> List[float]:
    """Generar embedding vectorial del texto"""
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def analyze_text_batch(texts: List[str]) -> List[Dict[str, Any]]:
    """Analizar batch de textos"""
    results = []
    
    for text in texts:
        analysis = {
            "text": text[:200],  # Primeros 200 caracteres
            "sentiment": analyze_sentiment(text),
            "keywords": extract_keywords(text),
            "length": len(text),
            "word_count": len(text.split()),
        }
        results.append(analysis)
    
    return results
