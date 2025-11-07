from typing import Dict, Any, Optional
from pathlib import Path
import yaml
from sqlalchemy.orm import Session

from app.models.data_source import DataSource
from app.logger import get_logger

logger = get_logger()

CONNECTORS_CONFIG_PATH = Path("config/connectors")


def load_connector_template(connector_type: str) -> Optional[Dict[str, Any]]:
    """Cargar plantilla de configuración de conector"""
    template_file = CONNECTORS_CONFIG_PATH / f"{connector_type}.yaml"
    
    if not template_file.exists():
        logger.warning(f"Plantilla de conector no encontrada: {connector_type}")
        return None
    
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            template = yaml.safe_load(f)
        return template
    except Exception as e:
        logger.error(f"Error cargando plantilla {connector_type}: {e}")
        return None


def validate_connector_config(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validar configuración de conector
    
    Returns:
        (is_valid, error_message)
    """
    if not config:
        return False, "config_json no puede estar vacío"
    
    connector_type = config.get('type')
    if not connector_type:
        return False, "El campo 'type' es requerido en config_json"
    
    # Cargar plantilla del tipo de conector
    template = load_connector_template(connector_type)
    
    if not template:
        return False, f"Tipo de conector no soportado: {connector_type}"
    
    # Validar campos requeridos
    required_fields = template.get('required_fields', [])
    for field in required_fields:
        if field not in config:
            return False, f"Campo requerido faltante: {field}"
    
    # Validar tipos de campos
    field_types = template.get('field_types', {})
    for field, expected_type in field_types.items():
        if field in config:
            value = config[field]
            
            if expected_type == 'string' and not isinstance(value, str):
                return False, f"Campo '{field}' debe ser string"
            elif expected_type == 'integer' and not isinstance(value, int):
                return False, f"Campo '{field}' debe ser integer"
            elif expected_type == 'array' and not isinstance(value, list):
                return False, f"Campo '{field}' debe ser array"
            elif expected_type == 'object' and not isinstance(value, dict):
                return False, f"Campo '{field}' debe ser object"
    
    # Validar reglas específicas
    validation_rules = template.get('validation_rules', {})
    for field, rules in validation_rules.items():
        if field in config:
            value = config[field]
            
            for rule in rules:
                if isinstance(rule, dict):
                    if 'allowed_values' in rule:
                        if value not in rule['allowed_values']:
                            return False, f"Campo '{field}' debe ser uno de: {rule['allowed_values']}"
                    
                    if 'min_length' in rule:
                        if len(value) < rule['min_length']:
                            return False, f"Campo '{field}' debe tener al menos {rule['min_length']} caracteres"
                    
                    if 'max_length' in rule:
                        if len(value) > rule['max_length']:
                            return False, f"Campo '{field}' debe tener máximo {rule['max_length']} caracteres"
    
    return True, None


def create_connector(db: Session, config: Dict[str, Any]) -> DataSource:
    """Crear un nuevo conector"""
    connector = DataSource(
        client_id=config['client_id'],
        name=config['name'],
        type=config['type'],
        config_json=config['config_json'],
        status='idle',
    )
    
    db.add(connector)
    db.commit()
    db.refresh(connector)
    
    logger.info(f"Conector creado: {connector.id} - {connector.name}")
    
    return connector


def get_connector(db: Session, connector_id: int) -> Optional[DataSource]:
    """Obtener conector por ID"""
    return db.query(DataSource).filter(DataSource.id == connector_id).first()


def run_connector(connector_id: int) -> str:
    """
    Encolar tarea de ingesta para un conector
    
    Returns:
        task_id
    """
    from app.workers.connector_tasks import ingest_source
    
    task = ingest_source.delay(connector_id)
    
    logger.info(f"Tarea de ingesta encolada: {task.id} para conector {connector_id}")
    
    return task.id
