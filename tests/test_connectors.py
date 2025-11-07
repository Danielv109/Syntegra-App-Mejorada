import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models.client import Client
from app.services.auth import get_password_hash, create_access_token
from app.workers.connector_tasks import ingest_source

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_connectors.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function")
def setup_database():
    """Setup test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_client_and_user(setup_database):
    """Create test client and user"""
    db = TestingSessionLocal()
    
    # Create test client
    test_client_obj = Client(
        name="Test Client",
        schema_name="test_client",
        industry="Testing",
    )
    db.add(test_client_obj)
    db.commit()
    db.refresh(test_client_obj)
    
    # Create test user
    test_user = User(
        email="test@test.com",
        username="testuser",
        hashed_password=get_password_hash("testpass"),
        role=UserRole.CLIENTE_ADMIN,
        client_id=test_client_obj.id,
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    
    # Create access token
    access_token = create_access_token(
        data={
            "sub": test_user.id,
            "username": test_user.username,
            "role": test_user.role.value,
            "client_id": test_user.client_id,
        }
    )
    
    db.close()
    
    return {
        "client": test_client_obj,
        "user": test_user,
        "token": access_token,
    }


def test_create_connector_valid_config(test_client_and_user):
    """Test: Crear conector con configuración válida devuelve 201"""
    
    token = test_client_and_user["token"]
    client_id = test_client_and_user["client"].id
    
    connector_data = {
        "client_id": client_id,
        "name": "Test CSV Connector",
        "type": "simple_csv",
        "config_json": {
            "type": "simple_csv",
            "url": "http://example.com/data.csv",
            "delimiter": ",",
            "encoding": "utf-8",
            "columns": ["id", "name", "value"],
        }
    }
    
    response = client.post(
        "/connectors/",
        json=connector_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Test CSV Connector"
    assert data["type"] == "simple_csv"
    assert data["status"] == "idle"


def test_create_connector_invalid_config(test_client_and_user):
    """Test: Crear conector con configuración inválida devuelve 400"""
    
    token = test_client_and_user["token"]
    client_id = test_client_and_user["client"].id
    
    connector_data = {
        "client_id": client_id,
        "name": "Invalid Connector",
        "type": "simple_csv",
        "config_json": {
            "type": "simple_csv",
            # Falta campo requerido 'url'
            "delimiter": ",",
        }
    }
    
    response = client.post(
        "/connectors/",
        json=connector_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 400
    assert "inválida" in response.json()["detail"].lower()


def test_list_connectors(test_client_and_user):
    """Test: Listar conectores del cliente"""
    
    token = test_client_and_user["token"]
    client_id = test_client_and_user["client"].id
    
    # Crear un conector primero
    connector_data = {
        "client_id": client_id,
        "name": "Test Connector",
        "type": "simple_csv",
        "config_json": {
            "type": "simple_csv",
            "url": "http://example.com/data.csv",
            "delimiter": ",",
            "encoding": "utf-8",
        }
    }
    
    client.post(
        "/connectors/",
        json=connector_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Listar conectores
    response = client.get(
        "/connectors/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Test Connector"


def test_get_connector(test_client_and_user):
    """Test: Obtener detalles de un conector"""
    
    token = test_client_and_user["token"]
    client_id = test_client_and_user["client"].id
    
    # Crear conector
    connector_data = {
        "client_id": client_id,
        "name": "Test Connector",
        "type": "simple_csv",
        "config_json": {
            "type": "simple_csv",
            "url": "http://example.com/data.csv",
            "delimiter": ",",
            "encoding": "utf-8",
        }
    }
    
    create_response = client.post(
        "/connectors/",
        json=connector_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    connector_id = create_response.json()["id"]
    
    # Obtener conector
    response = client.get(
        f"/connectors/{connector_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == connector_id
    assert data["name"] == "Test Connector"


def test_run_connector_enqueues_task(test_client_and_user):
    """Test: Ejecutar conector encola tarea y responde 202"""
    
    token = test_client_and_user["token"]
    client_id = test_client_and_user["client"].id
    
    # Crear conector
    connector_data = {
        "client_id": client_id,
        "name": "Test Connector",
        "type": "simple_csv",
        "config_json": {
            "type": "simple_csv",
            "url": "http://example.com/data.csv",
            "delimiter": ",",
            "encoding": "utf-8",
            "columns": ["id", "name", "value"],
        }
    }
    
    create_response = client.post(
        "/connectors/",
        json=connector_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    connector_id = create_response.json()["id"]
    
    # Ejecutar conector
    response = client.post(
        f"/connectors/{connector_id}/run",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["source_id"] == connector_id
    assert data["message"] == "Ingesta iniciada"


def test_ingest_source_creates_file(setup_database):
    """Test: Tarea ingest_source crea archivo y registro ETL"""
    
    db = TestingSessionLocal()
    
    # Create test client
    test_client_obj = Client(
        name="Test Client",
        schema_name="test_client",
    )
    db.add(test_client_obj)
    db.commit()
    
    # Create data source
    from app.models.data_source import DataSource
    
    source = DataSource(
        client_id=test_client_obj.id,
        name="Test Source",
        type="simple_csv",
        config_json={
            "type": "simple_csv",
            "url": "http://example.com/data.csv",
            "delimiter": ",",
            "encoding": "utf-8",
            "columns": ["id", "name", "value", "date"],
        },
        status="idle",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    
    # Execute task synchronously
    result = ingest_source(source.id)
    
    assert result["status"] == "success"
    assert "file_path" in result
    
    # Verify file exists
    file_path = Path(result["file_path"])
    assert file_path.exists()
    
    # Verify ETL history
    from app.models.dataset import ETLHistory, DatasetStatus
    
    etl_records = db.query(ETLHistory).all()
    assert len(etl_records) > 0
    
    success_records = [r for r in etl_records if r.status == DatasetStatus.SUCCESS]
    assert len(success_records) > 0
    
    # Verify data source updated
    db.refresh(source)
    assert source.status == "idle"
    assert source.last_run_at is not None
    
    # Cleanup
    file_path.unlink()
    db.close()


def test_ingest_source_invalid_config_marks_error(setup_database):
    """Test: Configuración inválida marca conector como error"""
    
    db = TestingSessionLocal()
    
    # Create test client
    test_client_obj = Client(
        name="Test Client",
        schema_name="test_client",
    )
    db.add(test_client_obj)
    db.commit()
    
    # Create data source with invalid config
    from app.models.data_source import DataSource
    
    source = DataSource(
        client_id=test_client_obj.id,
        name="Invalid Source",
        type="simple_csv",
        config_json={
            "type": "simple_csv",
            # Missing required 'url' field
            "delimiter": ",",
        },
        status="idle",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    
    # Execute task
    result = ingest_source(source.id)
    
    assert result["status"] == "failed"
    assert "error" in result
    
    # Verify data source marked as error
    db.refresh(source)
    assert source.status == "error"
    
    # Verify ETL history
    from app.models.dataset import ETLHistory, DatasetStatus
    
    etl_records = db.query(ETLHistory).filter(
        ETLHistory.task_id != None
    ).all()
    
    failed_records = [r for r in etl_records if r.status == DatasetStatus.FAILED]
    assert len(failed_records) > 0
    
    db.close()
