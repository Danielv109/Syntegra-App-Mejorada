import logging
from typing import List
from collections import Counter
import re

logger = logging.getLogger(__name__)

# Stopwords comunes en inglés y español
STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
    'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
    'el', 'la', 'los', 'las', 'un', 'una', 'y', 'o', 'pero', 'en', 'de',
    'para', 'con', 'por', 'que', 'es', 'son', 'está', 'están', 'ser',
}


def _fallback_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extracción simple de keywords sin NLP (fallback)
    """
    # Convertir a minúsculas y extraer palabras
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Filtrar stopwords
    filtered = [w for w in words if w not in STOPWORDS]
    
    if not filtered:
        return []
    
    # Contar frecuencias
    counter = Counter(filtered)
    most_common = counter.most_common(max_keywords)
    
    return [word for word, count in most_common]


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extraer keywords relevantes de un texto
    
    Intenta usar spaCy, si falla usa extracción simple
    
    Args:
        text: Texto a analizar
        max_keywords: Número máximo de keywords a retornar
        
    Returns:
        Lista de keywords (máximo max_keywords)
    """
    if not text or not text.strip():
        return []
    
    try:
        import spacy
        
        # Intentar cargar modelo
        try:
            nlp = spacy.load("en_core_web_md")
        except OSError:
            logger.warning("Modelo spaCy no disponible, usando extracción simple")
            return _fallback_keywords(text, max_keywords)
        
        doc = nlp(text[:5000])
        
        # Extraer sustantivos
        nouns = [
            token.lemma_.lower() 
            for token in doc 
            if token.pos_ == "NOUN" 
            and not token.is_stop 
            and len(token.text) > 2
            and token.is_alpha
        ]
        
        # Extraer entidades
        entities = [
            ent.text.lower() 
            for ent in doc.ents 
            if ent.label_ in {"PERSON", "ORG", "GPE", "PRODUCT", "EVENT"}
        ]
        
        # Combinar y contar
        all_candidates = nouns + entities
        
        if not all_candidates:
            return _fallback_keywords(text, max_keywords)
        
        counter = Counter(all_candidates)
        most_common = counter.most_common(max_keywords)
        
        keywords = [word for word, count in most_common]
        
        logger.debug(f"Extraídas {len(keywords)} keywords con spaCy")
        return keywords
        
    except ImportError:
        logger.warning("spaCy no disponible, usando extracción simple")
        return _fallback_keywords(text, max_keywords)
