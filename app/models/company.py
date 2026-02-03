"""
Modelo Company - Empresas/Clientes del sistema.

Cada empresa que usa el AI Engine tiene su propia configuración,
usuarios, y conversaciones aisladas (multi-tenant).
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Company(Base):
    """
    Representa una empresa cliente del sistema.
    
    Ejemplo: "Restaurante El Buen Sabor", "Clínica Dental Sonrisa"
    """
    __tablename__ = "companies"
    
    # === Identificación ===
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, comment="Nombre de la empresa")
    slug = Column(String(100), unique=True, comment="Identificador URL-friendly")
    
    # === Autenticación ===
    api_key = Column(String(100), unique=True, nullable=False, comment="API Key para autenticación")
    
    # === Información del negocio ===
    industry = Column(String(100), comment="Industria: restaurante, clinica, ecommerce, etc.")
    description = Column(Text, comment="Descripción del negocio")
    website = Column(String(255), comment="Sitio web")
    phone = Column(String(50), comment="Teléfono principal")
    email = Column(String(255), comment="Email de contacto")
    
    # === Configuración de canales ===
    whatsapp_number = Column(String(50), comment="Número de WhatsApp Business")
    messenger_page_id = Column(String(100), comment="ID de página de Facebook")
    
    # === Estado ===
    is_active = Column(Boolean, default=True, comment="Si la empresa está activa")
    
    # === Timestamps ===
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # === Relaciones ===
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    config = relationship("CompanyConfig", back_populates="company", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Company {self.name} ({self.id[:8]})>"