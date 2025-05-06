# Crear archivo tests/test_chatbot.py

import logging
import unittest
from unittest.mock import MagicMock, patch
import asyncio

from app.models.conversation import Conversation
from app.models.message import Message
from app.services.ai_service import ai_service
from app.services.questionnaire_service import questionnaire_service
from app.services.storage_service import storage_service

# Configurar logging para pruebas
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_chatbot")


class TestChatbotFlow(unittest.TestCase):
    """Pruebas para el flujo completo del chatbot"""

    def setUp(self):
        """Configuración previa a cada test"""
        # Mock para storage_service
        self.storage_mock = MagicMock()

        # Crear conversación de prueba
        self.conversation = Conversation()
        self.conversation.id = "test-conversation-id"

        # Añadir mensaje sistema inicial
        self.conversation.add_message(Message.system("Mensaje de sistema de prueba"))

    def _run_async(self, coro):
        """Ejecuta una corrutina en un nuevo event loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_initial_greeting(self):
        """Verifica que el saludo inicial tenga el formato correcto"""
        greeting = ai_service.get_initial_greeting()

        # Verificar estructura
        self.assertIn("Soy el diseñador de soluciones de agua de Hydrous AI", greeting)
        self.assertIn("**PREGUNTA: ¿En qué sector opera su empresa?**", greeting)
        self.assertIn("1. Industrial", greeting)

        # Verificar que tiene los 4 sectores
        for sector in ["Industrial", "Comercial", "Municipal", "Residencial"]:
            self.assertIn(sector, greeting)

    def test_extract_sector(self):
        """Verifica la extracción de sector de respuestas del usuario"""
        # Probar respuesta numérica
        self.assertEqual(ai_service._extract_sector("1"), "Industrial")
        self.assertEqual(ai_service._extract_sector("2"), "Comercial")

        # Probar respuesta textual
        self.assertEqual(
            ai_service._extract_sector("Trabajo en el sector Industrial"), "Industrial"
        )
        self.assertEqual(
            ai_service._extract_sector("Somos una empresa Comercial"), "Comercial"
        )

        # Probar respuesta no reconocible
        self.assertIsNone(ai_service._extract_sector("No lo sé"))

    def test_extract_subsector(self):
        """Verifica la extracción de subsector de respuestas del usuario"""
        # Probar respuesta numérica para sector Industrial
        self.assertEqual(
            ai_service._extract_subsector("1", "Industrial"), "Alimentos y Bebidas"
        )
        self.assertEqual(ai_service._extract_subsector("2", "Industrial"), "Textil")

        # Probar respuesta textual
        self.assertEqual(
            ai_service._extract_subsector("Textil", "Industrial"), "Textil"
        )
        self.assertEqual(
            ai_service._extract_subsector("Trabajamos con alimentos", "Industrial"),
            "Alimentos y Bebidas",
        )

    def test_format_response_with_questions(self):
        """Verifica el formato de respuestas con preguntas"""
        response = ai_service.format_response_with_questions(
            "Gracias por su respuesta sobre el sector.",
            "Las industrias textiles pueden reducir su consumo de agua hasta en un 40%.",
            "Conocer el subsector nos permite adaptar mejor la solución.",
            "¿Cuál es el subsector específico de su empresa?",
            ["Textil", "Alimentos y Bebidas", "Petroquímica"],
        )

        # Verificar estructura completa
        self.assertIn("Gracias por su respuesta sobre el sector.", response)
        self.assertIn("*Las industrias textiles pueden reducir su consumo", response)
        self.assertIn("Conocer el subsector nos permite", response)
        self.assertIn("**PREGUNTA: ¿Cuál es el subsector específico", response)
        self.assertIn("1. Textil", response)
        self.assertIn("2. Alimentos y Bebidas", response)
        self.assertIn("3. Petroquímica", response)

    @patch("app.services.ai_service.ai_service._update_questionnaire_state")
    @patch("app.services.ai_service.ai_service._get_next_question")
    @patch("app.services.ai_service.ai_service._generate_previous_answer_comment")
    async def test_handle_conversation_active_questionnaire(
        self, mock_comment, mock_next_question, mock_update
    ):
        """Verifica el manejo de conversación con cuestionario activo"""
        # Configurar conversación de prueba
        self.conversation.questionnaire_state.active = True
        self.conversation.questionnaire_state.sector = "Industrial"
        self.conversation.questionnaire_state.subsector = "Textil"
        self.conversation.questionnaire_state.current_question_id = "nombre_empresa"

        # Configurar mocks
        mock_comment.return_value = "Gracias por indicar su sector."
        mock_next_question.return_value = {
            "id": "ubicacion",
            "text": "¿Cuál es la ubicación de su empresa?",
            "type": "text",
            "explanation": "La ubicación es importante para entender factores regionales.",
        }

        # Ejecutar manejo de conversación
        response = await ai_service.handle_conversation(
            self.conversation, "Mi Empresa Textil"
        )

        # Verificar que se actualiza el estado
        mock_update.assert_called_once()

        # Verificar que se obtiene la siguiente pregunta
        mock_next_question.assert_called_once()

        # Verificar estructura de respuesta
        self.assertIn("Gracias por indicar su sector.", response)
        self.assertIn("**PREGUNTA: ¿Cuál es la ubicación de su empresa?**", response)

    # Agregar más pruebas para otras funcionalidades clave...


if __name__ == "__main__":
    unittest.main()
