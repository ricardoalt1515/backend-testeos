# app/models/conversation.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

from app.models.message import Message

# Quitar: from app.models.conversation_state import ConversationState


class Conversation(BaseModel):
    """Representa una conversación completa."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    messages: List[Message] = Field(default_factory=list)
    # --- Cambiar state por metadata simple ---
    # Quitar: state: ConversationState = Field(default_factory=ConversationState)
    metadata: Dict[str, Any] = Field(
        default_factory=lambda: {
            "current_question_id": None,
            "collected_data": {},
            "selected_sector": None,
            "selected_subsector": None,
            "questionnaire_path": [],  # Podemos seguir usando esto para referencia
            "is_complete": False,
            "has_proposal": False,
            "proposal_text": None,
            "pdf_path": None,
            "client_name": "Cliente",
            "last_error": None,
            # Puedes añadir más campos según necesites
        }
    )
    # --------------------------------------

    def add_message(self, message: Message):
        """Añade un mensaje a la conversación."""
        self.messages.append(message)
        # Limitar historial si es necesario? (Opcional)
        # MAX_HISTORY = 20
        # if len(self.messages) > MAX_HISTORY:
        #     self.messages = self.messages[-MAX_HISTORY:]

    class Config:
        allow_mutation = True


# Modelo para la respuesta al iniciar o cargar una conversación
class ConversationResponse(BaseModel):
    id: str
    created_at: datetime
    messages: List[Message]
    # Quitar state: Optional[ConversationState] = None
    metadata: Optional[Dict[str, Any]] = None  # Mantener metadata
