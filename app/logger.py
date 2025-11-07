import sys
from loguru import logger
from app.config import get_settings

settings = get_settings()

# Configurar formato de logs
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# Remover configuración por defecto
logger.remove()

# Agregar sink a stdout
logger.add(
    sys.stdout,
    format=log_format,
    level=settings.LOG_LEVEL,
    colorize=True,
)

# Agregar sink a archivo
logger.add(
    "logs/syntegra_{time:YYYY-MM-DD}.log",
    format=log_format,
    level=settings.LOG_LEVEL,
    rotation="00:00",
    retention="30 days",
    compression="zip",
)


def get_logger():
    return logger
