"""
Modelo de Conversación y Mensajes.
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Conversation(Base):
    """
    Una conversación es una sesión de chat con un usuario.
    """
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    channel = Column(String, nullable=False)  # whatsapp, messenger, voice, web
    status = Column(String, default="active")  # active, closed, escalated
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    last_message_at = Column(DateTime, default=datetime.utcnow)
    extra_data = Column(JSON, default=dict)
    
    # Relaciones
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")


class Message(Base):
    """
    Un mensaje individual en una conversación.
    """
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    model_used = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relación
    conversation = relationship("Conversation", back_populates="messages")


class Feedback(Base):
    """
    Feedback sobre respuestas del agente.
    Permite evaluar y mejorar el sistema.
    """
    __tablename__ = "feedback"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String, ForeignKey("messages.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    feedback_type = Column(String, default="user")  # user, supervisor
    comment = Column(Text, nullable=True)
    corrected_response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relación
    message = relationship("Message", backref="feedback")