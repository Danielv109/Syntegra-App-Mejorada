from typing import Dict, Any, Optional
from app.data_processing.utils.clean_text import clean_text
from app.data_processing.utils.standardize_dates import standardize_date


def normalize_retail_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizar datos de tiendas retail
    
    Args:
        data: Datos crudos de tienda
        
    Returns:
        Datos normalizados en formato estándar
    """
    normalized = {
        'type': 'retail',
        'name': extract_store_name(data),
        'address': extract_address(data),
        'phone': extract_phone(data),
        'email': extract_email(data),
        'rating': extract_rating(data),
        'reviews_count': extract_reviews_count(data),
        'category': extract_category(data),
        'products': extract_products(data),
        'opening_hours': extract_hours(data),
        'payment_methods': extract_payment_methods(data),
        'delivery_available': extract_delivery_info(data),
        'location': extract_location(data),
        'reviews': extract_reviews(data),
        'created_at': extract_date(data),
        'metadata': extract_metadata(data),
    }
    
    return normalized


def extract_store_name(data: Dict[str, Any]) -> str:
    """Extraer nombre de la tienda"""
    possible_keys = ['name', 'nombre', 'store_name', 'shop_name', 'business_name']
    
    for key in possible_keys:
        if key in data and data[key]:
            return clean_text(str(data[key]))
    
    return "Sin nombre"


def extract_address(data: Dict[str, Any]) -> str:
    """Extraer dirección"""
    possible_keys = ['address', 'direccion', 'location', 'ubicacion']
    
    for key in possible_keys:
        if key in data and data[key]:
            return clean_text(str(data[key]))
    
    return ""


def extract_phone(data: Dict[str, Any]) -> str:
    """Extraer teléfono"""
    possible_keys = ['phone', 'telefono', 'tel', 'contact']
    
    for key in possible_keys:
        if key in data and data[key]:
            phone = str(data[key])
            phone = ''.join(filter(str.isdigit, phone))
            return phone
    
    return ""


def extract_email(data: Dict[str, Any]) -> str:
    """Extraer email"""
    possible_keys = ['email', 'correo', 'mail']
    
    for key in possible_keys:
        if key in data and data[key]:
            return str(data[key]).lower().strip()
    
    return ""


def extract_rating(data: Dict[str, Any]) -> Optional[float]:
    """Extraer calificación"""
    possible_keys = ['rating', 'calificacion', 'score', 'stars']
    
    for key in possible_keys:
        if key in data and data[key]:
            try:
                rating = float(data[key])
                if rating > 5:
                    rating = rating / 2
                return round(rating, 1)
            except:
                pass
    
    return None


def extract_reviews_count(data: Dict[str, Any]) -> int:
    """Extraer número de reseñas"""
    possible_keys = ['reviews_count', 'num_reviews', 'total_reviews']
    
    for key in possible_keys:
        if key in data and data[key]:
            try:
                return int(data[key])
            except:
                pass
    
    return 0


def extract_category(data: Dict[str, Any]) -> list:
    """Extraer categoría de la tienda"""
    possible_keys = ['category', 'categoria', 'type', 'tipo', 'sector']
    
    categories = []
    
    for key in possible_keys:
        if key in data and data[key]:
            value = data[key]
            if isinstance(value, list):
                categories.extend([clean_text(str(c)) for c in value])
            else:
                categories.append(clean_text(str(value)))
    
    return list(set(categories))


def extract_products(data: Dict[str, Any]) -> list:
    """Extraer productos"""
    possible_keys = ['products', 'productos', 'items', 'articles', 'articulos']
    
    for key in possible_keys:
        if key in data and data[key]:
            products = data[key]
            if isinstance(products, list):
                return [
                    {
                        'name': clean_text(str(p.get('name', '') or p.get('nombre', ''))),
                        'price': p.get('price') or p.get('precio'),
                        'description': clean_text(str(p.get('description', '') or p.get('descripcion', ''))),
                        'category': clean_text(str(p.get('category', '') or p.get('categoria', ''))),
                        'stock': p.get('stock') or p.get('inventario'),
                    }
                    for p in products
                ]
    
    return []


def extract_hours(data: Dict[str, Any]) -> Dict[str, str]:
    """Extraer horario"""
    possible_keys = ['hours', 'horario', 'opening_hours', 'schedule']
    
    for key in possible_keys:
        if key in data and data[key]:
            hours = data[key]
            if isinstance(hours, dict):
                return hours
            elif isinstance(hours, str):
                return {'general': clean_text(hours)}
    
    return {}


def extract_payment_methods(data: Dict[str, Any]) -> list:
    """Extraer métodos de pago"""
    possible_keys = ['payment_methods', 'metodos_pago', 'payment', 'pagos']
    
    methods = []
    
    for key in possible_keys:
        if key in data and data[key]:
            value = data[key]
            if isinstance(value, list):
                methods.extend([clean_text(str(m)) for m in value])
            elif isinstance(value, str):
                methods.extend([clean_text(m) for m in value.split(',')])
    
    return list(set(methods))


def extract_delivery_info(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extraer información de entrega"""
    delivery = {}
    
    possible_keys = ['delivery', 'entrega', 'shipping', 'envio']
    
    for key in possible_keys:
        if key in data and data[key]:
            value = data[key]
            if isinstance(value, bool):
                delivery['available'] = value
            elif isinstance(value, dict):
                delivery = value
            elif isinstance(value, str):
                delivery['available'] = 'si' in value.lower() or 'yes' in value.lower()
    
    return delivery


def extract_location(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extraer ubicación"""
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
    possible_keys = ['reviews', 'reseñas', 'comments', 'comentarios']
    
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


def extract_date(data: Dict[str, Any]) -> Optional[str]:
    """Extraer fecha"""
    possible_keys = ['date', 'fecha', 'created_at', 'timestamp']
    
    for key in possible_keys:
        if key in data and data[key]:
            date_obj = standardize_date(str(data[key]))
            if date_obj:
                return date_obj.isoformat()
    
    return None


def extract_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extraer metadata adicional"""
    excluded_keys = {
        'name', 'nombre', 'address', 'phone', 'email', 'rating',
        'reviews_count', 'category', 'products', 'hours', 'payment_methods',
        'delivery', 'latitude', 'longitude', 'reviews'
    }
    
    metadata = {
        k: v for k, v in data.items()
        if k not in excluded_keys and v is not None
    }
    
    return metadata
