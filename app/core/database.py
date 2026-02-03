"""
Configuración de la base de datos PostgreSQL con SQLAlchemy async.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


# Convertir URL de Railway a formato asyncpg
database_url = settings.database_url
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    database_url,
    echo=settings.debug,
    poolclass=NullPool,
)

# Session factory
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Base para todos los modelos
class Base(DeclarativeBase):
    """Clase base para todos los modelos SQLAlchemy."""
    pass


async def get_db() -> AsyncSession:
    """
    Dependency que provee una sesión de base de datos.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Inicializa la base de datos creando todas las tablas.
    """
    async with engine.begin() as conn:
        # Importar todos los modelos para que SQLAlchemy los registre
        from app.models import Company, User, Conversation, Message, CompanyConfig, Feedback  # noqa
        
        # Crear tablas siempre
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Cierra las conexiones de la base de datos."""
    await engine.dispose()
