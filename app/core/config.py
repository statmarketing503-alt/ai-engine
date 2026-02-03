"""
Configuración central de la aplicación.
Carga variables de entorno y proporciona configuración tipada.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """
    Configuración de la aplicación.
    Los valores se cargan desde variables de entorno o archivo .env
    """
    
    # --- Aplicación ---
    app_name: str = Field(default="AI-Engine", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")
    
    # --- Base de Datos ---
    database_url: str = Field(
        default="postgresql+asyncpg://aiengine:devpassword123@localhost:5432/aiengine",
        alias="DATABASE_URL"
    )
    
    # --- Qdrant ---
    qdrant_host: str = Field(default="localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    qdrant_url: str | None = Field(default=None, alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    
    # --- OpenAI ---
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", 
        alias="OPENAI_EMBEDDING_MODEL"
    )
    
    # --- Twilio ---
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_whatsapp_number: str = Field(default="", alias="TWILIO_WHATSAPP_NUMBER")
    twilio_phone_number: str = Field(default="", alias="TWILIO_PHONE_NUMBER")
    
    # --- Meta/Facebook ---
    meta_app_id: str = Field(default="", alias="META_APP_ID")
    meta_app_secret: str = Field(default="", alias="META_APP_SECRET")
    meta_page_access_token: str = Field(default="", alias="META_PAGE_ACCESS_TOKEN")
    meta_verify_token: str = Field(default="", alias="META_VERIFY_TOKEN")
    
    # --- ElevenLabs ---
    elevenlabs_api_key: str = Field(default="", alias="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: str = Field(
        default="21m00Tcm4TlvDq8ikWAM", 
        alias="ELEVENLABS_VOICE_ID"
    )
    
    # --- CORS ---
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        alias="CORS_ORIGINS"
    )
    
    # --- Logging ---
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
    
    @property
    def is_development(self) -> bool:
        return self.app_env == "development"
    
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna instancia cacheada de Settings.
    Usar esta función en lugar de instanciar Settings directamente.
    """
    return Settings()


# Instancia global para importar fácilmente
settings = get_settings()
