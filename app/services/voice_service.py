"""
Servicio de Voz - Text-to-Speech con ElevenLabs y Speech-to-Text con Whisper.
"""

import openai
import httpx
import structlog
from typing import Optional
import base64

from app.core.config import settings

logger = structlog.get_logger()

# Cliente OpenAI para Whisper
openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)


async def speech_to_text(audio_url: str) -> Optional[str]:
    """
    Convierte audio a texto usando OpenAI Whisper.
    
    Args:
        audio_url: URL del archivo de audio (de Twilio)
    
    Returns:
        Texto transcrito o None si falla
    """
    try:
        # Descargar audio de Twilio
        async with httpx.AsyncClient() as client:
            response = await client.get(
                audio_url,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token)
            )
            audio_data = response.content
        
        # Crear archivo temporal en memoria
        audio_file = ("audio.wav", audio_data, "audio/wav")
        
        # Transcribir con Whisper
        transcript = await openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="es"  # Detecta automáticamente, pero priorizamos español
        )
        
        logger.info("speech_to_text_success", text_preview=transcript.text[:50])
        return transcript.text
        
    except Exception as e:
        logger.error("speech_to_text_error", error=str(e))
        return None


async def text_to_speech(text: str, voice_id: str = None) -> Optional[bytes]:
    """
    Convierte texto a audio usando ElevenLabs.
    
    Args:
        text: Texto a convertir
        voice_id: ID de la voz (opcional, usa default)
    
    Returns:
        Audio en bytes (MP3) o None si falla
    """
    if not settings.elevenlabs_api_key:
        logger.warning("elevenlabs_not_configured")
        return None
    
    voice_id = voice_id or settings.elevenlabs_voice_id
    
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": settings.elevenlabs_api_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                logger.info("text_to_speech_success", text_preview=text[:50])
                return response.content
            else:
                logger.error(
                    "text_to_speech_error", 
                    status=response.status_code,
                    response=response.text
                )
                return None
                
    except Exception as e:
        logger.error("text_to_speech_error", error=str(e))
        return None


async def text_to_speech_url(text: str, voice_id: str = None) -> Optional[str]:
    """
    Convierte texto a audio y retorna URL base64 para Twilio.
    
    Twilio puede reproducir audio desde una URL o desde datos base64.
    """
    audio_bytes = await text_to_speech(text, voice_id)
    
    if audio_bytes:
        # Convertir a base64 data URL
        b64_audio = base64.b64encode(audio_bytes).decode('utf-8')
        return f"data:audio/mpeg;base64,{b64_audio}"
    
    return None