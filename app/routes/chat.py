# app/routes/chat.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import logging
import os
import uuid  # Importar uuid
import re
from datetime import datetime  # Importar datetime
from typing import Any, Optional, Dict, List  # Añadir Optional y Dict
from pydantic import BaseModel

# Modelos
from app.models.conversation import ConversationResponse, Conversation
from app.models.message import Message, MessageCreate

# Servicios
from app.services.storage_service import storage_service
from app.services.ai_service import ai_service  # IA para conversación
from app.services.pdf_service import pdf_service  # Para generar PDF
from app.services.proposal_service import (
    proposal_service,
)  # NUEVO: Para generar texto propuesta
from app.services.questionnaire_service import (
    questionnaire_service,
)  # Para obtener IDs/detalles preguntas
from app.config import settings

router = APIRouter()
logger = logging.getLogger("hydrous")

# --- Funciones Auxiliares (Movidas aquí o importadas si son complejas) ---


def _get_full_questionnaire_path(metadata: Dict[str, Any]) -> List[str]:
    """Intenta construir la ruta completa del cuestionario."""
    # Reutilizar lógica de construcción de ruta (simplificada de proposal_service o questionnaire_service original)
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
            # Fallback a solo iniciales si falla
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

    # Intentar obtener/construir la ruta completa
    path = metadata.get("questionnaire_path", [])
    if not path:  # Si no está en metadata, intentar construirla ahora
        path = _get_full_questionnaire_path(metadata)
        metadata["questionnaire_path"] = path  # Guardar por si acaso
        logger.debug(f"Ruta construida on-the-fly en _is_last_question: {path}")

    if not path:
        return False  # Si no se pudo construir, no podemos saber si es la última

    try:
        # Es la última si su índice es el último de la lista
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
        return False  # No estaba en la ruta


def _is_pdf_request(message: str) -> bool:
    """Determina si el mensaje es una solicitud de PDF de forma más robusta."""
    if not message:
        return False
    message = message.lower().strip()
    # Palabras clave específicas
    pdf_keywords = [
        "pdf",
        "descargar propuesta",
        "descargar pdf",
        "generar pdf",
        "obtener documento",
        "propuesta final",
        "descargar",
    ]  # Añadir descargar
    # Podría ser una coincidencia exacta o contener una de las frases clave
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
async def start_conversation(request_data: Optional[ConversationStartRequest] = None):
    """Inicia conversación, Recibiendo contexto del usuario si existe."""
    try:
        conversation = await storage_service.create_conversation()
        logger.info(f"Nueva conversacion iniciada (ID: {conversation.id})")

        # Procesar contexto del usuario si existe
        if request_data and request_data.customContext:
            context = request_data.customContext
            logger.info(f"Contexto recibido: {context}")

            # Actualizar metadata con datos del usuario
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

            logger.info(f"Metadata actualizada con contexto: {conversation.metadata}")

        # Guardar conversación con la metadata actualizada
        await storage_service.save_conversation(conversation)

        # Devolver respuesta
        return ConversationResponse(
            id=conversation.id,
            created_at=conversation.created_at,
            messages=[],
            metadata=conversation.metadata,
        )
    except Exception as e:
        logger.error(f"Error crítico al iniciar conversación: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="No se pudo iniciar la conversación."
        )


@router.post("/message")
async def send_message(data: MessageCreate, background_tasks: BackgroundTasks):
    """
    Procesa mensaje usuario. Si es el último, genera propuesta y PDF automáticamente.
    Si el usuario pide 'descargar pdf' (y ya está lista), dispara la descarga.
    Si no, obtiene siguiente pregunta de la IA.
    Devuelve un diccionario JSON.
    """
    conversation_id = data.conversation_id
    user_input = data.message
    assistant_response_data = None  # Para guardar la respuesta a enviar al frontend

    try:
        # 1. Cargar Conversación
        logger.debug(f"Recibida petición /message para conv: {conversation_id}")
        conversation = await storage_service.get_conversation(conversation_id)
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

        # 2. Crear objeto mensaje usuario (se añade al historial más adelante si aplica)
        user_message_obj = Message.user(user_input)

        # --- 3. Lógica para decidir el flujo: Petición PDF explícita o Continuar/Finalizar ---
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
            conversation.messages.append(user_message_obj)

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
                await storage_service.save_conversation(conversation)

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
                        conversation.id, msg_to_add
                    )
                else:
                    # Mensaje de error si falló
                    error_message = "Lo siento, hubo un problema al generar la propuesta. Por favor, inténtalo de nuevo."
                    error_msg = Message.assistant(error_message)
                    await storage_service.add_message_to_conversation(
                        conversation.id, error_msg
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
                    await storage_service.save_conversation(conversation)
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
                    conversation.id, assistant_message
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
        await storage_service.save_conversation(conversation)
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
            f"Error fatal no controlado en send_message (PDF Automático) para {conversation_id}: {str(e)}",
            exc_info=True,
        )
        # Preparar una respuesta de error genérica para el frontend
        error_response = {
            "id": "error-fatal-" + str(uuid.uuid4())[:8],
            "message": "Lo siento, ha ocurrido un error inesperado en el servidor.",
            "conversation_id": (
                conversation_id if "conversation_id" in locals() else "unknown"
            ),
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
                await storage_service.save_conversation(conversation)
        except Exception as save_err:
            # Loguear si falla el guardado del error, pero no detener el flujo
            logger.error(
                f"Error adicional al intentar guardar error fatal en metadata: {save_err}"
            )

        # Devolver la respuesta de error al frontend
        return error_response


# Endpoint /download-pdf (SIN CAMBIOS)
@router.get("/{conversation_id}/download-pdf")
async def download_pdf(conversation_id: str):
    try:
        conversation = await storage_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversación no encontrada.")

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
            # Intentar obtener un nombre más específico de la metadata o usar el predeterminado
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
