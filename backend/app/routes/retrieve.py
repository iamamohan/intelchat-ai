from fastapi import APIRouter, Depends, HTTPException, status
from app.config import Settings
from app.dependencies import get_settings
from app.services.retrieval_service import RetrievalService
from app.models.response_models import RetrievalRequest, RetrievalResponse, ErrorResponse

router = APIRouter(prefix="/api")

def get_retrieval_service(settings: Settings = Depends(get_settings)) -> RetrievalService:
    """Dependency provider for the retrieval service."""
    return RetrievalService(settings)

@router.post(
    "/retrieve",
    response_model=RetrievalResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation failed: empty query"},
        404: {"model": ErrorResponse, "description": "No documents found or collection is empty"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Semantic Retrieval Query",
    description="Submits a query to generate an embedding, query the ChromaDB vector database, and return the Top-K most relevant chunks with metadata and similarity scores."
)
async def retrieve(
    payload: RetrievalRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service)
) -> RetrievalResponse:
    """Handles semantic search queries and returns the matching document chunks."""
    return await retrieval_service.retrieve_relevant_chunks(payload.query)
