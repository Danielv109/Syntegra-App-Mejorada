from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db, create_client_schema
from app.models.user import User, UserRole
from app.models.client import Client
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token
from app.services.auth import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_active_user,
    RoleChecker,
)
from app.logger import get_logger

router = APIRouter(prefix="/auth", tags=["Autenticación"])
logger = get_logger()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Registrar nuevo usuario"""
    
    # Verificar si el usuario ya existe
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email o username ya está registrado"
        )
    
    # Verificar cliente si se proporciona
    if user_data.client_id:
        client = db.query(Client).filter(Client.id == user_data.client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado"
            )
    
    # Crear usuario
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=user_data.role,
        client_id=user_data.client_id,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"Usuario registrado: {new_user.username}")
    
    return new_user


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Iniciar sesión"""
    
    user = authenticate_user(db, login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Crear token
    access_token = create_access_token(
        data={
            "sub": user.id,
            "username": user.username,
            "role": user.role.value,
            "client_id": user.client_id,
        }
    )
    
    logger.info(f"Usuario autenticado: {user.username}")
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Obtener información del usuario actual"""
    return current_user


@router.post("/clients", response_model=dict, dependencies=[Depends(RoleChecker([UserRole.ADMIN_GLOBAL]))])
async def create_client(
    name: str,
    industry: str = None,
    description: str = None,
    db: Session = Depends(get_db)
):
    """Crear nuevo cliente (solo admin global)"""
    
    # Verificar si el cliente ya existe
    existing_client = db.query(Client).filter(Client.name == name).first()
    if existing_client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El cliente ya existe"
        )
    
    # Crear cliente
    new_client = Client(
        name=name,
        schema_name=f"client_{name.lower().replace(' ', '_')}",
        industry=industry,
        description=description,
    )
    
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    
    # Crear esquema en base de datos
    schema_name = create_client_schema(new_client.id)
    
    logger.info(f"Cliente creado: {new_client.name}")
    
    return {
        "message": "Cliente creado exitosamente",
        "client_id": new_client.id,
        "schema_name": schema_name
    }
