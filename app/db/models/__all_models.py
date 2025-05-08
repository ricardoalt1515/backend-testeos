# Importar todos los modelos aquí para que Alembic los detecte
from app.db.base import Base
from app.db.models.user import User
from app.db.models.conversation import Conversation
from app.db.models.message import Message, RoleEnum
from app.db.models.conversation_metadata import ConversationMetadata
from app.db.models.document import Document

# Esto es importante para asegurar que las tablas se creen
__all__ = [
    "Base",
    "User",
    "Conversation",
    "Message",
    "RoleEnum",
    "ConversationMetadata",
    "Document",
]
