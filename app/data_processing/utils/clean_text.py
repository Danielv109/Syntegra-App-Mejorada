import re
from typing import Optional


def clean_text(text: str) -> str:
    """
    Limpiar texto eliminando HTML, emojis, saltos de línea y caracteres especiales
    
    Args:
        text: Texto a limpiar
        
    Returns:
        Texto limpio
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Eliminar tags HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    # Eliminar entidades HTML
    text = re.sub(r'&[a-zA-Z]+;', '', text)
    
    # Eliminar emojis
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub(r'', text)
    
    # Normalizar saltos de línea y espacios
    text = re.sub(r'\r\n|\r|\n', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    # Eliminar caracteres especiales (mantener letras, números, espacios y puntuación básica)
    text = re.sub(r'[^\w\s.,!?;:()\-áéíóúñÁÉÍÓÚÑüÜ]', '', text)
    
    # Eliminar espacios al inicio y final
    text = text.strip()
    
    return text


def clean_text_advanced(
    text: str,
    remove_numbers: bool = False,
    remove_punctuation: bool = False,
    lowercase: bool = False
) -> str:
    """
    Limpieza avanzada de texto con opciones adicionales
    
    Args:
        text: Texto a limpiar
        remove_numbers: Si debe eliminar números
        remove_punctuation: Si debe eliminar puntuación
        lowercase: Si debe convertir a minúsculas
        
    Returns:
        Texto limpio
    """
    # Aplicar limpieza básica
    text = clean_text(text)
    
    if remove_numbers:
        text = re.sub(r'\d+', '', text)
    
    if remove_punctuation:
        text = re.sub(r'[.,!?;:()\-]', '', text)
    
    if lowercase:
        text = text.lower()
    
    # Normalizar espacios nuevamente
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def extract_clean_sentences(text: str) -> list[str]:
    """
    Extraer oraciones limpias de un texto
    
    Args:
        text: Texto de entrada
        
    Returns:
        Lista de oraciones limpias
    """
    text = clean_text(text)
    
    # Dividir por puntos, signos de exclamación e interrogación
    sentences = re.split(r'[.!?]+', text)
    
    # Limpiar y filtrar oraciones vacías
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences
