"""
Modelo CompanyConfig - Configuración del agente IA por empresa.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class CompanyConfig(Base):
    """
    Configuración personalizada del agente para cada empresa.
    """
    __tablename__ = "company_configs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id"), unique=True, nullable=False)
    
    # Personalidad
    agent_name = Column(String(100), default="Asistente")
    tone = Column(String(50), default="profesional")  # profesional, amigable, formal
    language = Column(String(10), default="es")
    
    # Mensajes predefinidos
    greeting_message = Column(Text, default="¡Hola! ¿En qué puedo ayudarte hoy?")
    fallback_message = Column(Text, default="Disculpa, no entendí. ¿Podrías reformular?")
    out_of_hours_message = Column(Text, default="Estamos fuera de horario, te responderemos pronto.")
    escalation_message = Column(Text, default="Te conecto con un asesor humano.")
    
    # Comportamiento
    primary_cta = Column(String(100), default="agendar_cita")
    escalation_keywords = Column(JSON, default=["humano", "persona", "asesor", "queja"])
    qualification_questions = Column(JSON, default=["¿Qué servicio te interesa?"])
    
    # Horarios
    business_hours = Column(JSON, default={
        "lun": ["09:00", "18:00"],
        "mar": ["09:00", "18:00"],
        "mie": ["09:00", "18:00"],
        "jue": ["09:00", "18:00"],
        "vie": ["09:00", "18:00"],
        "sab": ["09:00", "14:00"],
        "dom": None
    })
    timezone = Column(String(50), default="America/El_Salvador")
    
    # Configuración avanzada
    max_response_length = Column(String(20), default="medium")
    use_emojis = Column(Boolean, default=False)
    custom_instructions = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación
    company = relationship("Company", back_populates="config")
    
    def __repr__(self):
        return f"<CompanyConfig for {self.company_id[:8]}>"