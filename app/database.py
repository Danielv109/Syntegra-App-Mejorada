from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import get_settings
from app.logger import get_logger

settings = get_settings()
logger = get_logger()

# Crear engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
)

# Crear SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()


def get_db():
    """Dependency para obtener sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_client_schema(client_id: int):
    """Crear esquema específico para un cliente (multi-tenant)"""
    schema_name = f"client_{client_id}_data"
    
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        conn.commit()
    
    logger.info(f"Esquema {schema_name} creado correctamente")
    return schema_name


def init_db():
    """Inicializar base de datos creando todas las tablas"""
    Base.metadata.create_all(bind=engine)
    logger.info("Base de datos inicializada correctamente")
