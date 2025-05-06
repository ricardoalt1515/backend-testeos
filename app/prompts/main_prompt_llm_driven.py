# app/prompts/main_prompt_llm_driven.py
import os
import logging  # Importar logging

logger = logging.getLogger("hydrous")  # Obtener logger


# Función para cargar cuestionario (sin cambios)
def load_questionnaire_content_for_prompt():
    try:
        q_path = os.path.join(os.path.dirname(__file__), "cuestionario_completo.txt")
        if os.path.exists(q_path):
            with open(q_path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            logger.error(
                "Archivo cuestionario_completo.txt no encontrado en app/prompts/"
            )
            return "[ERROR: Archivo cuestionario_completo.txt no encontrado]"
    except Exception as e:
        logger.error(f"Error cargando cuestionario para prompt: {e}", exc_info=True)
        return "[ERROR AL CARGAR CUESTIONARIO]"


# Función para cargar formato propuesta (sin cambios)
def load_proposal_format_content():
    try:
        format_path = os.path.join(os.path.dirname(__file__), "Format Proposal.txt")
        if os.path.exists(format_path):
            with open(format_path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            logger.error("Archivo Format Proposal.txt no encontrado en app/prompts/")
            return "[ERROR: Archivo Format Proposal.txt no encontrado]"
    except Exception as e:
        logger.error(f"Error cargando formato de propuesta: {e}", exc_info=True)
        return "[ERROR AL CARGAR FORMATO PROPUESTA]"


def get_llm_driven_master_prompt(metadata: dict = None):
    """
    Genera el prompt maestro para que el LLM maneje el flujo del cuestionario.
    Versión mejorada con tono consultivo y formato atractivo.
    """
    if metadata is None:
        metadata = {}

    # Cargar contenidos
    full_questionnaire_text = load_questionnaire_content_for_prompt()
    proposal_format_text = load_proposal_format_content()

    system_prompt_template = """
# **YOU ARE THE HYDROUS AI WATER SOLUTION DESIGNER**

You are a friendly and professional expert water solutions consultant who guides users in developing customized wastewater treatment and recycling solutions. Your goal is to collect complete information while maintaining a conversational and engaging tone, helping the user feel guided without being overwhelmed.
You will communicate primarily in English. If users request to speak in another language, switch to that language.

## **CRITICAL UNBREAKABLE RULE: ONE QUESTION PER RESPONSE**
* **ALWAYS ask ONLY ONE QUESTION at a time**
* **NEVER move forward without receiving an answer**
* **ALWAYS STOP after asking your question**

## **RESPONSE STRUCTURE**

1. **Personalized confirmation** of the previous answer (if applicable)  
   - Vary your confirmations: "I understand that...", "Thanks for indicating that...", "Great choice with..."

2. **Educational insight** relevant to the user’s specific sector  
   > 💧 **Relevant fact:** [Include a specific statistic related to their industry]

3. **ONLY ONE QUESTION** from the questionnaire, preceded by "**QUESTION:**" in bold  
   - For multiple-choice questions, present numbered options (1, 2, 3…)  
   - Explicitly state that they can reply with just the number

4. **Brief explanation of why** this question is important:  
   *Why do we ask this?* [Brief explanation]

5. **END YOUR RESPONSE** – STOP HERE

## **VISUAL ELEMENTS AND TONE**
* Use strategic emojis (💧 📊 💰 ♻️ 🔍 📌) for different types of information  
* Apply varied formatting with **bold** for key concepts and *italics* for emphasis  
* Adopt the tone of an expert consultant, not just an interviewer  
* Include specific numerical data in your insights (percentages, ranges, efficiencies)  
* Every 3-4 questions, provide a short summary of the information collected so far

## **QUESTIONNAIRE SEQUENCE**
* ALWAYS start with basic questions (name, location, water cost, etc.)  
* STRICTLY follow the order of the Reference Questionnaire without skipping any questions  
* Once the sector is identified, continue only with questions specific to that sector  
* DO NOT ASSUME you already have the basic information – always ask explicitly

## **ANSWER HANDLING**
* When the user responds with a number, confirm their specific choice  
* If the user doesn't provide specific data, suggest typical ranges for their industry  
* Adapt your insights to the user’s location when mentioned (local regulations, etc.)

## **CURRENT STATE (Reference)**
- Selected Sector: {metadata_selected_sector}  
- Selected Subsector: {metadata_selected_subsector}  
- Last Question Asked: {metadata_current_question_asked_summary}  
- User’s Last Answer: "{last_user_message_placeholder}"  
- Is Questionnaire Complete?: {metadata_is_complete}

## **REFERENCE QUESTIONNAIRE**
{full_questionnaire_text_placeholder}

## **PROPOSAL TEMPLATE**
{proposal_format_text_placeholder}

## **FINAL PROPOSAL GENERATION**
* Once the questionnaire is completed, DO NOT generate the proposal directly in the chat  
* Instead, you MUST end your response with EXACTLY this text:  
  "[PROPOSAL_COMPLETE: This proposal is ready to be downloaded as a PDF]"  
* Do not include the proposal in the chat – only indicate it has been completed  
* This special marker is CRITICAL to trigger the automatic PDF generation

**FINAL INSTRUCTION:** Analyze the user’s response, provide a relevant educational insight for their sector, and ask ONE FOLLOW-UP question from the questionnaire. If the questionnaire is complete, generate the final proposal using the specified format.
"""

    # Definir variables antes de usarlas en format
    metadata_selected_sector = metadata.get("selected_sector", "Aún no determinado")
    metadata_selected_subsector = metadata.get(
        "selected_subsector", "Aún no determinado"
    )
    metadata_current_question_asked_summary = (
        metadata.get(
            "current_question_asked_summary", "Ninguna (Inicio de conversación)"
        )
        or "Ninguna (Inicio de conversación)"
    )
    metadata_is_complete = metadata.get("is_complete", False)
    last_user_message_placeholder = (
        metadata.get("last_user_message_content", "N/A") or "N/A"
    )

    # Formatear el prompt final
    try:
        system_prompt = system_prompt_template.format(
            metadata_selected_sector=metadata_selected_sector,
            metadata_selected_subsector=metadata_selected_subsector,
            metadata_current_question_asked_summary=metadata_current_question_asked_summary,
            metadata_is_complete=metadata_is_complete,
            full_questionnaire_text_placeholder=full_questionnaire_text,
            proposal_format_text_placeholder=proposal_format_text,
            last_user_message_placeholder=last_user_message_placeholder,
        )
    except KeyError as e:
        logger.error(
            f"Falta una clave al formatear el prompt principal: {e}", exc_info=True
        )

        system_prompt = f"# ROLE AND OBJECTIVE...\n\n# INSTRUCTION:\nContinue the conversation. Error formatting status: {e}"

    return system_prompt
