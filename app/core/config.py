from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database - Credenciales correctas
    DATABASE_URL: str = "postgresql://syntegra_user:Syn7egrDB2024ProdSecure@postgres:5432/syntegra_db"
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    
    # PgVector
    PGVECTOR_DIM: int = 384
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Syntegra API"
    
    class Config:
        case_sensitive = True

settings = Settings()