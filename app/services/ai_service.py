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
    
    # System prompt restrictivo
    if not system_prompt:
        system_prompt = f"""Eres el asistente virtual oficial de {company_name}. Tu ÚNICO propósito es ayudar a los clientes con información sobre la empresa, sus servicios y productos.

REGLAS ESTRICTAS:
1. SOLO responde preguntas relacionadas con {company_name}, sus servicios, productos, precios, horarios y citas.
2. Si el usuario pregunta algo NO relacionado con la empresa (cultura general, otros temas, etc.), responde amablemente: "Soy el asistente de {company_name} y solo puedo ayudarte con información sobre nuestros servicios. ¿Te gustaría saber sobre nuestros precios, horarios o agendar una cita?"
3. Responde de forma concisa (máximo 2-3 oraciones).
4. Sé amable y profesional.
5. Si no tienes información específica, ofrece conectar con un asesor humano.
6. Si el usuario quiere agendar cita, pregunta día y hora preferidos.
7. Si detectas frustración o quejas, ofrece escalar a un humano inmediatamente.
8. USA SIEMPRE la información de la empresa proporcionada abajo cuando esté disponible.
9. NUNCA inventes información que no esté en el contexto de la empresa.
10. Recuerda el contexto de la conversación y usa el nombre del cliente si lo mencionó.

OBJETIVO PRINCIPAL: Guiar al cliente hacia agendar una cita o resolver su consulta sobre la empresa."""

    # Agregar contexto RAG al system prompt
    if rag_context:
        system_prompt += f"\n\n{rag_context}"
    else:
        system_prompt += f"\n\nNOTA: No hay información específica cargada sobre la empresa aún. Ofrece conectar con un asesor para más detalles."

    # Construir mensajes
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Agregar historial si existe (para memoria de conversación)
    if conversation_history:
        messages.extend(conversation_history)
    
    # Agregar mensaje actual
    messages.append({"role": "user", "content": user_message})
    
    try:
        logger.info(
            "calling_openai", 
            message_preview=user_message[:50], 
            has_rag=bool(rag_context),
            history_length=len(conversation_history) if conversation_history else 0
        )
        
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
        if any(word in user_message.lower() for word in ["humano", "persona", "asesor", "queja", "supervisor", "gerente"]):
            action = "escalate"
        
        # Detectar intención de cita
        lead_status = "interesado"
        if any(word in user_message.lower() for word in ["cita", "agendar", "reservar", "apartar", "programar"]):
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