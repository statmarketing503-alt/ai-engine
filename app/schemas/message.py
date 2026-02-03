"""
Esquemas para mensajes normalizados.

Todos los canales (WhatsApp, Messenger, Voice) se normalizan
a este formato estándar antes de procesarse.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class NormalizedMessage(BaseModel):
    """
    Formato estándar para mensajes de cualquier canal.
    Esta es la 'lingua franca' del sistema.
    """
    company_id: str = Field(..., description="ID de la empresa")
    user_id: str = Field(..., description="ID único del usuario en ese canal")
    channel: Literal["whatsapp", "messenger", "voice", "web"] = Field(..., description="Canal de origen")
    message: str = Field(..., description="Contenido del mensaje (texto)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = Field(default={}, description="Datos extra del canal")
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_id": "comp_123",
                "user_id": "+50312345678",
                "channel": "whatsapp",
                "message": "Hola, quiero información sobre sus servicios",
                "timestamp": "2024-01-15T10:30:00Z",
                "metadata": {"twilio_sid": "SM123"}
            }
        }


class AgentResponse(BaseModel):
    """
    Respuesta generada por el agente IA.
    """
    message: str = Field(..., description="Texto de respuesta")
    action: Optional[str] = Field(None, description="Acción: escalate, schedule, etc.")
    lead_status: Optional[str] = Field(None, description="Nuevo estado del lead")
    confidence: Optional[float] = Field(None, description="Confianza de la respuesta 0-1")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "¡Hola! Claro, con gusto te ayudo. ¿Qué servicio te interesa?",
                "action": None,
                "lead_status": "interesado",
                "confidence": 0.95
            }
        }


class WebhookResponse(BaseModel):
    """
    Respuesta estándar para webhooks.
    """
    status: str = Field(default="ok")
    message_id: Optional[str] = None
    error: Optional[str] = None