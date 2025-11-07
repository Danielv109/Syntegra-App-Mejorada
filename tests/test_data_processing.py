import pytest
from datetime import datetime

from app.data_processing.utils.clean_text import clean_text, clean_text_advanced
from app.data_processing.utils.standardize_dates import standardize_date, parse_relative_date
from app.data_processing.normalizers import normalize_data
from app.data_processing.processor import process_incoming_data, process_single_record
from app.models.processed_data import ProcessedData
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base


# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_processing.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def setup_database():
    """Setup test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(setup_database):
    """Get database session"""
    db = TestingSessionLocal()
    yield db
    db.close()


# Tests de limpieza de texto
def test_clean_text_removes_html():
    """Test: Eliminar tags HTML"""
    text = "<p>Hola <b>mundo</b></p>"
    result = clean_text(text)
    assert result == "Hola mundo"
    assert "<p>" not in result
    assert "<b>" not in result


def test_clean_text_removes_special_characters():
    """Test: Eliminar caracteres especiales"""
    text = "Hola@#$%mundo***"
    result = clean_text(text)
    assert "@" not in result
    assert "#" not in result
    assert "Hola" in result


def test_clean_text_normalizes_whitespace():
    """Test: Normalizar espacios"""
    text = "Hola    mundo\n\ncon    espacios"
    result = clean_text(text)
    assert "  " not in result
    assert "\n" not in result


# Tests de estandarización de fechas
def test_standardize_date_iso_format():
    """Test: Parsear fecha ISO 8601"""
    date_str = "2024-01-15"
    result = standardize_date(date_str)
    assert result is not None
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15


def test_standardize_date_slash_format():
    """Test: Parsear fecha con slashes"""
    date_str = "15/01/2024"
    result = standardize_date(date_str)
    assert result is not None
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15


def test_standardize_date_invalid():
    """Test: Fecha inválida devuelve None"""
    date_str = "fecha-invalida"
    result = standardize_date(date_str)
    assert result is None


# Tests de normalización
def test_normalize_restaurant_data():
    """Test: Normalizar datos de restaurante"""
    raw_data = {
        'name': 'Restaurante Test',
        'address': '123 Main St',
        'phone': '555-1234',
        'rating': 4.5,
        'cuisine': 'Italiana',
    }
    
    result = normalize_data(raw_data, 'restaurant')
    
    assert result['type'] == 'restaurant'
    assert result['name'] == 'Restaurante Test'
    assert result['address'] == '123 Main St'
    assert result['phone'] == '5551234'
    assert result['rating'] == 4.5


def test_normalize_retail_data():
    """Test: Normalizar datos de tienda"""
    raw_data = {
        'name': 'Tienda Test',
        'address': '456 Store Ave',
        'phone': '555-5678',
        'rating': 4.0,
        'category': 'Ropa',
    }
    
    result = normalize_data(raw_data, 'retail')
    
    assert result['type'] == 'retail'
    assert result['name'] == 'Tienda Test'
    assert 'Ropa' in result['category']


def test_normalize_service_data():
    """Test: Normalizar datos de servicio"""
    raw_data = {
        'name': 'Servicio Test',
        'address': '789 Service Rd',
        'phone': '555-9012',
        'rating': 5.0,
        'service_type': 'Peluquería',
    }
    
    result = normalize_data(raw_data, 'service')
    
    assert result['type'] == 'service'
    assert result['name'] == 'Servicio Test'
    assert result['service_type'] == 'Peluquería'


# Tests de procesamiento
def test_process_single_record(db_session):
    """Test: Procesar un registro individual"""
    raw_data = {
        'name': 'Test Restaurant',
        'rating': 4.5,
    }
    
    result = process_single_record(raw_data, 'restaurant', db_session)
    
    assert isinstance(result, ProcessedData)
    assert result.id is not None
    assert result.source_type == 'restaurant'
    assert result.data['type'] == 'restaurant'


def test_process_incoming_data_batch(db_session):
    """Test: Procesar batch de registros"""
    raw_data = [
        {'name': 'Restaurant 1', 'rating': 4.0},
        {'name': 'Restaurant 2', 'rating': 4.5},
        {'name': 'Restaurant 3', 'rating': 5.0},
    ]
    
    result = process_incoming_data(raw_data, 'restaurant', db_session)
    
    assert result['total_records'] == 3
    assert result['processed_successfully'] == 3
    assert result['failed'] == 0
    
    # Verificar que se guardaron en DB
    records = db_session.query(ProcessedData).all()
    assert len(records) == 3


def test_process_incoming_data_with_errors(db_session):
    """Test: Procesamiento con algunos errores"""
    raw_data = [
        {'name': 'Valid Restaurant', 'rating': 4.0},
        None,  # Esto causará un error
        {'name': 'Another Valid', 'rating': 4.5},
    ]
    
    result = process_incoming_data(raw_data, 'restaurant', db_session)
    
    assert result['total_records'] == 3
    assert result['processed_successfully'] >= 2
    assert result['failed'] >= 1


def test_clean_text_advanced_options():
    """Test: Limpieza avanzada con opciones"""
    text = "Hola Mundo 123! Con MAYÚSCULAS."
    
    result = clean_text_advanced(
        text,
        remove_numbers=True,
        remove_punctuation=True,
        lowercase=True
    )
    
    assert "123" not in result
    assert "!" not in result
    assert result.islower()
