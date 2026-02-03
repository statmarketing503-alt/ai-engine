"""
Servicio de Feedback - Gestiona calificaciones y métricas.

Permite aprender de las interacciones y mejorar el sistema.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select, func, and_
import structlog

from app.core.database import async_session_maker
from app.models import Message, Conversation, User, Feedback

logger = structlog.get_logger()


async def save_feedback(
    message_id: str,
    rating: int,
    feedback_type: str = "user",
    comment: str = None,
    corrected_response: str = None
) -> dict:
    """
    Guarda feedback para un mensaje específico.
    
    Args:
        message_id: ID del mensaje a calificar
        rating: Calificación (1-5, donde 5 es excelente)
        feedback_type: "user" o "supervisor"
        comment: Comentario opcional
        corrected_response: Respuesta corregida si la original fue mala
    
    Returns:
        Información del feedback guardado
    """
    async with async_session_maker() as session:
        feedback = Feedback(
            message_id=message_id,
            rating=rating,
            feedback_type=feedback_type,
            comment=comment,
            corrected_response=corrected_response,
            created_at=datetime.utcnow()
        )
        session.add(feedback)
        await session.commit()
        await session.refresh(feedback)
        
        logger.info(
            "feedback_saved",
            message_id=message_id,
            rating=rating,
            feedback_type=feedback_type
        )
        
        return {
            "id": feedback.id,
            "message_id": message_id,
            "rating": rating
        }


async def get_conversation_metrics(
    company_id: str,
    days: int = 7
) -> dict:
    """
    Obtiene métricas de conversaciones para una empresa.
    """
    async with async_session_maker() as session:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Contar conversaciones
        conv_query = select(func.count(Conversation.id)).join(
            User, Conversation.user_id == User.id
        ).where(
            and_(
                User.company_id == company_id,
                Conversation.started_at >= cutoff
            )
        )
        conv_result = await session.execute(conv_query)
        total_conversations = conv_result.scalar() or 0
        
        # Contar mensajes
        msg_query = select(func.count(Message.id)).join(
            Conversation, Message.conversation_id == Conversation.id
        ).join(
            User, Conversation.user_id == User.id
        ).where(
            and_(
                User.company_id == company_id,
                Message.created_at >= cutoff
            )
        )
        msg_result = await session.execute(msg_query)
        total_messages = msg_result.scalar() or 0
        
        # Promedio de tiempo de respuesta
        time_query = select(func.avg(Message.response_time_ms)).join(
            Conversation, Message.conversation_id == Conversation.id
        ).join(
            User, Conversation.user_id == User.id
        ).where(
            and_(
                User.company_id == company_id,
                Message.created_at >= cutoff,
                Message.role == "assistant",
                Message.response_time_ms.isnot(None)
            )
        )
        time_result = await session.execute(time_query)
        avg_response_time = time_result.scalar() or 0
        
        # Contar usuarios únicos
        user_query = select(func.count(func.distinct(User.id))).where(
            and_(
                User.company_id == company_id,
                User.last_interaction >= cutoff
            )
        )
        user_result = await session.execute(user_query)
        unique_users = user_result.scalar() or 0
        
        return {
            "period_days": days,
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "unique_users": unique_users,
            "avg_response_time_ms": round(avg_response_time, 2) if avg_response_time else 0,
            "messages_per_conversation": round(total_messages / max(total_conversations, 1), 2)
        }


async def get_lead_funnel(company_id: str) -> dict:
    """
    Obtiene el embudo de leads para una empresa.
    """
    async with async_session_maker() as session:
        # Contar por estado de lead
        query = select(
            User.lead_status,
            func.count(User.id)
        ).where(
            User.company_id == company_id
        ).group_by(User.lead_status)
        
        result = await session.execute(query)
        rows = result.all()
        
        funnel = {
            "nuevo": 0,
            "interesado": 0,
            "caliente": 0,
            "convertido": 0,
            "perdido": 0
        }
        
        for status, count in rows:
            if status in funnel:
                funnel[status] = count
        
        total = sum(funnel.values())
        
        return {
            "funnel": funnel,
            "total_leads": total,
            "conversion_rate": round(funnel["convertido"] / max(total, 1) * 100, 2)
        }


async def get_low_rated_responses(
    company_id: str,
    min_count: int = 5
) -> List[dict]:
    """
    Obtiene respuestas con baja calificación para revisión.
    Útil para identificar áreas de mejora.
    """
    async with async_session_maker() as session:
        query = select(
            Message.content,
            Feedback.rating,
            Feedback.comment,
            Feedback.corrected_response
        ).join(
            Feedback, Message.id == Feedback.message_id
        ).join(
            Conversation, Message.conversation_id == Conversation.id
        ).join(
            User, Conversation.user_id == User.id
        ).where(
            and_(
                User.company_id == company_id,
                Feedback.rating <= 2,
                Message.role == "assistant"
            )
        ).order_by(Feedback.created_at.desc()).limit(min_count)
        
        result = await session.execute(query)
        rows = result.all()
        
        return [
            {
                "response": row[0][:200],
                "rating": row[1],
                "comment": row[2],
                "corrected": row[3]
            }
            for row in rows
        ]


async def detect_escalation_patterns(company_id: str) -> dict:
    """
    Detecta patrones que llevan a escalación.
    """
    async with async_session_maker() as session:
        # Buscar conversaciones escaladas
        escalation_keywords = ["humano", "persona", "asesor", "queja", "supervisor"]
        
        # Esto es simplificado - en producción usarías análisis más sofisticado
        query = select(func.count(Message.id)).join(
            Conversation, Message.conversation_id == Conversation.id
        ).join(
            User, Conversation.user_id == User.id
        ).where(
            and_(
                User.company_id == company_id,
                Message.role == "user"
            )
        )
        
        result = await session.execute(query)
        total_user_messages = result.scalar() or 0
        
        # Contar mensajes con palabras de escalación
        escalation_count = 0
        if total_user_messages > 0:
            for keyword in escalation_keywords:
                kw_query = select(func.count(Message.id)).join(
                    Conversation, Message.conversation_id == Conversation.id
                ).join(
                    User, Conversation.user_id == User.id
                ).where(
                    and_(
                        User.company_id == company_id,
                        Message.role == "user",
                        Message.content.ilike(f"%{keyword}%")
                    )
                )
                kw_result = await session.execute(kw_query)
                escalation_count += kw_result.scalar() or 0
        
        escalation_rate = round(escalation_count / max(total_user_messages, 1) * 100, 2)
        
        return {
            "total_messages": total_user_messages,
            "escalation_requests": escalation_count,
            "escalation_rate_percent": escalation_rate,
            "status": "healthy" if escalation_rate < 10 else "needs_attention"
        }