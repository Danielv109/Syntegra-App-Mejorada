from datetime import datetime
from typing import Optional
import re


def standardize_date(date_str: str) -> Optional[datetime]:
    """
    Convertir fechas en distintos formatos a datetime
    
    Args:
        date_str: Cadena de fecha en varios formatos posibles
        
    Returns:
        Objeto datetime o None si no se puede parsear
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    # Limpiar la cadena
    date_str = date_str.strip()
    
    # Lista de formatos comunes a intentar
    date_formats = [
        # ISO 8601 y variantes
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d",
        "%Y/%m/%d %H:%M:%S",
        
        # Formatos DD/MM/YYYY
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y",
        "%d-%m-%Y %H:%M:%S",
        
        # Formatos MM/DD/YYYY
        "%m/%d/%Y",
        "%m/%d/%Y %H:%M:%S",
        "%m-%d-%Y",
        "%m-%d-%Y %H:%M:%S",
        
        # Formatos con nombre de mes
        "%d %B %Y",
        "%d %b %Y",
        "%B %d, %Y",
        "%b %d, %Y",
        
        # Formatos en español
        "%d de %B de %Y",
        "%d de %b de %Y",
    ]
    
    # Intentar parsear con cada formato
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Intentar parseo con expresiones regulares para casos especiales
    
    # Formato: "2024-01-15T10:30:00Z" o "2024-01-15T10:30:00+00:00"
    iso_pattern = r'(\d{4}-\d{2}-\d{2})[T\s](\d{2}:\d{2}:\d{2})'
    match = re.match(iso_pattern, date_str)
    if match:
        try:
            clean_date = f"{match.group(1)} {match.group(2)}"
            return datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S")
        except:
            pass
    
    # Formato: "15/01/2024" o "2024/01/15"
    slash_pattern = r'(\d{1,4})[/-](\d{1,2})[/-](\d{1,4})'
    match = re.match(slash_pattern, date_str)
    if match:
        parts = [match.group(1), match.group(2), match.group(3)]
        
        # Determinar si es YYYY-MM-DD o DD-MM-YYYY
        if len(parts[0]) == 4:  # YYYY-MM-DD
            try:
                return datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            except:
                pass
        else:  # DD-MM-YYYY
            try:
                return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
            except:
                pass
    
    # No se pudo parsear
    return None


def parse_relative_date(relative_str: str, reference_date: datetime = None) -> Optional[datetime]:
    """
    Parsear fechas relativas como "hace 2 días", "ayer", etc.
    
    Args:
        relative_str: Cadena de fecha relativa
        reference_date: Fecha de referencia (default: ahora)
        
    Returns:
        Objeto datetime o None
    """
    from datetime import timedelta
    
    if not reference_date:
        reference_date = datetime.now()
    
    relative_str = relative_str.lower().strip()
    
    # Patrones comunes
    if relative_str in ["hoy", "today"]:
        return reference_date
    
    if relative_str in ["ayer", "yesterday"]:
        return reference_date - timedelta(days=1)
    
    if relative_str in ["mañana", "tomorrow"]:
        return reference_date + timedelta(days=1)
    
    # "hace X días/horas/minutos"
    pattern = r'hace\s+(\d+)\s+(día|días|hora|horas|minuto|minutos|semana|semanas|mes|meses)'
    match = re.match(pattern, relative_str)
    if match:
        quantity = int(match.group(1))
        unit = match.group(2)
        
        if 'día' in unit:
            return reference_date - timedelta(days=quantity)
        elif 'hora' in unit:
            return reference_date - timedelta(hours=quantity)
        elif 'minuto' in unit:
            return reference_date - timedelta(minutes=quantity)
        elif 'semana' in unit:
            return reference_date - timedelta(weeks=quantity)
        elif 'mes' in unit:
            return reference_date - timedelta(days=quantity * 30)
    
    return None


def validate_date_range(date: datetime, min_date: datetime = None, max_date: datetime = None) -> bool:
    """
    Validar que una fecha esté dentro de un rango
    
    Args:
        date: Fecha a validar
        min_date: Fecha mínima permitida
        max_date: Fecha máxima permitida
        
    Returns:
        True si está en el rango, False en caso contrario
    """
    if not date:
        return False
    
    if min_date and date < min_date:
        return False
    
    if max_date and date > max_date:
        return False
    
    return True
