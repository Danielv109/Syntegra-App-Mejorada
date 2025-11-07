from app.data_processing.normalizers.restaurant_normalizer import normalize_restaurant_data
from app.data_processing.normalizers.retail_normalizer import normalize_retail_data
from app.data_processing.normalizers.service_normalizer import normalize_service_data


def normalize_data(data: dict, source_type: str) -> dict:
    """
    Normalizar datos según el tipo de fuente
    
    Args:
        data: Datos crudos
        source_type: Tipo de fuente (restaurant, retail, service)
        
    Returns:
        Datos normalizados
    """
    normalizers = {
        'restaurant': normalize_restaurant_data,
        'retail': normalize_retail_data,
        'service': normalize_service_data,
    }
    
    normalizer = normalizers.get(source_type.lower())
    
    if normalizer:
        return normalizer(data)
    
    # Si no hay normalizador específico, devolver datos con estructura básica
    return {
        'type': source_type,
        'raw_data': data,
        'normalized': False,
    }
