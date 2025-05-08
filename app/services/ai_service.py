# app/services/ai_service.py
import logging
from threading import current_thread
import httpx
import os
import json  # Importar json
from typing import List, Dict, Any, Optional  # Asegurarse que Optional esté importado

from app.config import settings
from app.models.conversation import Conversation

# Importar el prompt LLM-Driven (ajusta el nombre si usaste V4)
from app.prompts.main_prompt_llm_driven import get_llm_driven_master_prompt

# Importar QuestionnaireService SOLO para IDs iniciales/texto de preguntas en metadata
from app.services.questionnaire_service import questionnaire_service

logger = logging.getLogger("hydrous")


class AIServiceLLMDriven:

    def __init__(self):
        # Cargar configuración API
        self.api_key = settings.API_KEY
        self.model = settings.MODEL
        self.api_url = settings.API_URL
        if not self.api_key:
            logger.critical("¡Clave API de IA no configurada!")
        if not self.api_url:
            logger.critical("¡URL de API de IA no configurada!")
        # El prompt maestro ahora se genera dinámicamente en _prepare_messages

    async def _call_llm_api(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1500,
        temperature: float = 0.6,
    ) -> str:
        """Llama a la API del LLM con logging y manejo de errores detallado."""
        if not self.api_key or not self.api_url:
            error_msg = "Error de configuración: Clave API o URL no proporcionada."
            logger.error(error_msg)
            # Devolver mensaje de error que se mostrará al usuario
            return "Error de Configuración Interna [AIC01]."

        response_text = ""  # Para guardar el texto de respuesta en caso de error JSON
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }

                logger.info(
                    f"DBG_AI_CALL: Iniciando llamada a API LLM. URL: {self.api_url}, Model: {self.model}, #Msgs: {len(messages)}"
                )
                # Loggear parte del payload para depuración (ej. último mensaje)
                if messages:
                    logger.debug(f"DBG_AI_CALL: Último mensaje enviado: {messages[-1]}")

                response = await client.post(
                    self.api_url, json=payload, headers=headers, timeout=90.0
                )
                response_text = (
                    response.text
                )  # Guardar texto crudo para posible error JSON
                logger.info(
                    f"DBG_AI_CALL: Llamada a API completada. Status: {response.status_code}"
                )

                response.raise_for_status()  # Lanza excepción en errores HTTP 4xx/5xx

                logger.debug("DBG_AI_CALL: Procesando respuesta JSON...")
                data = response.json()  # Puede lanzar JSONDecodeError
                logger.debug(
                    f"DBG_AI_CALL: JSON recibido OK (primeros 500 chars): {str(data)[:500]}"
                )

                choices = data.get("choices")
                if not choices:
                    logger.warning(
                        f"DBG_AI_CALL: Respuesta LLM sin 'choices'. JSON: {data}"
                    )
                    return "(Respuesta inválida del asistente [AIC02])"  # Mensaje más específico

                message_data = choices[0].get("message", {})
                content = message_data.get("content", "")

                if not content:
                    logger.warning(
                        "DBG_AI_CALL: Respuesta del LLM con contenido vacío."
                    )
                    # Podríamos devolver un mensaje específico o dejar que el flujo continúe
                    # y chat.py maneje la respuesta vacía si es necesario.
                    # Devolver un placeholder podría ser más claro que un string vacío.
                    return "(El asistente no proporcionó texto en la respuesta)"

                logger.info(
                    f"DBG_AI_CALL: Contenido LLM extraído exitosamente (longitud: {len(content)})."
                )
                return content.strip()

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            logger.error(
                f"DBG_AI_CALL: Error HTTP {e.response.status_code} en API LLM: {error_body}",
                exc_info=True,
            )
            # Devolver mensaje de error claro al usuario
            user_error_msg = (
                f"Error de comunicación con la IA ({e.response.status_code})."
            )
            # Incluir más detalles si es un error común (ej. rate limit, auth)
            if e.response.status_code == 429:
                user_error_msg += " Límite de solicitudes excedido. Espera un momento."
            elif e.response.status_code in [401, 403]:
                user_error_msg += " Problema de autenticación con la API."
            return user_error_msg
        except httpx.RequestError as e:
            logger.error(
                f"DBG_AI_CALL: Error de red llamando a API LLM: {e}", exc_info=True
            )
            return f"Error de red al contactar la IA. Verifica tu conexión."
        except json.JSONDecodeError as e:
            logger.error(
                f"DBG_AI_CALL: Error decodificando JSON de API LLM: {e}", exc_info=True
            )
            logger.error(
                f"DBG_AI_CALL: Cuerpo de respuesta (texto crudo): {response_text}"
            )
            return "Error interno al procesar la respuesta de la IA [AIC03]."
        except Exception as e:
            logger.error(
                f"DBG_AI_CALL: Error inesperado en _call_llm_api: {str(e)}",
                exc_info=True,
            )
            return (
                "Lo siento, ocurrió un error inesperado en el servicio de IA [AIC04]."
            )

    def _prepare_messages(self, conversation: Conversation) -> List[Dict[str, str]]:
        """Prepara los mensajes para la API, incluyendo el prompt dinámico e informacion del usuario."""
        logger.debug("DBG_AI_PREP: Iniciando preparación de mensajes...")
        try:
            # Generar el prompt maestro con el estado actual y el cuestionario
            current_metadata = conversation.metadata if conversation.metadata else {}

            # Verificar si tenemos datos del sector/subsector
            sector = current_metadata.get("selected_sector")
            subsector = current_metadata.get("selected_subsector")
            location = current_metadata.get("user_location")
            client_name = current_metadata.get("client_name")

            logger.info(
                f"Datos de usuario en metadata: nombre={client_name}, sector={sector}, subsector{subsector}, ubicacion={location}"
            )

            # Generar prompt principal
            system_prompt = get_llm_driven_master_prompt(current_metadata)
            messages = [{"role": "system", "content": system_prompt}]

            # Si tenemos informacion previa del usuario, añadir contexto adicional
            if sector or subsector or location:
                context_info = ["User pre-information:"]
                if client_name and client_name != "Client":
                    context_info.append(f"- Name: {client_name}")
                if sector:
                    context_info.append(f"- Sector: {sector}")
                if subsector:
                    context_info.append(f"- Subsector: {subsector}")
                if location:
                    context_info.append(f"- Ubicacion: {location}")

                # Instruccion para la AI sobre como usar esta informacion
                context_info.append(
                    "Please adapt your introduction considering this information and avoid asking for data we already know."
                )

                # Añadir mensaje de contexto
                context_message = {"role": "system", "content": "\n".join(context_info)}
                messages.append(context_message)
                logger.info("Added additional user context to the prompt.")

            # Añadir historial de conversación (si existe)
            if conversation.messages:
                MAX_HISTORY_MSGS = 15  # Ajustar según necesidad y límites de tokens
                start_index = max(0, len(conversation.messages) - MAX_HISTORY_MSGS)
                for msg in conversation.messages[start_index:]:
                    # Asegurarse que msg es un objeto con atributos role y content
                    # (Si viene de BD, podría ser un dict)
                    role = getattr(msg, "role", None)
                    content = getattr(msg, "content", None)
                    if role and content and role != "system":
                        messages.append({"role": role, "content": content})
                    else:
                        logger.warning(
                            f"Mensaje inválido o de sistema en historial omitido: {msg}"
                        )

                logger.debug(
                    f"DBG_AI_PREP: Mensajes preparados (Total: {len(messages)}). Historial añadido."
                )
            else:
                logger.debug(
                    "DBG_AI_PREP: Mensajes preparados (Total: 1). Sin historial previo."
                )

            return messages
        except Exception as e:
            logger.error(f"Error fatal en _prepare_messages: {e}", exc_info=True)
            # Lanzar excepción para que handle_conversation la capture
            raise ValueError(f"Fallo al preparar mensajes: {e}")

    async def handle_conversation(self, conversation: Conversation) -> str:
        """
        Prepara los mensajes y obtiene la respuesta del LLM.
        Actualiza el estado mínimo en metadata basado en la respuesta del LLM.
        """
        logger.info(
            f"DBG_AI_HANDLE: Iniciando handle_conversation para conv {conversation.id if conversation else 'N/A'}"
        )
        if not conversation:
            logger.error("DBG_AI_HANDLE: Objeto conversation es None.")
            return "Error interno: Conversación inválida [AIH01]."
        if not isinstance(conversation.metadata, dict):
            logger.error(f"DBG_AI_HANDLE: Metadata inválida para {conversation.id}")
            # Resetear metadata si está mal? O devolver error? Devolver error es más seguro.
            return "Error interno: Metadata de conversación corrupta [AIH02]."

        llm_response = "Error inesperado en handle_conversation [AIH03]."  # Valor por defecto en caso de fallo total

        try:
            # 1. Preparar mensajes
            logger.debug("DBG_AI_HANDLE: Llamando a _prepare_messages...")
            messages = self._prepare_messages(conversation)
            logger.info(
                f"DBG_AI_HANDLE: Mensajes preparados OK (Total: {len(messages)})."
            )

            # 2. Llamar al LLM
            logger.debug("DBG_AI_HANDLE: Llamando a _call_llm_api...")
            llm_response = await self._call_llm_api(messages)
            logger.info(
                f"DBG_AI_HANDLE: Respuesta LLM recibida (primeros 50 chars): '{llm_response[:50]}'"
            )

            # 3. Actualizar estado MÍNIMO en metadata
            #    (Solo si la respuesta NO fue un mensaje de error generado por _call_llm_api)
            #    Es importante chequear contra los posibles mensajes de error que devuelve _call_llm_api
            possible_error_prefixes = (
                "Error",
                "Lo siento",
                "(Respuesta inválida",
                "(El asistente no",
            )
            if not llm_response.startswith(possible_error_prefixes):
                logger.debug(
                    f"DBG_AI_HANDLE: Actualizando metadata para {conversation.id}..."
                )
                try:  # Envolver actualización de metadata en try/except
                    lines = llm_response.split("\n")
                    last_q_summary = conversation.metadata.get(
                        "current_question_asked_summary", "Desconocida"
                    )  # Mantener anterior si no hay nueva
                    first_question_id = None
                    is_proposal = "[PROPOSAL_COMPLETE:" in llm_response

                    # Buscar la pregunta formulada en la respuesta
                    question_found_in_response = False
                    for line in lines:
                        if line.strip().startswith("**PREGUNTA:**"):
                            last_q_summary = (
                                line.strip().replace("**PREGUNTA:**", "").strip()[:100]
                            )
                            question_found_in_response = True
                            # Determinar ID de la primera pregunta si es el inicio
                            if conversation.metadata.get("current_question_id") is None:
                                initial_q_ids = [
                                    q["id"]
                                    for q in questionnaire_service.structure.get(
                                        "initial_questions", []
                                    )
                                    if "id" in q
                                ]
                                if initial_q_ids:
                                    first_question_id = initial_q_ids[0]
                            break  # Solo la primera pregunta en la respuesta

                    # Actualizar metadata
                    if (
                        first_question_id
                        and conversation.metadata.get("current_question_id") is None
                    ):
                        conversation.metadata["current_question_id"] = first_question_id
                        logger.info(
                            f"Metadata[current_question_id] actualizada a (inicio): '{first_question_id}'"
                        )
                    # Solo actualizar el summary si encontramos una pregunta en ESTA respuesta
                    if question_found_in_response:
                        conversation.metadata["current_question_asked_summary"] = (
                            last_q_summary
                        )
                        logger.info(
                            f"Metadata[current_question_asked_summary] actualizada a: '{last_q_summary}'"
                        )
                        # Si se hizo una pregunta, el cuestionario no está completo aún
                        conversation.metadata["is_complete"] = False
                        conversation.metadata["has_proposal"] = False

                    if is_proposal:
                        proposal_clean_text = llm_response.split("[PROPOSAL_COMPLETE:")[
                            0
                        ].strip()
                        conversation.metadata["proposal_text"] = proposal_clean_text
                        conversation.metadata["is_complete"] = True
                        conversation.metadata["has_proposal"] = True
                        logger.info(
                            f"Propuesta detectada y guardada en metadata para {conversation.id}"
                        )
                        # Devolver el mensaje amigable en lugar del texto completo + marcador
                        llm_response = "✅ ¡Propuesta Lista! Escribe 'descargar pdf' para obtener tu documento."

                    logger.debug(
                        f"DBG_AI_HANDLE: Metadata actualizada OK para {conversation.id}."
                    )

                except Exception as meta_err:
                    logger.error(
                        f"Error actualizando metadata para {conversation.id}: {meta_err}",
                        exc_info=True,
                    )
                    # No cambiar llm_response aquí, dejar que se devuelva la respuesta original de IA si hubo

            else:
                logger.warning(
                    f"DBG_AI_HANDLE: Respuesta de LLM fue un mensaje de error, no se actualiza metadata: '{llm_response}'"
                )

        except ValueError as e:  # Capturar error de _prepare_messages
            logger.error(
                f"DBG_AI_HANDLE: Error preparando mensajes: {e}", exc_info=True
            )
            llm_response = f"Error interno preparando la solicitud [AIH05]."  # Mensaje genérico para usuario
        except Exception as e:
            logger.error(
                f"DBG_AI_HANDLE: Error inesperado en handle_conversation: {e}",
                exc_info=True,
            )
            llm_response = (
                "Lo siento, ocurrió un error general al procesar tu solicitud [AIH06]."
            )

        logger.info(
            f"DBG_AI_HANDLE: Finalizando handle_conversation para {conversation.id}. Respuesta a devolver (primeros 50): '{llm_response[:50]}'"
        )
        return llm_response


# Instancia global
# Asegúrate de que el nombre de la clase aquí coincida con el usado en el import de chat.py
# Si chat.py importa 'ai_service', la instancia debe llamarse así.
ai_service = AIServiceLLMDriven()
