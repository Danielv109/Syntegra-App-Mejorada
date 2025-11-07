"""
Script para probar el módulo de procesamiento de datos
"""
import sys
sys.path.insert(0, '.')

from app.data_processing.utils.clean_text import clean_text, clean_text_advanced
from app.data_processing.utils.standardize_dates import standardize_date
from app.data_processing.normalizers import normalize_data


def test_text_cleaning():
    print("=" * 60)
    print("TEST: LIMPIEZA DE TEXTO")
    print("=" * 60)
    
    test_cases = [
        "<p>Hola <b>mundo</b> 😊</p>",
        "Texto    con    muchos    espacios",
        "Texto@#$%con&*caracteres()especiales",
        "Hola\nmundo\r\ncon\nsaltos",
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n{i}. Original: {text[:50]}")
        cleaned = clean_text(text)
        print(f"   Limpio:   {cleaned}")


def test_date_parsing():
    print("\n" + "=" * 60)
    print("TEST: PARSEO DE FECHAS")
    print("=" * 60)
    
    test_dates = [
        "2024-01-15",
        "15/01/2024",
        "01/15/2024",
        "January 15, 2024",
        "15 de enero de 2024",
        "2024-01-15T10:30:00Z",
    ]
    
    for date_str in test_dates:
        result = standardize_date(date_str)
        if result:
            print(f"✅ {date_str:<30} → {result.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"❌ {date_str:<30} → No se pudo parsear")


def test_normalization():
    print("\n" + "=" * 60)
    print("TEST: NORMALIZACIÓN DE DATOS")
    print("=" * 60)
    
    # Test Restaurant
    print("\n📍 Restaurant:")
    restaurant_data = {
        'name': 'Restaurante <b>Demo</b>',
        'phone': '(555) 123-4567',
        'rating': '8.5',
        'cuisine': 'Italiana',
        'address': '123 Main Street   ',
    }
    
    normalized = normalize_data(restaurant_data, 'restaurant')
    print(f"   Nombre: {normalized['name']}")
    print(f"   Teléfono: {normalized['phone']}")
    print(f"   Rating: {normalized['rating']}")
    print(f"   Cocina: {normalized['cuisine_type']}")
    
    # Test Retail
    print("\n🏪 Retail:")
    retail_data = {
        'name': 'Tienda Demo',
        'phone': '555-5678',
        'category': 'Ropa',
        'rating': 4.0,
    }
    
    normalized = normalize_data(retail_data, 'retail')
    print(f"   Nombre: {normalized['name']}")
    print(f"   Categoría: {normalized['category']}")
    print(f"   Rating: {normalized['rating']}")
    
    # Test Service
    print("\n💼 Service:")
    service_data = {
        'name': 'Peluquería Demo',
        'service_type': 'Belleza',
        'phone': '555-9012',
        'rating': 5.0,
    }
    
    normalized = normalize_data(service_data, 'service')
    print(f"   Nombre: {normalized['name']}")
    print(f"   Tipo: {normalized['service_type']}")
    print(f"   Rating: {normalized['rating']}")


def test_advanced_cleaning():
    print("\n" + "=" * 60)
    print("TEST: LIMPIEZA AVANZADA")
    print("=" * 60)
    
    text = "Hola Mundo 123! Con MAYÚSCULAS y números."
    
    print(f"\nTexto original: {text}")
    
    # Sin opciones
    result1 = clean_text(text)
    print(f"Básico:         {result1}")
    
    # Sin números
    result2 = clean_text_advanced(text, remove_numbers=True)
    print(f"Sin números:    {result2}")
    
    # Sin puntuación
    result3 = clean_text_advanced(text, remove_punctuation=True)
    print(f"Sin puntuación: {result3}")
    
    # Minúsculas
    result4 = clean_text_advanced(text, lowercase=True)
    print(f"Minúsculas:     {result4}")
    
    # Todo combinado
    result5 = clean_text_advanced(
        text,
        remove_numbers=True,
        remove_punctuation=True,
        lowercase=True
    )
    print(f"Todo combinado: {result5}")


if __name__ == "__main__":
    print("\n🧪 PRUEBAS DEL MÓDULO DATA PROCESSING\n")
    
    test_text_cleaning()
    test_date_parsing()
    test_normalization()
    test_advanced_cleaning()
    
    print("\n" + "=" * 60)
    print("✅ TODAS LAS PRUEBAS COMPLETADAS")
    print("=" * 60 + "\n")
