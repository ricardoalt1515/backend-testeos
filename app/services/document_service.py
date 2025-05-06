# app/services/document_service.py
import os
import logging
import uuid
import re
from typing import Dict, Any, Optional, List
from fastapi import UploadFile
import shutil

from app.config import settings

logger = logging.getLogger("hydrous")


class DocumentService:
    """Servicio para procesar documentos subidos por usuarios"""

    def __init__(self):
        """Inicialización del servicio"""
        # Crear directorio de uploads si no existe
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        # Registro de documentos
        self.documents = {}

    async def process_document(
        self, file: UploadFile, conversation_id: str
    ) -> Dict[str, Any]:
        """Procesa un documento subido por un usuario"""
        try:
            # Generar ID único para el documento
            doc_id = str(uuid.uuid4())

            # Guardar el archivo físicamente
            file_ext = os.path.splitext(file.filename)[1]
            save_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}{file_ext}")

            with open(save_path, "wb") as dest_file:
                shutil.copyfileobj(file.file, dest_file)

            # Intentar extraer información relevante según el tipo de archivo
            extracted_info = await self._extract_document_info(
                save_path, file.filename, file.content_type
            )

            # Registrar documento
            doc_info = {
                "id": doc_id,
                "filename": file.filename,
                "content_type": file.content_type,
                "path": save_path,
                "conversation_id": conversation_id,
                "extracted_info": extracted_info,
            }

            self.documents[doc_id] = doc_info

            return doc_info

        except Exception as e:
            logger.error(f"Error al procesar documento: {str(e)}")
            raise

    async def _extract_document_info(
        self, file_path: str, filename: str, content_type: str
    ) -> Dict[str, Any]:
        """Extrae información básica de un documento"""
        info = {
            "summary": f"Documento: {filename}",
            "type": "unknown",
            "parameters": {},
        }

        # Determinar tipo de documento basado en nombre y extensión
        if "factura" in filename.lower() or "recibo" in filename.lower():
            info["type"] = "invoice"
            info["summary"] = "Factura o recibo de agua"

            # Extraer información básica si es un texto
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()

                # Buscar patrones comunes en facturas
                date_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
                if date_match:
                    info["parameters"]["fecha"] = date_match.group(1)

                consumption_match = re.search(r"consumo:?\s*(\d+)", text, re.IGNORECASE)
                if consumption_match:
                    info["parameters"]["consumo"] = consumption_match.group(1)

                amount_match = re.search(
                    r"total:?\s*\$?\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE
                )
                if amount_match:
                    info["parameters"]["importe"] = amount_match.group(1)

            except Exception as e:
                logger.warning(f"Error al procesar texto de factura: {str(e)}")

        elif "analisis" in filename.lower() or "laboratorio" in filename.lower():
            info["type"] = "lab_analysis"
            info["summary"] = "Análisis de laboratorio de agua"

            # Extraer información básica si es un texto
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()

                # Buscar parámetros comunes en análisis de agua
                params = [
                    ("pH", r"pH[:\s]+(\d+(?:\.\d+)?)"),
                    ("DBO", r"DBO[:\s]+(\d+(?:\.\d+)?)"),
                    ("DQO", r"DQO[:\s]+(\d+(?:\.\d+)?)"),
                    ("SST", r"SST[:\s]+(\d+(?:\.\d+)?)"),
                    ("conductividad", r"conductividad[:\s]+(\d+(?:\.\d+)?)"),
                ]

                for param, pattern in params:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        info["parameters"][param] = match.group(1)

            except Exception as e:
                logger.warning(f"Error al procesar texto de análisis: {str(e)}")

        elif content_type.startswith("image/"):
            info["type"] = "image"
            info["summary"] = (
                "Imagen que podría mostrar instalaciones o equipos de tratamiento de agua"
            )

        return info

    def format_document_info_for_prompt(self, doc_info: Dict[str, Any]) -> str:
        """Formatea información del documento para incluir en el prompt"""
        doc_type = doc_info.get("type", "unknown")
        summary = doc_info.get("extracted_info", {}).get(
            "summary", f"Documento: {doc_info['filename']}"
        )
        parameters = doc_info.get("extracted_info", {}).get("parameters", {})

        formatted_text = f"[DOCUMENTO ADJUNTO: {doc_info['filename']}]\n"
        formatted_text += f"Tipo: {doc_type}\n"
        formatted_text += f"Resumen: {summary}\n"

        if parameters:
            formatted_text += "Información extraída:\n"
            for key, value in parameters.items():
                formatted_text += f"- {key}: {value}\n"

        return formatted_text

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de un documento por su ID"""
        return self.documents.get(doc_id)

    async def get_documents_for_conversation(
        self, conversation_id: str
    ) -> List[Dict[str, Any]]:
        """Obtiene todos los documentos asociados a una conversación"""
        return [
            doc
            for doc in self.documents.values()
            if doc["conversation_id"] == conversation_id
        ]


# Instancia global
document_service = DocumentService()
