# app/services/storage_service.py
import logging
import os
import pickle
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

# Importar la clase Conversation que falta
from app.models.conversation import Conversation
from app.models.message import Message
from app.config import settings

logger = logging.getLogger("hydrous")

# Directorio para almacenamiento persistente temporal
TEMP_STORAGE_DIR = "temp_storage"
os.makedirs(TEMP_STORAGE_DIR, exist_ok=True)

# Usar la importación correcta para la anotación de tipo
conversations_db: Dict[str, Conversation] = {}


class StorageService:

    async def create_conversation(self) -> Conversation:
        """Crea y almacena una nueva conversación con metadata inicial."""
        initial_metadata: Dict[str, Any] = {
            "current_question_id": None,
            "collected_data": {},
            "selected_sector": None,
            "selected_subsector": None,
            "questionnaire_path": [],
            "is_complete": False,
            "has_proposal": False,
            "proposal_text": None,
            "pdf_path": None,
            "client_name": "Cliente",
            "last_error": None,
        }
        new_conversation = Conversation(metadata=initial_metadata)
        conversations_db[new_conversation.id] = new_conversation

        # También guardar en disco para persistencia
        await self.save_conversation(new_conversation)

        logger.info(
            f"DBG_SS: Conversación {new_conversation.id} CREADA. Metadata inicial: {initial_metadata}"
        )
        return new_conversation

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Obtiene una conversación por su ID (EN MEMORIA O DISCO)."""
        # Intentar obtener de memoria primero
        conversation = conversations_db.get(conversation_id)

        # Si no está en memoria, intentar cargar desde disco
        if not conversation:
            try:
                file_path = os.path.join(TEMP_STORAGE_DIR, f"{conversation_id}.pkl")
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        conversation = pickle.load(f)
                    # Guardar en memoria para futuras solicitudes
                    conversations_db[conversation_id] = conversation
                    logger.info(f"Conversación {conversation_id} recuperada de disco")
            except Exception as e:
                logger.error(f"Error cargando conversación desde disco: {e}")

        if conversation:
            if not isinstance(conversation.metadata, dict):
                logger.warning(
                    f"Metadata inválida para {conversation_id}, reiniciando a default."
                )
                # Recrear metadata inicial si está corrupta
                conversation.metadata = {
                    "current_question_id": None,
                    "collected_data": {},
                    "selected_sector": None,
                    "selected_subsector": None,
                    "questionnaire_path": [],
                    "is_complete": False,
                    "has_proposal": False,
                    "proposal_text": None,
                    "pdf_path": None,
                    "client_name": "Cliente",
                    "last_error": None,
                }
            logger.info(
                f"DBG_SS: Conversación {conversation_id} RECUPERADA. Metadata actual: {conversation.metadata}"
            )
            return conversation
        else:
            logger.warning(f"DBG_SS: Conversación {conversation_id} NO encontrada.")
            return None

    async def add_message_to_conversation(
        self, conversation_id: str, message: Message
    ) -> bool:
        """Añade un mensaje (EN MEMORIA)."""
        conversation = await self.get_conversation(conversation_id)
        if conversation:
            # Asegurarse que messages es una lista
            if not isinstance(conversation.messages, list):
                logger.warning(
                    f"Lista de mensajes inválida para {conversation_id}, reiniciando."
                )
                conversation.messages = []
            conversation.messages.append(message)

            # Guardar conversación actualizada en memoria y disco
            await self.save_conversation(conversation)

            logger.debug(
                f"DBG_SS: Mensaje '{message.role}' añadido a {conversation_id}."
            )
            return True
        else:
            logger.error(
                f"DBG_SS: Error al añadir mensaje, conversación {conversation_id} no encontrada."
            )
            return False

    async def save_conversation(self, conversation: Conversation) -> bool:
        """Guarda/Actualiza la conversación completa (EN MEMORIA Y DISCO)."""
        if not isinstance(conversation, Conversation):
            logger.error(
                f"DBG_SS: Intento de guardar objeto inválido: {type(conversation)}"
            )
            return False
        # Verificar metadata y messages antes de guardar
        if not isinstance(conversation.metadata, dict):
            logger.error(
                f"DBG_SS: Intento de guardar metadata inválida para {conversation.id}: {type(conversation.metadata)}"
            )
            return False
        if not isinstance(conversation.messages, list):
            logger.error(
                f"DBG_SS: Intento de guardar lista de mensajes inválida para {conversation.id}: {type(conversation.messages)}"
            )
            return False

        logger.info(
            f"DBG_SS: GUARDANDO conversación {conversation.id}. Metadata: {conversation.metadata}"
        )

        # Guardar en memoria
        conversations_db[conversation.id] = conversation

        # También guardar en disco para persistencia entre reinicíos
        try:
            file_path = os.path.join(TEMP_STORAGE_DIR, f"{conversation.id}.pkl")
            with open(file_path, "wb") as f:
                pickle.dump(conversation, f)
            logger.info(f"Conversación {conversation.id} guardada en disco")
        except Exception as e:
            logger.error(f"Error guardando conversación en disco: {e}")
            return False

        logger.info(
            f"DBG_SS: Conversación {conversation.id} actualizada en memoria y disco."
        )
        return True

    async def cleanup_old_conversations(self):
        """Elimina conversaciones más antiguas que el timeout (ejemplo en memoria)."""
        now = datetime.utcnow()
        timeout_delta = timedelta(seconds=settings.CONVERSATION_TIMEOUT)
        ids_to_remove = [
            conv_id
            for conv_id, conv in conversations_db.items()
            if isinstance(conv, Conversation)
            and (now - conv.created_at > timeout_delta)
        ]
        removed_count = 0
        for conv_id in ids_to_remove:
            try:
                if conv_id in conversations_db:
                    del conversations_db[conv_id]

                    # También eliminar archivo en disco
                    file_path = os.path.join(TEMP_STORAGE_DIR, f"{conv_id}.pkl")
                    if os.path.exists(file_path):
                        os.remove(file_path)

                    logger.info(f"Conversación antigua eliminada: {conv_id}")
                    removed_count += 1
            except KeyError:
                pass
        if removed_count > 0:
            logger.info(
                f"Limpieza completada. {removed_count} conversaciones antiguas eliminadas."
            )


# Instancia global
storage_service = StorageService()
