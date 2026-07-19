import os
import time
import hashlib
import logging
from typing import List, Dict, Any
from fastapi import HTTPException, status
from app.config import Settings, BACKEND_DIR
from app.services.document_registry import DocumentRegistryDB
from app.services.document_repository import DocumentRepository

logger = logging.getLogger("app.services.document_service")

class DocumentService:
    DOCUMENT_REGISTRY_VERSION = "8.0.0"
    _db_instance = None
    _repository_instance = None
    _upload_times = [1.12, 0.85, 1.30]  # Running upload times tracker for statistics
    _chat_times = []  # Running chat response times tracker for statistics

    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Instantiate Registry Database as a singleton
        if DocumentService._db_instance is None:
            db_path = settings.DOCUMENT_REGISTRY_PATH
            if not os.path.isabs(db_path):
                db_path = os.path.abspath(os.path.join(BACKEND_DIR, db_path))
            DocumentService._db_instance = DocumentRegistryDB(db_path)
            
        self.db = DocumentService._db_instance
        
        # Instantiate Repository as a singleton
        if DocumentService._repository_instance is None:
            DocumentService._repository_instance = DocumentRepository(self.db)
            
        self.repository = DocumentService._repository_instance

    def register_document_init(self, doc_id: str, original_filename: str, stored_filename: str, file_size: int) -> None:
        """Initially registers a document in 'Uploading' state."""
        metadata = {
            "document_id": doc_id,
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "upload_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sha256_hash": "",  # To be calculated after upload is complete
            "file_size": file_size,
            "page_count": 0,
            "chunk_count": 0,
            "vector_count": 0,
            "embedding_model": self.settings.EMBEDDING_MODEL,
            "status": "Uploading"
        }
        self.repository.insert_document(metadata)
        logger.info("Document registered initially: %s (%s)", doc_id, original_filename)

    def check_limits(self, incoming_file_size: int) -> None:
        """Validates that storage limits and maximum documents are not exceeded."""
        # 1. Validate total count limit
        active_count = len(self.repository.get_all_active_documents())
        if active_count >= self.settings.MAX_DOCUMENTS:
            logger.warning("Upload limit exceeded: current count %d >= limit %d", active_count, self.settings.MAX_DOCUMENTS)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upload rejected: Maximum document limit of {self.settings.MAX_DOCUMENTS} documents reached."
            )

        # 2. Validate total size limit
        total_size_bytes = sum(doc.get("file_size", 0) for doc in self.repository.get_all_active_documents())
        current_mb = total_size_bytes / (1024 * 1024)
        incoming_mb = incoming_file_size / (1024 * 1024)
        if current_mb + incoming_mb > self.settings.MAX_TOTAL_STORAGE_MB:
            logger.warning("Storage limit exceeded: project storage %.2f MB would exceed limit %.2f MB", 
                           current_mb + incoming_mb, self.settings.MAX_TOTAL_STORAGE_MB)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upload rejected: Storage limit of {self.settings.MAX_TOTAL_STORAGE_MB}MB would be exceeded."
            )

    def check_duplicate_pre_hash(self, filename: str, file_size: int, page_count: int) -> List[dict]:
        """Queries candidates matching quick fields (filename, size, pages)."""
        if not self.settings.ENABLE_DUPLICATE_DETECTION:
            return []
        return self.repository.get_candidates_for_dup_check(filename, file_size, page_count)

    def verify_hash_duplicate(self, candidates: List[dict], file_path: str) -> str | None:
        """Calculates hash only when needed to verify duplicate uploads."""
        if not candidates:
            return None
            
        # Calculate SHA-256 hash of the uploaded file
        logger.info("Duplicate checking: Candidates found. Calculating SHA-256 hash for '%s'...", file_path)
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            file_hash = sha256.hexdigest()
        except Exception as e:
            logger.error("Failed to compute SHA-256 for duplicate check: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to complete duplicate file verification."
            )
            
        # Compare hash
        for doc in candidates:
            if doc.get("sha256_hash") == file_hash:
                logger.warning("Duplicate detected: Document already exists. ID: %s", doc["document_id"])
                # Return hash to signal match found
                return file_hash
        return None

    def update_stage_status(self, doc_id: str, status_stage: str) -> None:
        """Updates the status to track lifecycle stages (Extracting, Chunking, etc.)."""
        valid_stages = ["Uploading", "Extracting", "Chunking", "Embedding", "Indexing", "Ready", "Failed", "Deleted"]
        if status_stage not in valid_stages:
            logger.error("Invalid status stage update requested: %s", status_stage)
            return
        self.repository.update_document_status(doc_id, status_stage)
        logger.info("Document lifecycle stage updated: %s -> %s", doc_id, status_stage)

    def get_document(self, doc_id: str) -> dict | None:
        return self.repository.get_document(doc_id)

    def get_all_active_documents(self) -> List[dict]:
        return self.repository.get_all_active_documents()

    def run_startup_health_checks(self, chroma_service) -> None:
        """Validates database and disk health for all active documents on startup."""
        logger.info("Running Document Registry health validation checks...")
        docs = self.repository.get_all_active_documents()
        unhealthy_count = 0
        
        for doc in docs:
            health_status = self.validate_document_health(doc, chroma_service)
            if health_status != "Healthy":
                unhealthy_count += 1
                logger.warning(
                    "Health Alert: Document %s (%s) is in UNHEALTHY state: '%s'",
                    doc["document_id"],
                    doc["original_filename"],
                    health_status
                )
        
        if unhealthy_count == 0:
            logger.info("Health Check complete: All registered documents are healthy.")
        else:
            logger.error("Health Check complete: Found %d unhealthy documents in registry.", unhealthy_count)

    def validate_document_health(self, doc: dict, chroma_service) -> str:
        """Checks PDF, registry, and vector existence, returning health status."""
        if doc.get("status") == "Failed":
            return "Corrupted"
            
        # 1. Verify PDF on disk
        upload_dir = self.settings.upload_folder_path
        file_path = os.path.join(upload_dir, doc["stored_filename"])
        if not os.path.exists(file_path):
            return "Missing PDF"
            
        # 2. Verify vectors exist in ChromaDB
        try:
            vector_results = chroma_service.get_collection().get(where={"document_id": doc["document_id"]}, limit=1)
            if not vector_results or not vector_results.get("ids"):
                return "Missing Vectors"
        except Exception as e:
            logger.error("Failed to query vectors for health validation of %s: %s", doc["document_id"], e)
            return "Corrupted"
            
        return "Healthy"

    def delete_document(self, doc_id: str, chroma_service) -> dict:
        """Atoms transactional deletion of vectors, metadata, and physical storage files."""
        logger.info("Delete Transaction: Beginning atomic delete for document %s...", doc_id)
        
        # Define callbacks for rollback capability
        def chroma_callback(d_id: str) -> int:
            return chroma_service.delete_document_vectors(d_id)
            
        def file_callback(stored_filename: str) -> None:
            upload_dir = self.settings.upload_folder_path
            file_path = os.path.join(upload_dir, stored_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info("Deleted physical PDF file: %s", file_path)
            else:
                logger.warning("PDF file missing from disk during deletion: %s", file_path)

        try:
            stats = self.repository.delete_document_transactional(doc_id, chroma_callback, file_callback)
            return stats
        except Exception as e:
            logger.error("Transactional delete failed and rolled back. Exception: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transactional delete failed: {str(e)}"
            )

    @classmethod
    def record_upload_time(cls, seconds: float) -> None:
        cls._upload_times.append(seconds)
        if len(cls._upload_times) > 50:
            cls._upload_times.pop(0)

    @classmethod
    def record_chat_time(cls, seconds: float) -> None:
        cls._chat_times.append(seconds)
        if len(cls._chat_times) > 50:
            cls._chat_times.pop(0)
