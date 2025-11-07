import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from app.logger import get_logger
from app.database import SessionLocal
from app.models.activity_log import ActivityLog

logger = get_logger()


class ActivityLogMiddleware(BaseHTTPMiddleware):
    """Middleware para registrar todas las peticiones"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Obtener información de la petición
        method = request.method
        url = str(request.url.path)
        client_host = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Ejecutar petición
        response = await call_next(request)
        
        # Calcular tiempo de ejecución
        execution_time = int((time.time() - start_time) * 1000)
        
        # Log básico
        logger.info(
            f"{method} {url} - Status: {response.status_code} - Time: {execution_time}ms"
        )
        
        # Guardar en base de datos (de forma asíncrona, sin bloquear)
        try:
            db = SessionLocal()
            
            user_id = None
            if hasattr(request.state, "user"):
                user_id = request.state.user.id
            
            activity_log = ActivityLog(
                user_id=user_id,
                action=f"{method} {url}",
                endpoint=url,
                method=method,
                ip_address=client_host,
                user_agent=user_agent,
                response_status=response.status_code,
                execution_time=execution_time,
            )
            
            db.add(activity_log)
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error(f"Error guardando activity log: {e}")
        
        return response
