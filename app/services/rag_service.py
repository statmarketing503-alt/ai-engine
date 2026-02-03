"""
Servicio RAG - Retrieval Augmented Generation con Qdrant.

Permite que el agente responda usando documentos de la empresa.
"""

import openai
from qdrant_client import QdrantClient
from qdrant_client.http import models
from typing import List
import structlog
import hashlib

from app.core.config import settings

logger = structlog.get_logger()

# Cliente de OpenAI para embeddings
openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

# Cliente de Qdrant
qdrant_client = QdrantClient(
    host=settings.qdrant_host,
    port=settings.qdrant_port
)

# Dimensión de embeddings de OpenAI text-embedding-3-small
EMBEDDING_DIMENSION = 1536


def get_collection_name(company_id: str) -> str:
    """Genera nombre de colección para una empresa."""
    return f"company_{company_id}_docs"


def generate_numeric_id(content: str) -> int:
    """Genera un ID numérico único basado en el contenido."""
    hash_hex = hashlib.md5(content.encode()).hexdigest()
    # Tomar los primeros 15 caracteres hex y convertir a int
    return int(hash_hex[:15], 16)


async def create_embedding(text: str) -> List[float]:
    """
    Crea embedding de un texto usando OpenAI.
    """
    try:
        response = await openai_client.embeddings.create(
            model=settings.openai_embedding_model,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error("embedding_error", error=str(e))
        raise


async def ensure_collection_exists(company_id: str):
    """
    Asegura que existe la colección de Qdrant para una empresa.
    """
    collection_name = get_collection_name(company_id)
    
    try:
        collections = qdrant_client.get_collections()
        exists = any(c.name == collection_name for c in collections.collections)
        
        if not exists:
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=models.Distance.COSINE
                )
            )
            logger.info("collection_created", collection=collection_name)
        
        return collection_name
    except Exception as e:
        logger.error("collection_error", error=str(e))
        raise


async def add_document(
    company_id: str,
    content: str,
    metadata: dict = None,
    doc_id: int = None
) -> int:
    """
    Agrega un documento a la base de conocimiento de una empresa.
    """
    collection_name = await ensure_collection_exists(company_id)
    
    # Generar ID numérico si no se proporciona
    if doc_id is None:
        doc_id = generate_numeric_id(content)
    
    # Crear embedding
    embedding = await create_embedding(content)
    
    logger.info("adding_document", company_id=company_id, doc_id=doc_id, content_preview=content[:50])
    
    # Preparar payload
    payload = {
        "content": content,
        "company_id": company_id,
        **(metadata or {})
    }
    
    # Insertar en Qdrant
    qdrant_client.upsert(
        collection_name=collection_name,
        points=[
            models.PointStruct(
                id=doc_id,
                vector=embedding,
                payload=payload
            )
        ]
    )
    
    logger.info("document_added", company_id=company_id, doc_id=doc_id)
    return doc_id


async def search_documents(
    company_id: str,
    query: str,
    limit: int = 3
) -> List[dict]:
    """
    Busca documentos relevantes para una consulta.
    """
    collection_name = get_collection_name(company_id)
    
    try:
        # Verificar si existe la colección
        collections = qdrant_client.get_collections()
        exists = any(c.name == collection_name for c in collections.collections)
        
        logger.info("searching_documents", company_id=company_id, collection=collection_name, exists=exists)
        
        if not exists:
            logger.info("no_collection_for_company", company_id=company_id)
            return []
        
        # Verificar cuántos puntos hay en la colección
        collection_info = qdrant_client.get_collection(collection_name)
        logger.info("collection_info", points_count=collection_info.points_count)
        
        # Crear embedding de la consulta
        query_embedding = await create_embedding(query)
        
        # Buscar en Qdrant usando search (más compatible)
        search_result = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=limit
        )
        
        logger.info("search_raw_results", count=len(search_result))
        
        # Formatear resultados
        documents = []
        for result in search_result:
            documents.append({
                "content": result.payload.get("content", ""),
                "score": result.score,
                "metadata": {k: v for k, v in result.payload.items() if k != "content"}
            })
        
        logger.info(
            "documents_found",
            company_id=company_id,
            query_preview=query[:50],
            count=len(documents)
        )
        
        return documents
        
    except Exception as e:
        logger.error("search_error", error=str(e))
        return []


async def delete_document(company_id: str, doc_id: int) -> bool:
    """
    Elimina un documento de la base de conocimiento.
    """
    collection_name = get_collection_name(company_id)
    
    try:
        qdrant_client.delete(
            collection_name=collection_name,
            points_selector=models.PointIdsList(points=[doc_id])
        )
        logger.info("document_deleted", company_id=company_id, doc_id=doc_id)
        return True
    except Exception as e:
        logger.error("delete_error", error=str(e))
        return False


async def get_context_for_query(company_id: str, query: str) -> str:
    """
    Obtiene contexto relevante para una consulta.
    Retorna texto formateado listo para incluir en el prompt.
    """
    documents = await search_documents(company_id, query, limit=3)
    
    if not documents:
        return ""
    
    context_parts = ["INFORMACIÓN RELEVANTE DE LA EMPRESA:"]
    for i, doc in enumerate(documents, 1):
        context_parts.append(f"\n[Documento {i}]\n{doc['content']}")
    
    return "\n".join(context_parts)