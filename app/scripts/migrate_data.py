import os
import pickle
import logging
from uuid import UUID
import sys

# Añadir directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import get_db, SessionLocal
from app.repositories.conversation_repository import conversation_repository
from app.repositories.message_repository import message_repository
from app.models.conversation import Conversation as PydanticConversation
from app.models.message import Message as PydanticMessage

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("data_migration")

# Directorio de almacenamiento actual
TEMP_STORAGE_DIR = "temp_storage"


def migrate_conversations():
    """Migra las conversaciones desde los archivos pickle a la base de datos"""

    if not os.path.exists(TEMP_STORAGE_DIR):
        logger.warning(f"Directorio {TEMP_STORAGE_DIR} no encontrado. Nada que migrar.")
        return

    # Obtener todos los archivos pickle
    pickle_files = [f for f in os.listdir(TEMP_STORAGE_DIR) if f.endswith(".pkl")]

    if not pickle_files:
        logger.info("No se encontraron archivos pickle para migrar.")
        return

    logger.info(f"Encontrados {len(pickle_files)} archivos para migrar.")

    # Obtener sesión de base de datos
    db = SessionLocal()

    try:
        # Procesar cada archivo
        for i, filename in enumerate(pickle_files):
            file_path = os.path.join(TEMP_STORAGE_DIR, filename)

            try:
                # Cargar conversación desde pickle
                with open(file_path, "rb") as f:
                    pydantic_conversation = pickle.load(f)

                # Verificar que es una instancia de Conversation
                if not isinstance(pydantic_conversation, PydanticConversation):
                    logger.warning(
                        f"Archivo {filename} no contiene una conversación válida. Omitiendo."
                    )
                    continue

                # Crear conversación en base de datos
                db_conversation = conversation_repository.create_with_metadata(
                    db,
                    obj_in={
                        "selected_sector": pydantic_conversation.metadata.get(
                            "selected_sector"
                        ),
                        "selected_subsector": pydantic_conversation.metadata.get(
                            "selected_subsector"
                        ),
                        "current_question_id": pydantic_conversation.metadata.get(
                            "current_question_id"
                        ),
                        "is_complete": pydantic_conversation.metadata.get(
                            "is_complete", False
                        ),
                        "has_proposal": pydantic_conversation.metadata.get(
                            "has_proposal", False
                        ),
                        "client_name": pydantic_conversation.metadata.get(
                            "client_name", "Cliente"
                        ),
                        "proposal_text": pydantic_conversation.metadata.get(
                            "proposal_text"
                        ),
                        "pdf_path": pydantic_conversation.metadata.get("pdf_path"),
                    },
                    metadata=pydantic_conversation.metadata,
                )

                if not db_conversation:
                    logger.error(f"Error al crear conversación para {filename}")
                    continue

                # Migrar mensajes
                for msg in pydantic_conversation.messages:
                    if not isinstance(msg, PydanticMessage):
                        logger.warning(f"Mensaje inválido en {filename}. Omitiendo.")
                        continue

                    role = getattr(msg, "role", "user")
                    content = getattr(msg, "content", "")

                    if role == "user":
                        message_repository.create_user_message(
                            db, conversation_id=db_conversation.id, content=content
                        )
                    elif role == "assistant":
                        message_repository.create_assistant_message(
                            db, conversation_id=db_conversation.id, content=content
                        )
                    elif role == "system":
                        message_repository.create_system_message(
                            db, conversation_id=db_conversation.id, content=content
                        )

                logger.info(f"Migrado {filename} ({i+1}/{len(pickle_files)})")

            except Exception as e:
                logger.error(f"Error migrando {filename}: {e}")
                continue

        logger.info("Migración completada.")

    except Exception as e:
        logger.error(f"Error global en migración: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Iniciando migración de datos...")
    migrate_conversations()
    logger.info("Proceso finalizado.")
