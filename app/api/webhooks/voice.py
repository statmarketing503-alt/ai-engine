"""
Webhook para Twilio Voice.

Maneja llamadas entrantes con Speech-to-Text y Text-to-Speech.
"""

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
import structlog

from app.services.voice_service import speech_to_text, text_to_speech
from app.services.ai_service import generate_ai_response

router = APIRouter()
logger = structlog.get_logger()


@router.post("/voice", response_class=PlainTextResponse)
async def voice_webhook(request: Request):
    """
    Recibe llamadas entrantes de Twilio Voice.
    Responde con TwiML para grabar el mensaje del usuario.
    """
    form_data = await request.form()
    
    call_sid = form_data.get("CallSid", "")
    from_number = form_data.get("From", "")
    
    logger.info("voice_call_received", call_sid=call_sid, from_number=from_number)
    
    # TwiML: Saludar y grabar lo que dice el usuario
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="es-MX" voice="Polly.Mia">
        Hola, gracias por llamar. ¿En qué puedo ayudarte?
    </Say>
    <Record 
        maxLength="30" 
        action="/webhook/voice/process"
        recordingStatusCallback="/webhook/voice/status"
        transcribe="false"
        playBeep="false"
        timeout="3"
    />
    <Say language="es-MX" voice="Polly.Mia">
        No escuché nada. Por favor llama de nuevo.
    </Say>
</Response>"""
    
    return PlainTextResponse(content=twiml, media_type="application/xml")


@router.post("/voice/process", response_class=PlainTextResponse)
async def process_voice(request: Request):
    """
    Procesa la grabación del usuario.
    1. Descarga el audio
    2. Transcribe con Whisper
    3. Genera respuesta con GPT-4
    4. Responde con voz
    """
    form_data = await request.form()
    
    recording_url = form_data.get("RecordingUrl", "")
    call_sid = form_data.get("CallSid", "")
    
    logger.info("processing_voice", call_sid=call_sid, recording_url=recording_url)
    
    if not recording_url:
        return _error_response("No pude escucharte. Intenta de nuevo.")
    
    # 1. Transcribir audio con Whisper
    user_text = await speech_to_text(recording_url)
    
    if not user_text:
        return _error_response("No pude entender lo que dijiste. Intenta de nuevo.")
    
    logger.info("transcription_complete", text=user_text[:50])
    
    # 2. Generar respuesta con IA
    response = await generate_ai_response(
        user_message=user_text,
        company_id="demo_company"
    )
    
    ai_text = response.message
    logger.info("ai_response_complete", text=ai_text[:50])
    
    # 3. Responder con voz (usando Polly de Twilio por simplicidad)
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="es-MX" voice="Polly.Mia">{ai_text}</Say>
    <Say language="es-MX" voice="Polly.Mia">
        ¿Hay algo más en que pueda ayudarte?
    </Say>
    <Record 
        maxLength="30" 
        action="/webhook/voice/process"
        playBeep="false"
        timeout="5"
    />
    <Say language="es-MX" voice="Polly.Mia">
        Gracias por llamar. Hasta pronto.
    </Say>
    <Hangup/>
</Response>"""
    
    return PlainTextResponse(content=twiml, media_type="application/xml")


@router.post("/voice/status")
async def recording_status(request: Request):
    """
    Callback para el estado de la grabación.
    """
    form_data = await request.form()
    status = form_data.get("RecordingStatus", "")
    recording_url = form_data.get("RecordingUrl", "")
    
    logger.info("recording_status", status=status, url=recording_url)
    
    return {"status": "ok"}


def _error_response(message: str) -> PlainTextResponse:
    """Genera respuesta TwiML de error."""
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="es-MX" voice="Polly.Mia">{message}</Say>
    <Record 
        maxLength="30" 
        action="/webhook/voice/process"
        playBeep="false"
        timeout="3"
    />
    <Say language="es-MX" voice="Polly.Mia">
        Gracias por llamar. Hasta pronto.
    </Say>
    <Hangup/>
</Response>"""
    return PlainTextResponse(content=twiml, media_type="application/xml")