"""
Script para crear usuario administrador inicial
"""
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.services.auth import get_password_hash

def create_admin_user():
    db = SessionLocal()
    
    try:
        # Verificar si ya existe un admin
        existing_admin = db.query(User).filter(
            User.role == UserRole.ADMIN_GLOBAL
        ).first()
        
        if existing_admin:
            print(f"Ya existe un administrador: {existing_admin.username}")
            return
        
        # Crear admin
        admin = User(
            email="admin@syntegra.com",
            username="admin",
            full_name="Administrador Global",
            hashed_password=get_password_hash("Admin123!"),
            role=UserRole.ADMIN_GLOBAL,
            is_active=True,
        )
        
        db.add(admin)
        db.commit()
        
        print("✅ Usuario administrador creado exitosamente")
        print("Username: admin")
        print("Password: Admin123!")
        print("⚠️  Cambie esta contraseña inmediatamente")
        
    except Exception as e:
        print(f"❌ Error creando administrador: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
