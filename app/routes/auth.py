from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
import logging
from sqlalchemy.orm import Session

from app.models.user import UserCreate, User, LoginRequest
from app.services.auth_service import auth_service
from app.db.base import get_db

# Configuración del logger
logger = logging.getLogger("hydrous")

# Crear router
router = APIRouter()


@router.post("/register", response_model=dict)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Registra un nuevo usuario"""
    try:
        # Crear usuario
        user = auth_service.create_user(user_data, db)

        # Generar token
        token_data = auth_service.create_access_token(user.id)

        # Devolver datos de usuario y token
        return {
            "status": "success",
            "message": "Usuario registrado exitosamente",
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "company_name": user.company_name,
                "location": user.location,
                "sector": user.sector,
                "subsector": user.subsector,
            },
            "token": token_data.access_token,
            "token_type": token_data.token_type,
            "expires_at": token_data.expires_at.isoformat(),
        }
    except ValueError as ve:
        # Errores de validación (ej: email duplicado)
        logger.warning(f"Error de validación en registro: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Otros errores
        logger.error(f"Error en registro: {str(e)}")
        raise HTTPException(status_code=500, detail="Error en el registro")


@router.post("/login", response_model=dict)
async def login_user(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Inicia sesión de usuario"""
    try:
        # Autenticar usuario
        user = auth_service.authenticate_user(login_data.email, login_data.password, db)

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Credenciales incorrectas",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generar token
        token_data = auth_service.create_access_token(user.id)

        # Devolver datos de usuario y token
        return {
            "status": "success",
            "message": "Inicio de sesión exitoso",
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "company_name": user.company_name,
                "location": user.location,
                "sector": user.sector,
                "subsector": user.subsector,
            },
            "token": token_data.access_token,
            "token_type": token_data.token_type,
            "expires_at": token_data.expires_at.isoformat(),
        }
    except HTTPException:
        # Re-lanzar HTTPExceptions
        raise
    except Exception as e:
        # Otros errores
        logger.error(f"Error en login: {str(e)}")
        raise HTTPException(status_code=500, detail="Error en el inicio de sesión")


@router.get("/verify", response_model=dict)
async def verify_token(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
):
    """Verifica si un token es válido"""
    try:
        # Verificar que hay un token
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Token no proporcionado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extraer token
        token = authorization.replace("Bearer ", "")

        # Verificar token
        user_data = await auth_service.verify_token(token, db)

        if not user_data:
            raise HTTPException(
                status_code=401,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Devolver datos del usuario
        return {"status": "success", "message": "Token válido", "user": user_data}
    except HTTPException:
        # Re-lanzar HTTPExceptions
        raise
    except Exception as e:
        # Otros errores
        logger.error(f"Error en verificación de token: {str(e)}")
        raise HTTPException(status_code=500, detail="Error verificando token")


@router.get("/me", response_model=dict)
async def get_current_user(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
):
    """Obtiene información del usuario actual"""
    try:
        # Verificar que hay un token
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Token no proporcionado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extraer token
        token = authorization.replace("Bearer ", "")

        # Verificar token
        user_data = await auth_service.verify_token(token, db)

        if not user_data:
            raise HTTPException(
                status_code=401,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Obtener usuario completo
        user = auth_service.get_user_by_id(user_data["id"], db)

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Usuario no encontrado",
            )

        # Devolver datos del usuario
        return {
            "status": "success",
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "company_name": user.company_name,
                "location": user.location,
                "sector": user.sector,
                "subsector": user.subsector,
                "created_at": user.created_at.isoformat(),
            },
        }
    except HTTPException:
        # Re-lanzar HTTPExceptions
        raise
    except Exception as e:
        # Otros errores
        logger.error(f"Error obteniendo usuario actual: {str(e)}")
        raise HTTPException(status_code=500, detail="Error obteniendo usuario")
