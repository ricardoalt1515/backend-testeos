from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Callable
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.services.auth_service import auth_service
from app.db.base import SessionLocal

logger = logging.getLogger("hydrous")


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware que verifica automáticamente la autenticación en todas las rutas
    excepto aquellas que están en la lista de excepciones.
    """

    def __init__(self, app, exempt_paths: list = None):
        """
        Args:
            app: La aplicación FastAPI
            exempt_paths: Lista de rutas que NO requieren autenticación
        """
        super().__init__(app)
        # Rutas que NO requieren autenticación
        self.exempt_paths = exempt_paths or [
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/forgot-password",  # Nuevo endpoint
            "/api/auth/reset-password",  # Nuevo endpoint
            "/api/auth/verify-reset-token",  # Nuevo endpoint
            "/api/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]

    async def dispatch(self, request: Request, call_next: Callable):
        """
        Este método se ejecuta en CADA petición HTTP.

        Flujo:
        1. Permite métodos OPTIONS para CORS
        2. Verifica si la ruta requiere autenticación
        3. Si requiere, extrae y valida el token JWT
        4. Si es válido, añade los datos del usuario al request
        5. Si no es válido, devuelve error 401
        6. Continúa con la petición normal
        """

        # 1. IMPORTANTE: Permitir métodos OPTIONS para CORS
        if request.method == "OPTIONS":
            return await call_next(request)

        # 2. Verificar si la ruta está exenta de autenticación
        path = request.url.path
        if any(path.startswith(exempt_path) for exempt_path in self.exempt_paths):
            return await call_next(request)

        # 3. Extraer token del header Authorization
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            logger.debug(f"Acceso denegado a {path}: Token no proporcionado")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Token de autorización requerido",
                    "error_code": "MISSING_TOKEN",
                },
                headers={
                    # Añadir headers CORS para respuestas de error
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "*",
                },
            )

        # 4. Extraer el token JWT
        token = authorization.replace("Bearer ", "")

        # 5. Verificar el token
        try:
            # Crear una sesión de base de datos para la verificación
            db = SessionLocal()
            try:
                user_data = await auth_service.verify_token(token, db)

                if not user_data:
                    logger.debug(f"Acceso denegado a {path}: Token inválido")
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "detail": "Token inválido o expirado",
                            "error_code": "INVALID_TOKEN",
                        },
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Headers": "*",
                            "Access-Control-Allow-Methods": "*",
                        },
                    )

                # 6. Añadir datos del usuario al request para uso posterior
                request.state.user = user_data
                request.state.token = token

                # Logging para monitoreo (no registramos datos sensibles)
                logger.debug(
                    f"Usuario autenticado: {user_data['id']} accediendo a {path}"
                )

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error en middleware de autenticación: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Error verificando token",
                    "error_code": "TOKEN_VERIFICATION_ERROR",
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "*",
                },
            )

        # 7. Continuar con la petición normal
        response = await call_next(request)
        return response
