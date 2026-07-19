import os
import uuid
import time
import hashlib
import logging
from fastapi import UploadFile, HTTPException, status
from app.config import Settings
from app.utils.file_utils import is_pdf, sanitize_filename
from app.services.pdf_service import PDFService
from app.services.chunk_service import ChunkService
from app.services.embedding_service import EmbeddingService
from app.services.chroma_service import ChromaService
from app.services.document_service import DocumentService
from app.models.response_models import StorageResponse

logger = logging.getLogger("app.services.upload_service")

class UploadService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.document_service = DocumentService(settings)

    async def upload_file(self, file: UploadFile) -> StorageResponse:
        """
        Validates, sanitizes, saves the uploaded PDF file to the local directory,
        extracts text, chunks it, generates embeddings, stores them in ChromaDB,
        tracks the incremental lifecycle stages, and registers it in the SQLite registry.
        """
        start_time = time.time()

        # 1. Validate file object and filename existence
        if not file or not file.filename:
            logger.warning("Upload validation failed: No file payload provided.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file uploaded."
            )

        # 2. Validate PDF format
        if not is_pdf(file.filename):
            logger.warning(f"Upload validation failed: '{file.filename}' is not a PDF.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed."
            )

        # 3. Validate file size
        file_size = getattr(file, "size", None)
        if file_size is None:
            try:
                file.file.seek(0, 2)
                file_size = file.file.tell()
                file.file.seek(0)
            except Exception as e:
                logger.error(f"Failed to determine file size: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error."
                )

        max_size = self.settings.MAX_UPLOAD_SIZE
        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            logger.warning(
                f"Upload validation failed: File size ({file_size} B) "
                f"exceeds limit ({max_size} B)."
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds the maximum limit of {max_size_mb:.0f}MB."
            )

        # 4. Generate document_id and check limits (storage size, document count limit)
        document_id = str(uuid.uuid4())
        self.document_service.check_limits(file_size)

        # 5. Register document initally with 'Uploading' status
        original_filename = file.filename
        safe_filename = f"{document_id}_{sanitize_filename(original_filename)}"
        self.document_service.register_document_init(
            doc_id=document_id,
            original_filename=original_filename,
            stored_filename=safe_filename,
            file_size=file_size
        )

        upload_dir = self.settings.upload_folder_path
        destination_path = os.path.join(upload_dir, safe_filename)

        try:
            # Create upload folder if missing
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save uploaded PDF to storage disk
            with open(destination_path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    buffer.write(chunk)
            logger.info("File saved to disk successfully: '%s'", destination_path)

            # 6. Extract text using PDFService
            self.document_service.update_stage_status(document_id, "Extracting")
            pdf_service = PDFService()
            extraction_result = pdf_service.extract_text(destination_path)
            extraction_result.document_id = document_id  # Force override with pre-generated document_id

            # 7. Quick Duplicate Detection (Filename, File Size, Page Count)
            candidates = self.document_service.check_duplicate_pre_hash(
                original_filename, file_size, extraction_result.total_pages
            )
            computed_hash = None
            if candidates:
                computed_hash = self.document_service.verify_hash_duplicate(candidates, destination_path)
                if computed_hash:
                    # Duplicate found! Delete file and mark deleted in registry
                    if os.path.exists(destination_path):
                        os.remove(destination_path)
                    self.document_service.update_stage_status(document_id, "Deleted")
                    
                    # Log structured duplicate detection warnings
                    existing_doc = next(c for c in candidates if c.get("sha256_hash") == computed_hash)
                    logger.warning(
                        "Duplicate Detection: Blocked duplicate upload for filename '%s'. "
                        "Existing Document ID: %s, Original Uploaded Time: %s",
                        original_filename,
                        existing_doc["document_id"],
                        existing_doc["upload_timestamp"]
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "message": "Document already exists",
                            "existing_document_id": existing_doc["document_id"],
                            "original_upload_time": existing_doc["upload_timestamp"]
                        }
                    )

            # Compute hash to save if not computed already
            if not computed_hash:
                sha256 = hashlib.sha256()
                with open(destination_path, "rb") as f:
                    while chunk := f.read(8192):
                        sha256.update(chunk)
                computed_hash = sha256.hexdigest()

            # Save computed hash and page count
            self.document_service.repository.update_document(document_id, {
                "sha256_hash": computed_hash,
                "page_count": extraction_result.total_pages
            })

            # 8. Chunk the extracted text using ChunkService
            self.document_service.update_stage_status(document_id, "Chunking")
            chunk_service = ChunkService()
            chunk_result = chunk_service.create_chunks(extraction_result)

            # 9. Generate embeddings using EmbeddingService
            self.document_service.update_stage_status(document_id, "Embedding")
            embedding_service = EmbeddingService(self.settings)
            emb_start = time.time()
            embedding_result = embedding_service.generate_embeddings(chunk_result)
            embedding_time = time.time() - emb_start

            # 10. Store embeddings in ChromaDB using ChromaService
            self.document_service.update_stage_status(document_id, "Indexing")
            chroma_service = ChromaService(self.settings)
            storage_result = chroma_service.store_embeddings(embedding_result)

            # 11. Complete Registration -> Set status to Ready and save timings
            elapsed_time = time.time() - start_time
            self.document_service.repository.update_document(document_id, {
                "chunk_count": len(chunk_result.chunks),
                "vector_count": len(chunk_result.chunks),
                "status": "Ready",
                "processing_time": round(elapsed_time, 4),
                "embedding_time": round(embedding_time, 4)
            })

            logger.info(
                "Document upload lifecycle completed successfully: %s. Processing time: %.4f s",
                document_id,
                elapsed_time
            )
            DocumentService.record_upload_time(elapsed_time)

            return storage_result

        except Exception as e:
            # If any failure occurs during lifecycle, clean up storage and mark failed
            logger.exception("Upload processing failed for document_id '%s'", document_id)
            if os.path.exists(destination_path):
                try:
                    os.remove(destination_path)
                except Exception as cleanup_err:
                    logger.error("Failed to clean up file %s on error: %s", destination_path, cleanup_err)
            
            # Prevent marking as Failed if it was deleted due to duplicate check
            doc_record = self.document_service.get_document(document_id)
            if doc_record and doc_record.get("status") != "Deleted":
                self.document_service.update_stage_status(document_id, "Failed")
            raise e
