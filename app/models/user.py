"""
Modelo User - Contactos/Leads de cada empresa.

Representa a las personas que interactúan con el agente IA.
Guarda información de contacto, estado del lead, y preferencias.
"""

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class User(Base):
    """
    Representa un contacto/lead de una empresa.
    """
    __tablename__ = "users"
    
    # === Identificación ===
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    
    # === Identificadores por canal ===
    whatsapp_id = Column(String(50), unique=True, nullable=True)
    messenger_id = Column(String(100), unique=True, nullable=True)
    phone = Column(String(50))
    email = Column(String(255))
    
    # === Información personal ===
    name = Column(String(255))
    
    # === Lead Scoring ===
    lead_status = Column(String(50), default="nuevo")
    lead_score = Column(Integer, default=0)
    
    # === Memoria del usuario ===
    preferences = Column(JSON, default=dict)
    objections = Column(JSON, default=list)
    notes = Column(Text)
    
    # === Timestamps ===
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_interaction = Column(DateTime)
    
    # === Relaciones ===
    company = relationship("Company", back_populates="users")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.name or self.whatsapp_id or self.id[:8]}>"