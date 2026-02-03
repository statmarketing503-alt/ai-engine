"""
AI Engine - Motor de IA Multicanal
==================================

Aplicación principal FastAPI.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import time

from app.core.config import settings
from app.core.database import init_db, close_db


# Configurar logging estructurado
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.is_production 
            else structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja el ciclo de vida de la aplicación.
    """
    logger.info("🚀 Iniciando AI Engine", env=settings.app_env)
    await init_db()
    logger.info("✅ Base de datos conectada")
    
    yield
    
    logger.info("🛑 Cerrando AI Engine")
    await close_db()
    logger.info("✅ Conexiones cerradas")


app = FastAPI(
    title=settings.app_name,
    description="""
    ## Motor de IA Multicanal
    
    API para gestionar conversaciones inteligentes a través de múltiples canales:
    - 📱 WhatsApp
    - 💬 Messenger
    - 📞 Llamadas de voz
    
    ### Características
    - Multi-empresa (multi-tenant)
    - Memoria de conversaciones
    - RAG (Retrieval Augmented Generation)
    - Feedback loop para aprendizaje
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    if settings.is_development or process_time > 1000:
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(process_time, 2)
        )
    
    response.headers["X-Process-Time"] = str(round(process_time, 2))
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Error interno del servidor",
            "error": str(exc) if settings.is_development else None
        }
    )


# ===========================================
# ENDPOINTS BASE
# ===========================================

@app.get("/", tags=["Health"])
async def root():
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs" if settings.is_development else "disabled"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.app_env,
        "checks": {"api": "ok"}
    }


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    from app.core.database import engine
    
    checks = {"database": "unknown", "qdrant": "unknown"}
    
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
    
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        client.get_collections()
        checks["qdrant"] = "ok"
    except Exception as e:
        checks["qdrant"] = f"error: {str(e)}"
    
    all_ok = all(v == "ok" for v in checks.values())
    
    return {
        "status": "ready" if all_ok else "not_ready",
        "checks": checks
    }


# ===========================================
# INCLUIR ROUTERS
# ===========================================

from app.api.webhooks.whatsapp import router as whatsapp_router
app.include_router(whatsapp_router, prefix="/webhook", tags=["Webhooks"])


# ===========================================
# ENDPOINTS DE PRUEBA Y SETUP
# ===========================================

@app.post("/test/ai", tags=["Test"])
async def test_ai(message: str = "Hola"):
    from app.services.ai_service import generate_ai_response
    response = await generate_ai_response(message)
    return {"response": response.message, "status": "ok"}


@app.post("/setup/demo-company", tags=["Setup"])
async def create_demo_company():
    from app.core.database import async_session_maker
    from app.models import Company, CompanyConfig
    from sqlalchemy import select
    import secrets
    
    async with async_session_maker() as session:
        query = select(Company).where(Company.id == "demo_company")
        result = await session.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            return {"message": "Demo company already exists", "api_key": existing.api_key}
        
        company = Company(
            id="demo_company",
            name="Empresa Demo",
            slug="demo",
            api_key=f"aie_{secrets.token_hex(24)}",
            industry="servicios",
            is_active=True
        )
        session.add(company)
        
        config = CompanyConfig(
            company_id="demo_company",
            agent_name="Asistente Demo",
            tone="amigable",
            greeting_message="¡Hola! Soy el asistente de Empresa Demo. ¿En qué puedo ayudarte?",
            primary_cta="agendar_cita"
        )
        session.add(config)
        
        await session.commit()
        
        return {
            "message": "Demo company created",
            "company_id": company.id,
            "api_key": company.api_key
        }


# ===========================================
# KNOWLEDGE BASE
# ===========================================

@app.post("/knowledge/add", tags=["Knowledge Base"])
async def add_knowledge_document(
    company_id: str = "demo_company",
    title: str = "Documento",
    content: str = "Contenido del documento"
):
    from app.services.rag_service import add_document
    
    doc_id = await add_document(
        company_id=company_id,
        content=content,
        metadata={"title": title}
    )
    
    return {
        "message": "Document added",
        "doc_id": doc_id,
        "company_id": company_id
    }


@app.post("/knowledge/search", tags=["Knowledge Base"])
async def search_knowledge(
    company_id: str = "demo_company",
    query: str = "información"
):
    from app.services.rag_service import search_documents
    
    results = await search_documents(company_id, query, limit=5)
    
    return {
        "query": query,
        "results": results,
        "count": len(results)
    }


@app.delete("/knowledge/clear", tags=["Knowledge Base"])
async def clear_knowledge(company_id: str = "demo_company"):
    """Borra todos los documentos de una empresa."""
    from qdrant_client import QdrantClient
    from app.core.config import settings
    
    try:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        collection_name = f"company_{company_id}_docs"
        
        # Verificar si existe
        collections = client.get_collections()
        exists = any(c.name == collection_name for c in collections.collections)
        
        if exists:
            client.delete_collection(collection_name)
            return {"message": f"Collection {collection_name} deleted", "company_id": company_id}
        else:
            return {"message": "Collection not found", "company_id": company_id}
    except Exception as e:
        return {"error": str(e)}


# ===========================================
# FEEDBACK Y MÉTRICAS
# ===========================================

@app.post("/feedback/rate", tags=["Feedback"])
async def rate_message(
    message_id: str,
    rating: int = 5,
    comment: str = None
):
    from app.services.feedback_service import save_feedback
    
    result = await save_feedback(
        message_id=message_id,
        rating=rating,
        comment=comment
    )
    return result


@app.get("/metrics/{company_id}", tags=["Metrics"])
async def get_metrics(company_id: str = "demo_company"):
    from app.services.feedback_service import get_conversation_metrics
    
    return await get_conversation_metrics(company_id)


@app.get("/metrics/{company_id}/funnel", tags=["Metrics"])
async def get_funnel(company_id: str = "demo_company"):
    from app.services.feedback_service import get_lead_funnel
    
    return await get_lead_funnel(company_id)


@app.get("/metrics/{company_id}/escalations", tags=["Metrics"])
async def get_escalations(company_id: str = "demo_company"):
    from app.services.feedback_service import detect_escalation_patterns
    
    return await detect_escalation_patterns(company_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development
    )