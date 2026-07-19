from fastapi import APIRouter, Depends, HTTPException, status
from app.config import Settings, settings
from app.dependencies import get_settings
from app.services.document_service import DocumentService
from app.services.chroma_service import ChromaService
from app.models.response_models import ErrorResponse
from typing import List, Dict, Any

router = APIRouter(prefix="/api")

def get_document_service(settings: Settings = Depends(get_settings)) -> DocumentService:
    return DocumentService(settings)

def get_chroma_service(settings: Settings = Depends(get_settings)) -> ChromaService:
    return ChromaService(settings)

@router.get(
    "/documents",
    summary="List Uploaded Documents",
    description="Returns a list of all indexed documents in the knowledge base along with their status and properties."
)
async def list_documents(doc_service: DocumentService = Depends(get_document_service)):
    docs = doc_service.get_all_active_documents()
    return {
        "total_documents": len(docs),
        "documents": docs
    }

@router.get(
    "/documents/{document_id}",
    summary="Get Document Metadata Details",
    description="Returns the complete registered metadata properties for a single document ID."
)
async def get_document_details(document_id: str, doc_service: DocumentService = Depends(get_document_service)):
    doc = doc_service.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
    return doc

@router.delete(
    "/documents/{document_id}",
    summary="Delete Document",
    description="Deletes a document from the system, removing its stored PDF file, registry metadata, and all ChromaDB vector embeddings."
)
async def delete_document(
    document_id: str,
    doc_service: DocumentService = Depends(get_document_service),
    chroma_service: ChromaService = Depends(get_chroma_service)
):
    return doc_service.delete_document(document_id, chroma_service)
