"""
Query API endpoints for RAG querying
"""
from fastapi import APIRouter, HTTPException
import logging
from app.models.schemas import QueryRequest, QueryResponse
from app.services.agentic_rag import get_agentic_rag

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


@router.post("/", response_model=QueryResponse)
async def query_system(request: QueryRequest):
    """
    Query the RAG system with a user question

    Args:
        request: Query request containing the question

    Returns:
        Query response with answer and citations
    """
    try:
        logger.info(f"Received query: {request.query[:100]}...")

        # Get agentic RAG system
        agentic_rag = get_agentic_rag()

        # Process query
        response = agentic_rag.process_query(request)

        logger.info(f"Query processed successfully. Confidence: {response.confidence:.2f}")

        return response

    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check endpoint

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "Agentic RAG Query Service"
    }
