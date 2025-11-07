import time
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.logger import get_logger

settings = get_settings()
logger = get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware para limitar rate de peticiones"""
    
    def __init__(self, app, max_requests: int = None):
        super().__init__(app)
        self.max_requests = max_requests or settings.RATE_LIMIT_PER_MINUTE
        self.requests = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        client_host = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Limpiar peticiones antiguas (más de 60 segundos)
        self.requests[client_host] = [
            req_time for req_time in self.requests[client_host]
            if current_time - req_time < 60
        ]
        
        # Verificar límite
        if len(self.requests[client_host]) >= self.max_requests:
            logger.warning(f"Rate limit excedido para IP: {client_host}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiadas peticiones. Por favor, intente más tarde."
            )
        
        # Registrar petición
        self.requests[client_host].append(current_time)
        
        response = await call_next(request)
        return response
