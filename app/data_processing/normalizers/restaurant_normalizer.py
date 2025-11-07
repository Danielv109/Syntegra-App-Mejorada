from typing import Dict, Any, Optional
from app.data_processing.utils.clean_text import clean_text
from app.data_processing.utils.standardize_dates import standardize_date


def normalize_restaurant_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizar datos de restaurantes
    
    Args:
        data: Datos crudos de restaurante
        
    Returns:
        Datos normalizados en formato estándar
    """
    normalized = {
        'type': 'restaurant',
        'name': extract_name(data),
        'address': extract_address(data),
        'phone': extract_phone(data),
        'email': extract_email(data),
        'rating': extract_rating(data),
        'reviews_count': extract_reviews_count(data),
        'price_range': extract_price_range(data),
        'cuisine_type': extract_cuisine_type(data),
        'opening_hours': extract_opening_hours(data),
        'services': extract_services(data),
        'location': extract_location(data),
        'reviews': extract_reviews(data),
        'menu_items': extract_menu_items(data),
        'created_at': extract_date(data),
        'metadata': extract_metadata(data),
    }
    
    return normalized


def extract_name(data: Dict[str, Any]) -> str:
    """Extraer y limpiar nombre del restaurante"""
    possible_keys = ['name', 'nombre', 'restaurant_name', 'title', 'titulo']
    
    for key in possible_keys:
        if key in data and data[key]:
            return clean_text(str(data[key]))
    
    return "Sin nombre"


def extract_address(data: Dict[str, Any]) -> str:
    """Extraer dirección"""
    possible_keys = ['address', 'direccion', 'location', 'ubicacion', 'street']
    
    for key in possible_keys:
        if key in data and data[key]:
            return clean_text(str(data[key]))
    
    return ""


def extract_phone(data: Dict[str, Any]) -> str:
    """Extraer teléfono"""
    possible_keys = ['phone', 'telefono', 'tel', 'contact', 'contacto']
    
    for key in possible_keys:
        if key in data and data[key]:
            phone = str(data[key])
            # Limpiar formato de teléfono
            phone = ''.join(filter(str.isdigit, phone))
            return phone
    
    return ""


def extract_email(data: Dict[str, Any]) -> str:
    """Extraer email"""
    possible_keys = ['email', 'correo', 'mail', 'contact_email']
    
    for key in possible_keys:
        if key in data and data[key]:
            email = str(data[key]).lower().strip()
            return email
    
    return ""


def extract_rating(data: Dict[str, Any]) -> Optional[float]:
    """Extraer calificación"""
    possible_keys = ['rating', 'calificacion', 'score', 'puntuacion', 'stars', 'estrellas']
    
    for key in possible_keys:
        if key in data and data[key]:
            try:
                rating = float(data[key])
                # Normalizar a escala 0-5
                if rating > 5:
                    rating = rating / 2  # Si es escala 0-10
                return round(rating, 1)
            except:
                pass
    
    return None


def extract_reviews_count(data: Dict[str, Any]) -> int:
    """Extraer número de reseñas"""
    possible_keys = ['reviews_count', 'num_reviews', 'total_reviews', 'opiniones']
    
    for key in possible_keys:
        if key in data and data[key]:
            try:
                return int(data[key])
            except:
                pass
    
    return 0


def extract_price_range(data: Dict[str, Any]) -> str:
    """Extraer rango de precio"""
    possible_keys = ['price_range', 'precio', 'price', 'cost']
    
    for key in possible_keys:
        if key in data and data[key]:
            price = str(data[key])
            # Normalizar símbolos de precio
            if '$' in price:
                return price
            elif any(word in price.lower() for word in ['bajo', 'económico', 'barato']):
                return '$'
            elif any(word in price.lower() for word in ['medio', 'moderado']):
                return '$$'
            elif any(word in price.lower() for word in ['alto', 'caro', 'premium']):
                return '$$$'
    
    return '$$'


def extract_cuisine_type(data: Dict[str, Any]) -> list:
    """Extraer tipo de cocina"""
    possible_keys = ['cuisine', 'cocina', 'type', 'category', 'categoria']
    
    cuisines = []
    
    for key in possible_keys:
        if key in data and data[key]:
            value = data[key]
            if isinstance(value, list):
                cuisines.extend([clean_text(str(c)) for c in value])
            else:
                cuisines.append(clean_text(str(value)))
    
    return list(set(cuisines))


def extract_opening_hours(data: Dict[str, Any]) -> Dict[str, str]:
    """Extraer horario de apertura"""
    possible_keys = ['hours', 'horario', 'opening_hours', 'schedule']
    
    for key in possible_keys:
        if key in data and data[key]:
            hours = data[key]
            if isinstance(hours, dict):
                return hours
            elif isinstance(hours, str):
                return {'general': clean_text(hours)}
    
    return {}


def extract_services(data: Dict[str, Any]) -> list:
    """Extraer servicios ofrecidos"""
    possible_keys = ['services', 'servicios', 'amenities', 'features']
    
    services = []
    
    for key in possible_keys:
        if key in data and data[key]:
            value = data[key]
            if isinstance(value, list):
                services.extend([clean_text(str(s)) for s in value])
            elif isinstance(value, str):
                # Dividir por comas si es texto
                services.extend([clean_text(s) for s in value.split(',')])
    
    return list(set(services))


def extract_location(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extraer coordenadas de ubicación"""
    location = {}
    
    if 'latitude' in data or 'lat' in data:
        location['latitude'] = data.get('latitude') or data.get('lat')
    
    if 'longitude' in data or 'lng' in data or 'lon' in data:
        location['longitude'] = data.get('longitude') or data.get('lng') or data.get('lon')
    
    if 'city' in data or 'ciudad' in data:
        location['city'] = clean_text(str(data.get('city') or data.get('ciudad', '')))
    
    if 'state' in data or 'estado' in data:
        location['state'] = clean_text(str(data.get('state') or data.get('estado', '')))
    
    return location


def extract_reviews(data: Dict[str, Any]) -> list:
    """Extraer reseñas"""
    possible_keys = ['reviews', 'reseñas', 'comments', 'comentarios', 'opinions']
    
    for key in possible_keys:
        if key in data and data[key]:
            reviews = data[key]
            if isinstance(reviews, list):
                return [
                    {
                        'text': clean_text(str(r.get('text', '') or r.get('comment', ''))),
                        'rating': r.get('rating'),
                        'date': r.get('date'),
                        'author': clean_text(str(r.get('author', '') or r.get('user', ''))),
                    }
                    for r in reviews
                ]
    
    return []


def extract_menu_items(data: Dict[str, Any]) -> list:
    """Extraer items del menú"""
    possible_keys = ['menu', 'menu_items', 'dishes', 'platillos']
    
    for key in possible_keys:
        if key in data and data[key]:
            menu = data[key]
            if isinstance(menu, list):
                return [
                    {
                        'name': clean_text(str(item.get('name', ''))),
                        'price': item.get('price'),
                        'description': clean_text(str(item.get('description', ''))),
                    }
                    for item in menu
                ]
    
    return []


def extract_date(data: Dict[str, Any]) -> Optional[str]:
    """Extraer fecha de creación/actualización"""
    possible_keys = ['date', 'fecha', 'created_at', 'updated_at', 'timestamp']
    
    for key in possible_keys:
        if key in data and data[key]:
            date_obj = standardize_date(str(data[key]))
            if date_obj:
                return date_obj.isoformat()
    
    return None


def extract_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extraer metadata adicional"""
    # Campos que no se procesaron en las extracciones específicas
    excluded_keys = {
        'name', 'nombre', 'address', 'phone', 'email', 'rating',
        'reviews_count', 'price_range', 'cuisine', 'hours', 'services',
        'latitude', 'longitude', 'reviews', 'menu'
    }
    
    metadata = {
        k: v for k, v in data.items()
        if k not in excluded_keys and v is not None
    }
    
    return metadata
