"""
Webhook para Twilio Voice.
"""

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
import structlog

from app.services.voice_service import speech_to_text
from app.services.ai_service import generate_ai_response

router = APIRouter()
logger = structlog.get_logger()


@router.post("/voice", response_class=PlainTextResponse)
async def voice_webhook(request: Request):
    """
    Recibe llamadas entrantes de Twilio Voice.
    """
    form_data = await request.form()
    
    call_sid = form_data.get("CallSid", "")
    from_number = form_data.get("From", "")
    
    print(f"📞 LLAMADA RECIBIDA: {from_number}")
    
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="es-MX" voice="Polly.Mia">
        Hola, gracias por llamar. ¿En qué puedo ayudarte?
    </Say>
    <Record 
        maxLength="20" 
        action="/webhook/voice/process"
        playBeep="false"
        timeout="2"
    />
    <Say language="es-MX" voice="Polly.Mia">
        No escuché nada. Hasta pronto.
    </Say>
    <Hangup/>
</Response>"""
    
    return PlainTextResponse(content=twiml, media_type="application/xml")


@router.post("/voice/process", response_class=PlainTextResponse)
async def process_voice(request: Request):
    """
    Procesa la grabación del usuario.
    """
    form_data = await request.form()
    
    recording_url = form_data.get("RecordingUrl", "")
    
    print(f"🎙️ PROCESANDO AUDIO: {recording_url}")
    
    if not recording_url:
        return _hangup_response("No pude escucharte. Hasta pronto.")
    
    # 1. Transcribir audio con Whisper
    print("🔄 Transcribiendo con Whisper...")
    user_text = await speech_to_text(recording_url)
    
    if not user_text:
        return _hangup_response("No pude entender. Hasta pronto.")
    
    print(f"✅ TRANSCRIPCIÓN: {user_text}")
    
    # Detectar despedida
    despedidas = ["adiós", "adios", "gracias", "hasta luego", "bye", "chao", "no nada más", "no nada mas", "eso es todo"]
    if any(d in user_text.lower() for d in despedidas):
        return _hangup_response("Gracias por llamar. Hasta pronto.")
    
    # 2. Generar respuesta con IA
    print("🤖 Generando respuesta con GPT-4...")
    response = await generate_ai_response(
        user_message=user_text,
        company_id="demo_company"
    )
    
    ai_text = response.message
    # Limpiar respuesta para evitar repeticiones
    ai_text = ai_text.replace("¿Hay algo más en lo que pueda ayudarte?", "")
    ai_text = ai_text.replace("¿Hay algo más en que pueda ayudarte?", "")
    ai_text = ai_text.replace("¿Hay algo más en lo que te pueda ayudar?", "")
    ai_text = ai_text.strip()
    
    print(f"✅ RESPUESTA IA: {ai_text}")
    
    # 3. Responder y continuar conversación
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="es-MX" voice="Polly.Mia">{ai_text}</Say>
    <Pause length="1"/>
    <Say language="es-MX" voice="Polly.Mia">¿Algo más?</Say>
    <Record 
        maxLength="20" 
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


@router.post("/voice/status")
async def recording_status(request: Request):
    form_data = await request.form()
    status = form_data.get("RecordingStatus", "")
    print(f"📊 ESTADO GRABACIÓN: {status}")
    return {"status": "ok"}


def _hangup_response(message: str) -> PlainTextResponse:
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="es-MX" voice="Polly.Mia">{message}</Say>
    <Hangup/>
</Response>"""
    return PlainTextResponse(content=twiml, media_type="application/xml")