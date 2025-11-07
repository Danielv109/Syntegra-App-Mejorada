from typing import Dict, Any, Optional
from app.data_processing.utils.clean_text import clean_text
from app.data_processing.utils.standardize_dates import standardize_date


def normalize_service_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizar datos de servicios (peluquerías, talleres, etc.)
    
    Args:
        data: Datos crudos de servicio
        
    Returns:
        Datos normalizados en formato estándar
    """
    normalized = {
        'type': 'service',
        'name': extract_name(data),
        'address': extract_address(data),
        'phone': extract_phone(data),
        'email': extract_email(data),
        'rating': extract_rating(data),
        'reviews_count': extract_reviews_count(data),
        'service_type': extract_service_type(data),
        'services_offered': extract_services(data),
        'pricing': extract_pricing(data),
        'opening_hours': extract_hours(data),
        'booking_available': extract_booking_info(data),
        'location': extract_location(data),
        'staff': extract_staff(data),
        'reviews': extract_reviews(data),
        'created_at': extract_date(data),
        'metadata': extract_metadata(data),
    }
    
    return normalized


def extract_name(data: Dict[str, Any]) -> str:
    """Extraer nombre del servicio"""
    possible_keys = ['name', 'nombre', 'business_name', 'service_name']
    
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


def extract_service_type(data: Dict[str, Any]) -> str:
    """Extraer tipo de servicio"""
    possible_keys = ['service_type', 'tipo_servicio', 'category', 'categoria']
    
    for key in possible_keys:
        if key in data and data[key]:
            return clean_text(str(data[key]))
    
    return "general"


def extract_services(data: Dict[str, Any]) -> list:
    """Extraer servicios ofrecidos"""
    possible_keys = ['services', 'servicios', 'offerings', 'ofertas']
    
    for key in possible_keys:
        if key in data and data[key]:
            services = data[key]
            if isinstance(services, list):
                return [
                    {
                        'name': clean_text(str(s.get('name', '') or s.get('nombre', ''))),
                        'price': s.get('price') or s.get('precio'),
                        'duration': s.get('duration') or s.get('duracion'),
                        'description': clean_text(str(s.get('description', '') or s.get('descripcion', ''))),
                    }
                    for s in services
                ]
    
    return []


def extract_pricing(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extraer información de precios"""
    pricing = {}
    
    possible_keys = ['pricing', 'precios', 'price_range', 'rango_precio']
    
    for key in possible_keys:
        if key in data and data[key]:
            value = data[key]
            if isinstance(value, dict):
                pricing = value
            elif isinstance(value, str):
                pricing['range'] = clean_text(value)
    
    return pricing


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


def extract_booking_info(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extraer información de reservas"""
    booking = {}
    
    possible_keys = ['booking', 'reservas', 'appointments', 'citas']
    
    for key in possible_keys:
        if key in data and data[key]:
            value = data[key]
            if isinstance(value, bool):
                booking['available'] = value
            elif isinstance(value, dict):
                booking = value
            elif isinstance(value, str):
                booking['available'] = 'si' in value.lower() or 'yes' in value.lower()
    
    return booking


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


def extract_staff(data: Dict[str, Any]) -> list:
    """Extraer información del personal"""
    possible_keys = ['staff', 'personal', 'employees', 'empleados']
    
    for key in possible_keys:
        if key in data and data[key]:
            staff = data[key]
            if isinstance(staff, list):
                return [
                    {
                        'name': clean_text(str(member.get('name', '') or member.get('nombre', ''))),
                        'role': clean_text(str(member.get('role', '') or member.get('cargo', ''))),
                        'specialties': member.get('specialties') or member.get('especialidades', []),
                    }
                    for member in staff
                ]
    
    return []


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
        'reviews_count', 'service_type', 'services', 'pricing',
        'hours', 'booking', 'latitude', 'longitude', 'staff', 'reviews'
    }
    
    metadata = {
        k: v for k, v in data.items()
        if k not in excluded_keys and v is not None
    }
    
    return metadata
