import logging
import subprocess
from typing import Dict
import re

logger = logging.getLogger(__name__)

# Palabras positivas y negativas para fallback (español e inglés)
POSITIVE_WORDS = {
    'excelente', 'bueno', 'genial', 'fantástico', 'increíble', 'perfecto',
    'excellent', 'good', 'great', 'fantastic', 'amazing', 'perfect',
    'mejor', 'positivo', 'éxito', 'ganar', 'beneficio', 'ventaja',
    'better', 'positive', 'success', 'win', 'benefit', 'advantage'
}

NEGATIVE_WORDS = {
    'malo', 'terrible', 'horrible', 'pésimo', 'problema', 'error',
    'bad', 'terrible', 'horrible', 'awful', 'problem', 'error',
    'peor', 'negativo', 'fracaso', 'perder', 'riesgo', 'desventaja',
    'worse', 'negative', 'failure', 'lose', 'risk', 'disadvantage'
}


def _try_ollama_sentiment(text: str) -> Dict[str, any]:
    """
    Intentar análisis de sentimiento con Ollama
    
    Args:
        text: Texto a analizar
        
    Returns:
        Dict con polarity y label, o None si falla
    """
    try:
        prompt = f"""Analyze the sentiment of this text and respond ONLY with one word: positive, negative, or neutral.
Text: {text[:500]}
Sentiment:"""
        
        cmd = ["ollama", "run", "llama2", prompt]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            response = result.stdout.strip().lower()
            
            if 'positive' in response:
                return {"polarity": 0.7, "label": "positive"}
            elif 'negative' in response:
                return {"polarity": -0.7, "label": "negative"}
            else:
                return {"polarity": 0.0, "label": "neutral"}
                
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning(f"Ollama sentiment analysis failed: {e}")
    
    return None


def _rule_based_sentiment(text: str) -> Dict[str, any]:
    """
    Análisis de sentimiento basado en reglas (fallback)
    
    Args:
        text: Texto a analizar
        
    Returns:
        Dict con polarity y label
    """
    text_lower = text.lower()
    words = re.findall(r'\w+', text_lower)
    
    positive_count = sum(1 for word in words if word in POSITIVE_WORDS)
    negative_count = sum(1 for word in words if word in NEGATIVE_WORDS)
    
    total = positive_count + negative_count
    
    if total == 0:
        return {"polarity": 0.0, "label": "neutral"}
    
    polarity = (positive_count - negative_count) / total
    
    if polarity > 0.2:
        label = "positive"
    elif polarity < -0.2:
        label = "negative"
    else:
        label = "neutral"
    
    return {"polarity": float(polarity), "label": label}


def analyze_sentiment(text: str) -> Dict[str, any]:
    """
    Analizar sentimiento de un texto
    
    Estrategia:
    1. Intentar Ollama local
    2. Fallback a reglas basadas en palabras
    
    Args:
        text: Texto a analizar
        
    Returns:
        Dict con:
        - polarity: float entre -1.0 y 1.0
        - label: 'positive', 'negative', o 'neutral'
    """
    if not text or not text.strip():
        return {"polarity": 0.0, "label": "neutral"}
    
    # Intentar Ollama primero
    result = _try_ollama_sentiment(text)
    
    # Fallback a reglas
    if result is None:
        logger.debug("Usando análisis de sentimiento basado en reglas")
        result = _rule_based_sentiment(text)
    
    # Validar rango de polarity
    result["polarity"] = max(-1.0, min(1.0, result["polarity"]))
    
    return result
