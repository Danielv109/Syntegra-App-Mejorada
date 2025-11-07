from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import TokenData
from app.logger import get_logger

settings = get_settings()
logger = get_logger()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash de contraseña"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crear token JWT"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """Decodificar token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: int = payload.get("sub")
        username: str = payload.get("username")
        role: str = payload.get("role")
        client_id: Optional[int] = payload.get("client_id")
        
        if user_id is None:
            raise credentials_exception
        
        token_data = TokenData(
            user_id=user_id,
            username=username,
            role=UserRole(role) if role else None,
            client_id=client_id
        )
        
        return token_data
        
    except JWTError as e:
        logger.error(f"Error decodificando token: {e}")
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Obtener usuario actual desde token"""
    token = credentials.credentials
    token_data = decode_access_token(token)
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )
    
    # Actualizar last_login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verificar que el usuario esté activo"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user


class RoleChecker:
    """Verificador de roles para endpoints"""
    
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, user: User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            logger.warning(f"Usuario {user.username} intentó acceder sin permisos adecuados")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos suficientes"
            )
        return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Autenticar usuario"""
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user
