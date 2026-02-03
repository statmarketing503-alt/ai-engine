"""
Webhook para WhatsApp (Twilio).

Recibe mensajes de Twilio y los normaliza para procesamiento.
"""

from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import Response
from datetime import datetime
import structlog

from app.schemas.message import NormalizedMessage, WebhookResponse
from app.services.orchestrator import process_message

router = APIRouter()
logger = structlog.get_logger()


@router.post("/whatsapp", response_model=WebhookResponse)
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Recibe mensajes de Twilio WhatsApp.
    
    Twilio envía datos como form-urlencoded.
    Procesamos en background para responder rápido a Twilio.
    """
    try:
        # Obtener datos del form
        form_data = await request.form()
        
        # Extraer información del mensaje
        from_number = form_data.get("From", "").replace("whatsapp:", "")
        to_number = form_data.get("To", "").replace("whatsapp:", "")
        body = form_data.get("Body", "")
        message_sid = form_data.get("MessageSid", "")
        
        logger.info(
            "whatsapp_message_received",
            from_number=from_number,
            to_number=to_number,
            message_preview=body[:50] if body else ""
        )
        
        # Validar que hay mensaje
        if not body:
            return WebhookResponse(status="ok", message_id=message_sid)
        
        # TODO: Obtener company_id basado en el número destino
        # Por ahora usamos un placeholder
        company_id = "demo_company"
        
        # Normalizar mensaje
        normalized = NormalizedMessage(
            company_id=company_id,
            user_id=from_number,
            channel="whatsapp",
            message=body,
            timestamp=datetime.utcnow(),
            metadata={
                "twilio_sid": message_sid,
                "to_number": to_number,
                "num_media": form_data.get("NumMedia", "0")
            }
        )
        
        # Procesar en background
        background_tasks.add_task(
            process_and_respond_whatsapp,
            normalized,
            from_number,
            to_number
        )
        
        return WebhookResponse(status="ok", message_id=message_sid)
        
    except Exception as e:
        logger.error("whatsapp_webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def process_and_respond_whatsapp(
    message: NormalizedMessage,
    to_number: str,
    from_number: str
):
    """
    Procesa el mensaje y envía respuesta por Twilio.
    Se ejecuta en background.
    """
    try:
        # Procesar con el orquestador
        response = await process_message(message)
        
        # Enviar respuesta por Twilio
        await send_whatsapp_message(to_number, from_number, response.message)
        
        logger.info(
            "whatsapp_response_sent",
            to=to_number,
            message_preview=response.message[:50]
        )
        
    except Exception as e:
        logger.error("whatsapp_process_error", error=str(e))


async def send_whatsapp_message(from_number: str, to_number: str, message: str):
    """
    Envía mensaje por Twilio WhatsApp.
    """
    from app.core.config import settings
    
    # Solo enviar si tenemos credenciales configuradas
    if not settings.twilio_account_sid or settings.twilio_account_sid == "tu-account-sid":
        logger.warning("twilio_not_configured", message="Twilio no está configurado")
        return
    
    try:
        from twilio.rest import Client
        
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        
        client.messages.create(
            body=message,
            from_=f"whatsapp:{from_number}",
            to=f"whatsapp:{to_number}"
        )
    except Exception as e:
        logger.error("twilio_send_error", error=str(e))