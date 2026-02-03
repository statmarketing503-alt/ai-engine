"""
Servicio de IA - Genera respuestas usando OpenAI con soporte RAG.
"""

import openai
from typing import Optional
import structlog

from app.core.config import settings
from app.schemas.message import AgentResponse
from app.services.rag_service import get_context_for_query

logger = structlog.get_logger()

# Configurar cliente de OpenAI
client = openai.AsyncOpenAI(api_key=settings.openai_api_key)


async def generate_ai_response(
    user_message: str,
    conversation_history: list = None,
    system_prompt: str = None,
    company_name: str = "la empresa",
    company_id: str = None
) -> AgentResponse:
    """
    Genera una respuesta usando OpenAI GPT-4 con RAG.
    """
    
    # Buscar contexto RAG si hay company_id
    rag_context = ""
    if company_id:
        try:
            rag_context = await get_context_for_query(company_id, user_message)
            if rag_context:
                logger.info("rag_context_found", company_id=company_id)
        except Exception as e:
            logger.warning("rag_search_failed", error=str(e))
    
    # System prompt por defecto si no se proporciona
    if not system_prompt:
        system_prompt = f"""Eres un asistente virtual amigable y profesional de {company_name}.

REGLAS:
1. Responde de forma concisa (máximo 2-3 oraciones)
2. Sé amable y servicial
3. Si no sabes algo, ofrece conectar con un humano
4. Si el usuario quiere agendar cita, pregunta día y hora
5. Si detectas frustración, ofrece escalar a un humano
6. USA LA INFORMACIÓN DE LA EMPRESA cuando esté disponible

OBJETIVO: Ayudar al cliente y guiarlo hacia agendar una cita o resolver su consulta."""

    # Agregar contexto RAG al system prompt
    if rag_context:
        system_prompt += f"\n\n{rag_context}"

    # Construir mensajes
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Agregar historial si existe
    if conversation_history:
        messages.extend(conversation_history)
    
    # Agregar mensaje actual
    messages.append({"role": "user", "content": user_message})
    
    try:
        logger.info("calling_openai", message_preview=user_message[:50], has_rag=bool(rag_context))
        
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )
        
        ai_message = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        logger.info(
            "openai_response",
            tokens=tokens_used,
            response_preview=ai_message[:50]
        )
        
        # Detectar si debe escalar
        action = None
        if any(word in user_message.lower() for word in ["humano", "persona", "asesor", "queja"]):
            action = "escalate"
        
        # Detectar intención de cita
        lead_status = "interesado"
        if any(word in user_message.lower() for word in ["cita", "agendar", "reservar"]):
            lead_status = "caliente"
        
        return AgentResponse(
            message=ai_message,
            action=action,
            lead_status=lead_status,
            confidence=0.9
        )
        
    except openai.APIError as e:
        logger.error("openai_api_error", error=str(e))
        return AgentResponse(
            message="Disculpa, tengo problemas técnicos. ¿Podrías intentar de nuevo?",
            action=None,
            lead_status=None,
            confidence=0.0
        )
    except Exception as e:
        logger.error("ai_service_error", error=str(e))
        return AgentResponse(
            message="Ocurrió un error. Por favor intenta de nuevo.",
            action=None,
            lead_status=None,
            confidence=0.0
        )