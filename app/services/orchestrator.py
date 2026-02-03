"""
Orquestador - Coordina el procesamiento de mensajes con memoria y RAG.
"""

from datetime import datetime
import time
import structlog

from app.schemas.message import NormalizedMessage, AgentResponse
from app.services.ai_service import generate_ai_response
from app.services.database_service import (
    get_or_create_user,
    get_or_create_conversation,
    save_message,
    get_conversation_history,
    update_user_lead_status
)

logger = structlog.get_logger()


async def process_message(message: NormalizedMessage) -> AgentResponse:
    """
    Procesa un mensaje con memoria, contexto y RAG.
    """
    start_time = time.time()
    
    logger.info(
        "processing_message",
        company_id=message.company_id,
        channel=message.channel,
        user_id=message.user_id,
        message_preview=message.message[:50]
    )
    
    try:
        # 1. Obtener o crear usuario
        user = await get_or_create_user(
            company_id=message.company_id,
            channel=message.channel,
            channel_user_id=message.user_id
        )
        
        # 2. Obtener o crear conversación
        conversation = await get_or_create_conversation(
            user_id=user.id,
            channel=message.channel
        )
        
        # 3. Guardar mensaje del usuario
        await save_message(
            conversation_id=conversation.id,
            role="user",
            content=message.message
        )
        
        # 4. Obtener historial de conversación
        history = await get_conversation_history(
            conversation_id=conversation.id,
            limit=10
        )
        
        # Remover el último mensaje (el actual) del historial
        if history and history[-1]["content"] == message.message:
            history = history[:-1]
        
        logger.info("conversation_context", history_length=len(history))
        
        # 5. Generar respuesta con IA + RAG
        response = await generate_ai_response(
            user_message=message.message,
            conversation_history=history,
            company_name="nuestra empresa",
            company_id=message.company_id  # Para RAG
        )
        
        # Calcular tiempo de respuesta
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # 6. Guardar respuesta del asistente
        await save_message(
            conversation_id=conversation.id,
            role="assistant",
            content=response.message,
            response_time_ms=response_time_ms
        )
        
        # 7. Actualizar estado del lead si cambió
        if response.lead_status:
            await update_user_lead_status(user.id, response.lead_status)
        
        logger.info(
            "response_generated",
            response_preview=response.message[:50],
            response_time_ms=response_time_ms,
            lead_status=response.lead_status
        )
        
        return response
        
    except Exception as e:
        logger.error("process_message_error", error=str(e))
        
        return AgentResponse(
            message="Disculpa, tuve un problema. ¿Podrías intentar de nuevo?",
            action=None,
            lead_status=None,
            confidence=0.0
        )