# app/routes/chat.py
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Header, Request
from fastapi.responses import FileResponse
import logging
import os
import uuid
import re
from datetime import datetime
from typing import Any, Optional, Dict, List
from pydantic import BaseModel
from uuid import UUID
from sqlalchemy.orm import Session

# Modelos
from app.models.conversation import ConversationResponse, Conversation
from app.models.message import Message, MessageCreate

# Servicios
from app.services.storage_service import storage_service
from app.services.ai_service import ai_service
from app.services.pdf_service import pdf_service
from app.services.proposal_service import proposal_service
from app.services.questionnaire_service import questionnaire_service
from app.services.auth_service import auth_service
from app.config import settings
from app.db.base import get_db

# Importar repositorios
from app.repositories.conversation_repository import conversation_repository

router = APIRouter()
logger = logging.getLogger("hydrous")

# --- Funciones Auxiliares ---


# FUNCIÓN HELPER para obtener usuario actual
def get_current_user(request: Request):
    """
    Extrae los datos del usuario autenticado del middleware.

    El middleware ya verificó el token y almacenó los datos en request.state.user
    """
    if not hasattr(request.state, "user") or not request.state.user:
        raise HTTPException(
            status_code=401, detail="No se encontraron datos de usuario autenticado"
        )
    return request.state.user


def _get_full_questionnaire_path(metadata: Dict[str, Any]) -> List[str]:
    """Intenta construir la ruta completa del cuestionario."""
    path = [
        q["id"]
        for q in questionnaire_service.structure.get("initial_questions", [])
        if "id" in q
    ]
    sector = metadata.get("selected_sector")
    subsector = metadata.get("selected_subsector")
    if sector and subsector:
        try:
            sector_data = questionnaire_service.structure.get(
                "sector_questionnaires", {}
            ).get(sector, {})
            subsector_questions = sector_data.get(subsector, [])
            if not isinstance(subsector_questions, list):
                subsector_questions = sector_data.get("Otro", [])
            path.extend([q["id"] for q in subsector_questions if "id" in q])
        except Exception as e:
            logger.error(f"Error construyendo ruta en _get_full_path: {e}")
            path = [
                q["id"]
                for q in questionnaire_service.structure.get("initial_questions", [])
                if "id" in q
            ]
    return path


def _is_last_question(
    current_question_id: Optional[str], metadata: Dict[str, Any]
) -> bool:
    """Verifica si la pregunta actual es la última de la ruta completa."""
    if not current_question_id:
        return False

    path = metadata.get("questionnaire_path", [])
    if not path:
        path = _get_full_questionnaire_path(metadata)
        metadata["questionnaire_path"] = path
        logger.debug(f"Ruta construida on-the-fly en _is_last_question: {path}")

    if not path:
        return False

    try:
        is_last = path.index(current_question_id) == len(path) - 1
        if is_last:
            logger.info(
                f"Detectada respuesta a la última pregunta ({current_question_id}) de la ruta."
            )
        return is_last
    except ValueError:
        logger.warning(
            f"_is_last_question: ID '{current_question_id}' no encontrado en ruta {path}"
        )
        return False


def _is_pdf_request(message: str) -> bool:
    """Determina si el mensaje es una solicitud de PDF de forma más robusta."""
    if not message:
        return False
    message = message.lower().strip()
    pdf_keywords = [
        "pdf",
        "descargar propuesta",
        "descargar pdf",
        "generar pdf",
        "obtener documento",
        "propuesta final",
        "descargar",
    ]
    is_request = message in pdf_keywords or any(
        keyword in message for keyword in pdf_keywords
    )
    logger.debug(
        f"_is_pdf_request: Input='{message}', Keywords={pdf_keywords}, Result={is_request}"
    )
    return is_request


# --- Endpoints ---
class ConversationStartRequest(BaseModel):
    customContext: Optional[Dict[str, Any]] = None


@router.post("/start", response_model=ConversationResponse)
async def start_conversation(
    request: Request,  # Para acceder a datos del usuario
    request_data: Optional[ConversationStartRequest] = None,
    db: Session = Depends(get_db),
):
    """Inicia conversación. Ahora requiere autenticación obligatoria."""
    try:
        # Obtener usuario autenticado del middleware
        current_user = get_current_user(request)

        # Crear conversación
        conversation = await storage_service.create_conversation(db)
        logger.info(
            f"Nueva conversacion iniciada (ID: {conversation.id}) por usuario: {current_user['id']}"
        )

        # AUTOMÁTICAMENTE asociar con usuario autenticado
        # Obtener de base de datos usando el ID de la conversación recién creada
        db_conversation = conversation_repository.get(db, UUID(conversation.id))
        if db_conversation:
            # Siempre asociamos con el usuario autenticado
            db_conversation.user_id = UUID(current_user["id"])
            db.commit()
            logger.info(
                f"Conversación {conversation.id} asociada al usuario {current_user['id']}"
            )

            # Guardar ID en metadata para verificación también
            conversation.metadata["user_id"] = current_user["id"]

        # Aplicar contexto personalizado si existe
        if request_data and request_data.customContext:
            context = request_data.customContext

            # Añadir datos del usuario al contexto
            conversation.metadata["user_email"] = current_user.get("email")
            conversation.metadata["user_name"] = (
                f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}"
            )

            # Aplicar contexto del cliente
            if "client_name" in context:
                conversation.metadata["client_name"] = context["client_name"]
            if "selected_sector" in context:
                conversation.metadata["selected_sector"] = context["selected_sector"]
            if "selected_subsector" in context:
                conversation.metadata["selected_subsector"] = context[
                    "selected_subsector"
                ]
            if "user_location" in context:
                conversation.metadata["user_location"] = context["user_location"]

            logger.info(
                f"Contexto actualizado para conversación: {conversation.metadata}"
            )

        # Guardar cambios
        await storage_service.save_conversation(conversation, db)

        return ConversationResponse(
            id=conversation.id,
            created_at=conversation.created_at,
            messages=[],
            metadata=conversation.metadata,
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error crítico al iniciar conversación: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="No se pudo iniciar la conversación."
        )


@router.post("/message")
async def send_message(
    request: Request,  # Para acceder a datos del usuario
    data: MessageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Procesa mensaje del usuario autenticado."""
    # Definir conversation_id al inicio para que esté disponible en el manejador de excepciones
    conversation_id = (
        data.conversation_id if hasattr(data, "conversation_id") else "unknown"
    )
    user_input = data.message if hasattr(data, "message") else ""
    assistant_response_data = None

    try:
        # Obtener usuario autenticado
        current_user = get_current_user(request)

        # 1. Cargar Conversación
        logger.debug(f"Recibida petición /message para conv: {conversation_id}")
        conversation = await storage_service.get_conversation(conversation_id, db)
        if not conversation:
            logger.error(f"Conversación no encontrada: {conversation_id}")
            return {
                "id": "error-conv-not-found",
                "message": "Error: Conversación no encontrada. Por favor, reinicia.",
                "conversation_id": conversation_id,
                "created_at": datetime.utcnow(),
            }
        if not isinstance(conversation.metadata, dict):
            logger.error(f"Metadata inválida para conversación: {conversation_id}")
            return {
                "id": "error-metadata",
                "message": "Error interno [MD01].",
                "conversation_id": conversation_id,
                "created_at": datetime.utcnow(),
            }

        # 2. Crear objeto mensaje usuario
        user_message_obj = Message.user(user_input)

        # VERIFICAR PROPIEDAD: Solo el dueño puede enviar mensajes
        # Obtener directamente de la base de datos para verificar el user_id
        db_conversation = conversation_repository.get(db, UUID(conversation_id))
        if not db_conversation or str(db_conversation.user_id) != current_user["id"]:
            logger.warning(
                f"Usuario {current_user['id']} intentó acceder a conversación {conversation_id} no autorizada"
            )
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para acceder a esta conversación",
            )

        # 3. Lógica para decidir el flujo
        is_pdf_req = _is_pdf_request(user_input)
        proposal_ready = conversation.metadata.get("has_proposal", False)

        logger.info(
            f"DBG_PDF_CHECK: ConvID={conversation_id}, Input='{user_input}', is_pdf_req={is_pdf_req}, proposal_ready={proposal_ready}"
        )

        if is_pdf_req and proposal_ready:
            # --- Flujo de Descarga PDF Explícita ---
            logger.info(
                f"DBG_PDF_CHECK: Entrando en flujo de descarga PDF explícita para {conversation_id}."
            )
            # NO añadir mensaje "descargar pdf" al historial
            # NO llamar a AI Service
            download_url = f"{settings.BACKEND_URL}{settings.API_V1_STR}/chat/{conversation.id}/download-pdf"
            assistant_response_data = {  # Usamos la variable común
                "id": "pdf-trigger-" + str(uuid.uuid4())[:8],
                "message": None,  # No hay mensaje de chat
                "conversation_id": conversation_id,
                "created_at": datetime.utcnow(),
                "action": "trigger_download",  # Flag para frontend
                "download_url": download_url,
            }
            logger.info(
                f"DBG_PDF_CHECK: Preparada respuesta trigger_download para {conversation_id}."
            )
            # No es necesario guardar la conversación aquí, no cambió nada crítico

        else:
            # --- Flujo Normal: Añadir mensaje usuario y Continuar/Finalizar Cuestionario ---
            logger.info(
                f"DBG_PDF_CHECK: Entrando en flujo normal/final para {conversation_id}."
            )

            # Añadir mensaje del usuario al historial en memoria AHORA
            await storage_service.add_message_to_conversation(
                conversation_id, user_message_obj, db
            )

            # Guardar un resumen de la respuesta del usuario
            if conversation.metadata.get("current_question_id"):
                question_id = conversation.metadata.get("current_question_id")
                summary = {}

                # Si ya existe un resumen, usarlo
                if conversation.metadata.get("response_summaries") is None:
                    conversation.metadata["response_summaries"] = {}

                # Guardar esta respuesta en el resumen
                conversation.metadata["response_summaries"][question_id] = {
                    "question": conversation.metadata.get(
                        "current_question_asked_summary", ""
                    ),
                    "answer": user_input.strip(),
                }

                logger.info(
                    f"Guardada respuesta para {question_id}: '{user_input.strip()}'"
                )

                # Guardar la conversación actualizada
                await storage_service.save_conversation(conversation, db)

            # Determinar si fue la última respuesta ANTES de llamar a IA
            last_question_id = conversation.metadata.get("current_question_id")
            is_final_answer = _is_last_question(last_question_id, conversation.metadata)
            logger.debug(
                f"DBG_PDF_CHECK: last_q_id='{last_question_id}', is_final_answer={is_final_answer}"
            )

            if is_final_answer:
                logger.info(
                    f"Generando propuesta para {conversation_id} con enfoque radical"
                )

                # Importar el nuevo generador
                from app.services.direct_proposal_generator import (
                    direct_proposal_generator,
                )

                # Generar propuesta y PDF directamente
                pdf_path = await direct_proposal_generator.generate_complete_proposal(
                    conversation
                )

                # Guardar en metadata
                conversation.metadata["is_complete"] = True
                conversation.metadata["current_question_id"] = None
                conversation.metadata["current_question_asked_summary"] = (
                    "Cuestionario Completado"
                )

                if pdf_path:
                    logger.info(f"Propuesta directa generada exitosamente: {pdf_path}")
                    conversation.metadata["pdf_path"] = pdf_path
                    conversation.metadata["has_proposal"] = True

                    # Preparar respuesta con descarga automática
                    download_url = f"{settings.BACKEND_URL}{settings.API_V1_STR}/chat/{conversation.id}/download-pdf"
                    assistant_response_data = {
                        "id": "proposal-ready-" + str(uuid.uuid4())[:8],
                        "message": "¡Hemos completado tu propuesta! Puedes descargarla ahora.",
                        "conversation_id": conversation_id,
                        "created_at": datetime.utcnow(),
                        "action": "download_proposal_pdf",
                        "download_url": download_url,
                    }

                    # Añadir mensaje al historial
                    msg_to_add = Message.assistant(assistant_response_data["message"])
                    await storage_service.add_message_to_conversation(
                        conversation.id, msg_to_add, db
                    )
                else:
                    # Mensaje de error si falló
                    error_message = "Lo siento, hubo un problema al generar la propuesta. Por favor, inténtalo de nuevo."
                    error_msg = Message.assistant(error_message)
                    await storage_service.add_message_to_conversation(
                        conversation.id, error_msg, db
                    )
                    assistant_response_data = {
                        "id": error_msg.id,
                        "message": error_message,
                        "conversation_id": conversation_id,
                        "created_at": error_msg.created_at,
                    }

            else:
                # --- Aún hay preguntas: Llamar a IA ---
                logger.info(
                    f"DBG_PDF_CHECK: No es la última pregunta ni petición PDF válida. Llamando a AI Service."
                )

                # Asegurarse de guardar el estado ANTES de llamar a la IA por si actualizamos sector/subsector
                try:
                    last_q_summary = conversation.metadata.get(
                        "current_question_asked_summary", ""
                    )
                    logger.debug(
                        f"Actualizando sector/subsector basado en user_input='{user_input}' y last_q_summary='{last_q_summary}'"
                    )
                    if "sector principal opera" in last_q_summary:
                        # ... (lógica para actualizar metadata["selected_sector"]) ...
                        pass
                    elif "giro específico" in last_q_summary:
                        # ... (lógica para actualizar metadata["selected_subsector"]) ...
                        pass
                    # Guardar conversación con metadata actualizada ANTES de llamar a IA
                    await storage_service.save_conversation(conversation, db)
                except Exception as e:
                    logger.error(
                        f"Error actualizando metadata antes de llamar a IA: {e}",
                        exc_info=True,
                    )
                    # Continuar de todas formas? O devolver error? Optamos por continuar.

                ai_response_content = await ai_service.handle_conversation(conversation)
                assistant_message = Message.assistant(ai_response_content)
                # Añadir respuesta de IA al historial
                await storage_service.add_message_to_conversation(
                    conversation.id, assistant_message, db
                )
                # Preparar respuesta normal para frontend
                assistant_response_data = {
                    "id": assistant_message.id,
                    "message": assistant_message.content,
                    "conversation_id": conversation_id,
                    "created_at": assistant_message.created_at,
                }

        # --- Guardar y Devolver ---
        if not assistant_response_data:
            # Fallback si algo salió MUY mal
            logger.error(
                f"Fallo crítico: No se preparó assistant_response_data para {conversation_id}"
            )
            assistant_response_data = {
                "id": "error-no-resp-prep",
                "message": "Error interno [RP01]",
                "conversation_id": conversation_id,
                "created_at": datetime.utcnow(),
            }

        # Guardar estado final de la conversación (incluye mensajes añadidos y metadata)
        await storage_service.save_conversation(conversation, db)
        background_tasks.add_task(storage_service.cleanup_old_conversations)  # Limpieza

        logger.info(
            f"Devolviendo respuesta para {conversation_id}: action={assistant_response_data.get('action', 'N/A')}, msg_len={len(assistant_response_data.get('message', '') or '')}"
        )
        return assistant_response_data

    # --- Manejo de Excepciones ---
    except HTTPException as http_exc:
        # Re-lanzar excepciones HTTP conocidas
        raise http_exc
    except Exception as e:
        # Capturar cualquier otra excepción inesperada
        logger.error(
            f"Error fatal no controlado en send_message para {conversation_id}: {str(e)}",
            exc_info=True,
        )
        # Preparar una respuesta de error genérica para el frontend
        error_response = {
            "id": "error-fatal-" + str(uuid.uuid4())[:8],
            "message": "Lo siento, ha ocurrido un error inesperado en el servidor.",
            "conversation_id": conversation_id,
            "created_at": datetime.utcnow(),
        }
        # Intentar guardar el error en la metadata de la conversación si es posible
        try:
            # Verificar si 'conversation' existe y es válida antes de accederla
            if (
                "conversation" in locals()
                and isinstance(conversation, Conversation)
                and isinstance(conversation.metadata, dict)
            ):
                conversation.metadata["last_error"] = (
                    f"Fatal: {str(e)[:200]}"  # Limitar longitud
                )
                await storage_service.save_conversation(conversation, db)
        except Exception as save_err:
            # Loguear si falla el guardado del error, pero no detener el flujo
            logger.error(
                f"Error adicional al intentar guardar error fatal en metadata: {save_err}"
            )

        # Devolver la respuesta de error al frontend
        return error_response


# Endpoint /download-pdf (SIN CAMBIOS)
@router.get("/{conversation_id}/download-pdf")
async def download_pdf(
    request: Request,  # Para acceder a datos del usuario
    conversation_id: str,
    db: Session = Depends(get_db),
):
    """Descarga PDF. Solo el dueño de la conversación puede descargar."""
    try:
        # Obtener usuario autenticado
        current_user = get_current_user(request)

        # Cargar conversación
        conversation = await storage_service.get_conversation(conversation_id, db)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")

        # VERIFICAR PROPIEDAD
        db_conversation = conversation_repository.get(db, UUID(conversation_id))
        if not db_conversation or str(db_conversation.user_id) != current_user["id"]:
            logger.warning(
                f"Usuario {current_user['id']} intentó descargar conversación {conversation_id} no autorizada"
            )
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para descargar esta propuesta",
            )

        pdf_path = conversation.metadata.get("pdf_path")

        # Si no existe, intentar generarlo de nuevo
        if not pdf_path or not os.path.exists(pdf_path):
            from app.services.direct_proposal_generator import direct_proposal_generator

            logger.info(f"Regenerando PDF bajo demanda para {conversation_id}...")
            pdf_path = await direct_proposal_generator.generate_complete_proposal(
                conversation
            )

            if not pdf_path or not os.path.exists(pdf_path):
                raise ValueError("Generación PDF falló")

        # Preparar nombre personalizado
        client_name = conversation.metadata.get("client_name", "Cliente")
        if client_name == "Cliente" and "[" not in client_name:
            client_name = "Industrias_Agua_Pura"

        # Limpiar el nombre para asegurar que sea válido como nombre de archivo
        client_name = "".join(
            c if c.isalnum() or c in "_- " else "_" for c in client_name
        )

        # Generar nombre de archivo
        filename = f"Propuesta_Hydrous_{client_name}_{conversation_id[:8]}.pdf"

        return FileResponse(
            path=pdf_path,
            filename=filename,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(
            f"Error en descarga de PDF para {conversation_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Error procesando descarga")
