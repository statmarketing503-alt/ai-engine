"""
Seguridad y autenticación.
Maneja API keys y validación de empresas.
"""

from fastapi import HTTPException, Security, Depends, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.core.database import get_db


# Header para API Key
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="API Key de la empresa para autenticación"
)


class CompanyContext:
    """
    Contexto de la empresa autenticada.
    Se usa para pasar información de la empresa a través de las requests.
    """
    def __init__(self, company_id: str, name: str, is_active: bool = True):
        self.company_id = company_id
        self.name = name
        self.is_active = is_active
    
    def __repr__(self):
        return f"<CompanyContext {self.name} ({self.company_id})>"


async def get_company_from_api_key(
    api_key: Optional[str] = Security(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> CompanyContext:
    """
    Valida API key y retorna contexto de la empresa.
    
    Uso:
        @router.post("/endpoint")
        async def endpoint(company: CompanyContext = Depends(get_company_from_api_key)):
            print(company.company_id)
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key requerida. Incluir header 'X-API-Key'",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Buscar empresa por API key
    from app.models.company import Company
    
    query = select(Company).where(Company.api_key == api_key)
    result = await db.execute(query)
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key inválida o empresa no encontrada"
        )
    
    if not company.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Empresa desactivada. Contactar soporte."
        )
    
    return CompanyContext(
        company_id=company.id,
        name=company.name,
        is_active=company.is_active
    )


async def get_optional_company(
    api_key: Optional[str] = Security(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> Optional[CompanyContext]:
    """
    Similar a get_company_from_api_key pero no falla si no hay API key.
    Útil para endpoints que pueden funcionar con o sin autenticación.
    """
    if not api_key:
        return None
    
    try:
        return await get_company_from_api_key(api_key, db)
    except HTTPException:
        return None


def generate_api_key() -> str:
    """
    Genera una nueva API key única.
    Formato: aie_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
    """
    import secrets
    return f"aie_{secrets.token_hex(24)}"
