import redis.asyncio as redis
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
import jwt

from app.config import settings

logger = logging.getLogger("hydrous")


class TokenBlacklistService:
    """
    Servicio para gestionar la blacklist de tokens JWT.

    ¿Por qué usar Redis?
    - Performance: Acceso ultrarrápido
    - TTL automático: Los tokens se eliminan cuando expiran
    - Escalabilidad: Compartido entre múltiples instancias del servidor

    ¿Cómo funciona?
    - Al hacer logout, añadimos el token a Redis
    - Cada verificación de token consulta la blacklist
    - TTL del token = tiempo restante hasta expiración
    """

    def __init__(self):
        # Configuración de Redis
        redis_url = (
            settings.REDIS_URL
            if hasattr(settings, "REDIS_URL")
            else "redis://localhost:6379"
        )
        self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)

        # Prefijos para diferentes tipos de claves
        self.BLACKLIST_PREFIX = "blacklist:"
        self.USER_SESSIONS_PREFIX = "user_sessions:"

    async def add_to_blacklist(self, token: str) -> bool:
        """
        Añade un token a la blacklist.

        Args:
            token: JWT token a invalidar

        Returns:
            bool: True si se añadió exitosamente
        """
        try:
            # Decodificar el token para obtener el jti y exp
            # No verificamos la firma porque podría ser un token válido que estamos revocando
            decoded = jwt.decode(token, options={"verify_signature": False})

            # Obtener identificador único del token
            jti = decoded.get("jti")
            if not jti:
                # Si no hay jti, usamos hash del token
                import hashlib

                jti = hashlib.sha256(token.encode()).hexdigest()

            # Calcular TTL (tiempo hasta expiración)
            exp = decoded.get("exp")
            if exp:
                exp_datetime = datetime.fromtimestamp(exp)
                ttl = max(0, (exp_datetime - datetime.utcnow()).total_seconds())
            else:
                # Si no hay exp, usar un día por defecto
                ttl = 86400

            # Añadir a blacklist con TTL
            blacklist_key = f"{self.BLACKLIST_PREFIX}{jti}"
            await self.redis_client.setex(
                blacklist_key,
                int(ttl),
                json.dumps(
                    {
                        "invalidated_at": datetime.utcnow().isoformat(),
                        "user_id": decoded.get("sub"),
                        "reason": "logout",
                    }
                ),
            )

            logger.info(f"Token añadido a blacklist: {jti[:8]}... TTL: {ttl}s")
            return True

        except Exception as e:
            logger.error(f"Error añadiendo token a blacklist: {e}")
            return False

    async def is_blacklisted(self, token: str) -> bool:
        """
        Verifica si un token está en la blacklist.

        Args:
            token: JWT token a verificar

        Returns:
            bool: True si está blacklisted
        """
        try:
            # Decodificar token para obtener jti
            decoded = jwt.decode(token, options={"verify_signature": False})

            jti = decoded.get("jti")
            if not jti:
                import hashlib

                jti = hashlib.sha256(token.encode()).hexdigest()

            # Verificar si existe en blacklist
            blacklist_key = f"{self.BLACKLIST_PREFIX}{jti}"
            exists = await self.redis_client.exists(blacklist_key)

            if exists:
                logger.debug(f"Token blacklisted encontrado: {jti[:8]}...")
                return True

            return False

        except Exception as e:
            logger.error(f"Error verificando blacklist: {e}")
            # En caso de error, por seguridad, no permitimos el token
            return True

    async def add_user_session(
        self, user_id: str, token_data: dict, device_info: dict
    ) -> str:
        """
        Registra una sesión activa de usuario.

        Args:
            user_id: ID del usuario
            token_data: Información del token (jti, exp, etc.)
            device_info: Información del dispositivo

        Returns:
            str: ID de la sesión
        """
        try:
            session_id = (
                token_data.get("jti")
                or f"session_{user_id}_{datetime.utcnow().timestamp()}"
            )

            session_key = f"{self.USER_SESSIONS_PREFIX}{user_id}:{session_id}"

            session_data = {
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (
                    datetime.fromtimestamp(token_data.get("exp", 0)).isoformat()
                    if token_data.get("exp")
                    else None
                ),
                "device_info": device_info,
                "last_activity": datetime.utcnow().isoformat(),
            }

            # TTL basado en la expiración del token
            ttl = token_data.get("exp", 0) - datetime.utcnow().timestamp()
            ttl = max(0, int(ttl)) if ttl > 0 else 86400  # 1 día por defecto

            await self.redis_client.setex(session_key, ttl, json.dumps(session_data))

            return session_id

        except Exception as e:
            logger.error(f"Error añadiendo sesión de usuario: {e}")
            return ""

    async def invalidate_user_sessions(
        self, user_id: str, exclude_session: Optional[str] = None
    ) -> int:
        """
        Invalida todas las sesiones de un usuario (logout masivo).

        Args:
            user_id: ID del usuario
            exclude_session: ID de sesión a excluir (para logout de otros dispositivos)

        Returns:
            int: Número de sesiones invalidadas
        """
        try:
            # Buscar todas las sesiones del usuario
            pattern = f"{self.USER_SESSIONS_PREFIX}{user_id}:*"
            sessions = []

            async for key in self.redis_client.scan_iter(pattern):
                if exclude_session and key.endswith(f":{exclude_session}"):
                    continue
                sessions.append(key)

            # Obtener datos de sesiones para añadir tokens a blacklist
            invalidated = 0
            for session_key in sessions:
                session_data = await self.redis_client.get(session_key)
                if session_data:
                    session_info = json.loads(session_data)
                    # Aquí añadiríamos el token a blacklist si lo tuviéramos almacenado
                    await self.redis_client.delete(session_key)
                    invalidated += 1

            logger.info(f"Invalidadas {invalidated} sesiones para usuario {user_id}")
            return invalidated

        except Exception as e:
            logger.error(f"Error invalidando sesiones de usuario: {e}")
            return 0

    async def get_user_sessions(self, user_id: str) -> list:
        """
        Obtiene todas las sesiones activas de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            list: Lista de sesiones activas
        """
        try:
            pattern = f"{self.USER_SESSIONS_PREFIX}{user_id}:*"
            sessions = []

            async for key in self.redis_client.scan_iter(pattern):
                session_data = await self.redis_client.get(key)
                if session_data:
                    sessions.append(json.loads(session_data))

            return sessions

        except Exception as e:
            logger.error(f"Error obteniendo sesiones de usuario: {e}")
            return []


# Instancia global
blacklist_service = TokenBlacklistService()
