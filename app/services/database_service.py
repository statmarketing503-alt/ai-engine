"""
Servicio de Base de Datos - Gestiona usuarios, conversaciones y mensajes.
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models import Company, User, Conversation, Message, CompanyConfig
from app.core.database import async_session_maker

logger = structlog.get_logger()


async def get_or_create_user(
    company_id: str,
    channel: str,
    channel_user_id: str
) -> User:
    """
    Obtiene un usuario existente o crea uno nuevo.
    """
    async with async_session_maker() as session:
        # Buscar usuario por canal
        if channel == "whatsapp":
            query = select(User).where(
                and_(User.company_id == company_id, User.whatsapp_id == channel_user_id)
            )
        elif channel == "messenger":
            query = select(User).where(
                and_(User.company_id == company_id, User.messenger_id == channel_user_id)
            )
        else:
            query = select(User).where(
                and_(User.company_id == company_id, User.phone == channel_user_id)
            )
        
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            # Actualizar última interacción
            user.last_interaction = datetime.utcnow()
            await session.commit()
            logger.info("user_found", user_id=user.id)
            return user
        
        # Crear nuevo usuario
        user = User(
            company_id=company_id,
            whatsapp_id=channel_user_id if channel == "whatsapp" else None,
            messenger_id=channel_user_id if channel == "messenger" else None,
            phone=channel_user_id if channel == "voice" else None,
            lead_status="nuevo",
            last_interaction=datetime.utcnow()
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        logger.info("user_created", user_id=user.id)
        return user


async def get_or_create_conversation(
    user_id: str,
    channel: str,
    timeout_minutes: int = 30
) -> Conversation:
    """
    Obtiene conversación activa o crea una nueva.
    Una conversación se considera activa si tuvo actividad en los últimos N minutos.
    """
    async with async_session_maker() as session:
        # Buscar conversación activa reciente
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        
        query = select(Conversation).where(
            and_(
                Conversation.user_id == user_id,
                Conversation.channel == channel,
                Conversation.status == "active",
                Conversation.last_message_at >= cutoff_time
            )
        )
        
        result = await session.execute(query)
        conversation = result.scalar_one_or_none()
        
        if conversation:
            logger.info("conversation_found", conversation_id=conversation.id)
            return conversation
        
        # Crear nueva conversación
        conversation = Conversation(
            user_id=user_id,
            channel=channel,
            status="active",
            started_at=datetime.utcnow(),
            last_message_at=datetime.utcnow()
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)
        
        logger.info("conversation_created", conversation_id=conversation.id)
        return conversation


async def save_message(
    conversation_id: str,
    role: str,
    content: str,
    response_time_ms: int = None,
    tokens_used: int = None,
    model_used: str = None
) -> Message:
    """
    Guarda un mensaje en la conversación.
    """
    async with async_session_maker() as session:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            response_time_ms=response_time_ms,
            tokens_used=tokens_used,
            model_used=model_used,
            created_at=datetime.utcnow()
        )
        session.add(message)
        
        # Actualizar last_message_at en la conversación
        query = select(Conversation).where(Conversation.id == conversation_id)
        result = await session.execute(query)
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.last_message_at = datetime.utcnow()
        
        await session.commit()
        await session.refresh(message)
        
        logger.info("message_saved", message_id=message.id, role=role)
        return message


async def get_conversation_history(
    conversation_id: str,
    limit: int = 10
) -> list:
    """
    Obtiene el historial de mensajes de una conversación.
    Retorna en formato listo para OpenAI.
    """
    async with async_session_maker() as session:
        query = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).limit(limit)
        
        result = await session.execute(query)
        messages = result.scalars().all()
        
        # Convertir a formato OpenAI (orden cronológico)
        history = []
        for msg in reversed(messages):
            history.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return history


async def get_company_config(company_id: str) -> Optional[CompanyConfig]:
    """
    Obtiene la configuración del agente para una empresa.
    """
    async with async_session_maker() as session:
        query = select(CompanyConfig).where(CompanyConfig.company_id == company_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()


async def update_user_lead_status(user_id: str, status: str):
    """
    Actualiza el estado del lead.
    """
    async with async_session_maker() as session:
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            user.lead_status = status
            user.updated_at = datetime.utcnow()
            await session.commit()
            logger.info("lead_status_updated", user_id=user_id, status=status)