from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Any
from app.config import Settings
from app.dependencies import get_settings
from app.services.upload_service import UploadService
from app.models.response_models import StorageResponse, ErrorResponse

router = APIRouter(prefix="/api")

def get_upload_service(settings: Settings = Depends(get_settings)) -> UploadService:
    """Dependency provider for the upload service."""
    return UploadService(settings)

@router.post(
    "/upload",
    response_model=StorageResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation failed: duplicate, not a PDF or missing file"},
        413: {"model": ErrorResponse, "description": "Validation failed: file exceeds the size limit"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Upload PDF File",
    description="Validates, sanitizes, and stores the uploaded PDF document locally, chunking and embedding it, and saving it inside the configured ChromaDB collection."
)
async def upload_file(
    file: UploadFile = File(..., description="PDF document file payload"),
    upload_service: UploadService = Depends(get_upload_service)
) -> Any:
    """Handles upload requests, processes them, stores chunks in ChromaDB, and returns a storage status confirmation."""
    try:
        return await upload_service.upload_file(file)
    except HTTPException as e:
        if isinstance(e.detail, dict) and e.detail.get("message") == "Document already exists":
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "success": False,
                    "message": "Document already exists",
                    "existing_document_id": e.detail["existing_document_id"],
                    "original_upload_time": e.detail["original_upload_time"]
                }
            )
        raise e
