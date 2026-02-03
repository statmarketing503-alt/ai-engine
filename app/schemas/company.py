"""
Esquemas para empresas.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CompanyCreate(BaseModel):
    """Para crear una nueva empresa."""
    name: str = Field(..., min_length=2, max_length=255)
    industry: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp_number: Optional[str] = None
    messenger_page_id: Optional[str] = None


class CompanyResponse(BaseModel):
    """Respuesta con datos de empresa."""
    id: str
    name: str
    slug: Optional[str]
    api_key: str
    industry: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class CompanyConfigUpdate(BaseModel):
    """Para actualizar configuración del agente."""
    agent_name: Optional[str] = None
    tone: Optional[str] = None
    language: Optional[str] = None
    greeting_message: Optional[str] = None
    fallback_message: Optional[str] = None
    primary_cta: Optional[str] = None
    escalation_keywords: Optional[list] = None
    business_hours: Optional[dict] = None
    custom_instructions: Optional[str] = None