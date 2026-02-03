"""
Webhook para WhatsApp (Twilio).

Recibe mensajes de Twilio y los normaliza para procesamiento.
"""

from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
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
    """
    try:
        form_data = await request.form()
        
        # From = número del usuario que envía
        # To = número del sandbox de Twilio
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
        
        if not body:
            return WebhookResponse(status="ok", message_id=message_sid)
        
        company_id = "demo_company"
        
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
        
        # from_number = usuario (a quien responder)
        background_tasks.add_task(
            process_and_respond_whatsapp,
            normalized,
            from_number
        )
        
        return WebhookResponse(status="ok", message_id=message_sid)
        
    except Exception as e:
        logger.error("whatsapp_webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def process_and_respond_whatsapp(
    message: NormalizedMessage,
    user_phone: str
):
    """
    Procesa el mensaje y envía respuesta por Twilio.
    """
    try:
        response = await process_message(message)
        
        await send_whatsapp_message(user_phone, response.message)
        
        logger.info(
            "whatsapp_response_sent",
            to=user_phone,
            message_preview=response.message[:50]
        )
        
    except Exception as e:
        logger.error("whatsapp_process_error", error=str(e))


async def send_whatsapp_message(to_number: str, message: str):
    """
    Envía mensaje por Twilio WhatsApp.
    
    to_number: número del usuario destinatario
    message: texto a enviar
    """
    from app.core.config import settings
    
    if not settings.twilio_account_sid or settings.twilio_account_sid == "tu-account-sid":
        logger.warning("twilio_not_configured", message="Twilio no está configurado")
        return
    
    try:
        from twilio.rest import Client
        
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        
        # from_ = número del sandbox de Twilio (configurado en settings)
        # to = número del usuario
        client.messages.create(
            body=message,
            from_=f"whatsapp:{settings.twilio_whatsapp_number}",
            to=f"whatsapp:{to_number}"
        )
        
        logger.info("twilio_message_sent", to=to_number)
        
    except Exception as e:
        logger.error("twilio_send_error", error=str(e))