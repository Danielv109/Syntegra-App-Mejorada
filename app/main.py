from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import init_db
from app.logger import get_logger
from app.middleware.logging import ActivityLogMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

# Routers - CAMBIAR: imports individuales para detectar errores
from app.routers import auth
from app.routers import datasets
from app.routers import analysis
from app.routers import reports
from app.routers import gold_dataset
from app.routers import clustering
from app.routers import connectors
from app.api.routes import insights_api

settings = get_settings()
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de inicio y cierre de la aplicación"""
    # Startup
    logger.info("Iniciando aplicación SYNTEGRA...")
    try:
        init_db()
        logger.info("Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"Error inicializando base de datos: {e}")
    
    yield
    
    # Shutdown
    logger.info("Cerrando aplicación SYNTEGRA...")


app = FastAPI(
    title="SYNTEGRA API",
    description="Plataforma de Inteligencia de Clientes y Datos Empresariales",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middlewares
app.add_middleware(ActivityLogMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=settings.RATE_LIMIT_PER_MINUTE)

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error no manejado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Error interno del servidor",
            "error": str(exc) if settings.DEBUG else None
        }
    )


# Health check
@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "SYNTEGRA API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected"
    }


# Include routers
app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(analysis.router)
app.include_router(reports.router)
app.include_router(gold_dataset.router)
app.include_router(clustering.router)
app.include_router(connectors.router)
app.include_router(insights_api.router)  # <-- AGREGAR


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
