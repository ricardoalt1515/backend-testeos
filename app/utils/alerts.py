# Crear archivo app/utils/alerts.py

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
import os
from datetime import datetime

logger = logging.getLogger("hydrous-alerts")

# Configuración de correo (leer de variables de entorno)
SMTP_SERVER = os.environ.get("SMTP_SERVER", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ALERT_RECIPIENTS = os.environ.get("ALERT_RECIPIENTS", "").split(",")


def send_error_alert(
    error_type: str, description: str, details: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Envía una alerta por correo sobre un error crítico

    Args:
        error_type: Tipo de error
        description: Descripción del error
        details: Detalles adicionales

    Returns:
        bool: True si se envió correctamente, False en caso contrario
    """
    if not SMTP_SERVER or not SMTP_USER or not ALERT_RECIPIENTS:
        logger.warning("No se puede enviar alerta: configuración de correo incompleta")
        return False

    try:
        # Crear mensaje
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = ", ".join(ALERT_RECIPIENTS)
        msg["Subject"] = f"[ALERTA] Error en Chatbot Hydrous: {error_type}"

        # Cuerpo del mensaje
        body = f"""
        <html>
        <body>
            <h2>Alerta de Error en Chatbot Hydrous</h2>
            <p><strong>Tipo de Error:</strong> {error_type}</p>
            <p><strong>Fecha y Hora:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Descripción:</strong> {description}</p>
        """

        if details:
            body += "<h3>Detalles adicionales:</h3><ul>"
            for key, value in details.items():
                body += f"<li><strong>{key}:</strong> {value}</li>"
            body += "</ul>"

        body += """
            <p>Este es un mensaje automático generado por el sistema de monitoreo del Chatbot Hydrous.</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, "html"))

        # Enviar correo
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        logger.info(f"Alerta enviada: {error_type}")
        return True

    except Exception as e:
        logger.error(f"Error al enviar alerta: {e}")
        return False


def send_completion_notification(client_info: Dict[str, Any], proposal_id: str) -> bool:
    """
    Envía una notificación cuando se completa un cuestionario

    Args:
        client_info: Información del cliente
        proposal_id: ID de la propuesta generada

    Returns:
        bool: True si se envió correctamente, False en caso contrario
    """
    if not SMTP_SERVER or not SMTP_USER or not ALERT_RECIPIENTS:
        logger.warning(
            "No se puede enviar notificación: configuración de correo incompleta"
        )
        return False

    try:
        # Crear mensaje
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = ", ".join(ALERT_RECIPIENTS)
        msg["Subject"] = f"Nueva propuesta generada: {proposal_id}"

        # Cuerpo del mensaje
        body = f"""
        <html>
        <body>
            <h2>Nueva Propuesta de Tratamiento de Agua</h2>
            <p>Se ha generado una nueva propuesta a través del chatbot.</p>
            
            <h3>Información del Cliente:</h3>
            <ul>
                <li><strong>Empresa:</strong> {client_info.get('name', 'No especificado')}</li>
                <li><strong>Sector:</strong> {client_info.get('sector', 'No especificado')} - {client_info.get('subsector', 'No especificado')}</li>
                <li><strong>Ubicación:</strong> {client_info.get('location', 'No especificada')}</li>
            </ul>
            
            <p><strong>ID de Propuesta:</strong> {proposal_id}</p>
            <p><strong>Fecha y Hora:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <p>Puede acceder al sistema administrativo para ver los detalles completos de esta propuesta.</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, "html"))

        # Enviar correo
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        logger.info(f"Notificación enviada: nueva propuesta {proposal_id}")
        return True

    except Exception as e:
        logger.error(f"Error al enviar notificación: {e}")
        return False
