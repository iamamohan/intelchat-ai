from fastapi import APIRouter, Depends
from app.config import Settings, settings, BACKEND_DIR
from app.dependencies import get_settings
from app.services.document_service import DocumentService
from app.services.retrieval_service import RetrievalService
import os

router = APIRouter(prefix="/api")

def get_document_service(settings: Settings = Depends(get_settings)) -> DocumentService:
    return DocumentService(settings)

@router.get(
    "/statistics",
    summary="Get Document Base Statistics",
    description="Returns cumulative statistics and analytical metrics of the Multi-Document Knowledge Base."
)
async def get_statistics(doc_service: DocumentService = Depends(get_document_service)):
    """Computes total counts, storage sizes, and timing averages for the knowledge base."""
    # 1. Fetch active documents
    active_docs = doc_service.get_all_active_documents()
    
    total_docs = len(active_docs)
    total_pages = sum(doc.get("page_count", 0) for doc in active_docs)
    total_chunks = sum(doc.get("chunk_count", 0) for doc in active_docs)
    total_embeddings = sum(doc.get("vector_count", 0) for doc in active_docs)
    
    # Largest / Smallest Document
    largest_doc = None
    smallest_doc = None
    if active_docs:
        largest_record = max(active_docs, key=lambda x: x.get("file_size", 0))
        smallest_record = min(active_docs, key=lambda x: x.get("file_size", 0))
        largest_doc = {
            "filename": largest_record["original_filename"],
            "file_size_bytes": largest_record["file_size"]
        }
        smallest_doc = {
            "filename": smallest_record["original_filename"],
            "file_size_bytes": smallest_record["file_size"]
        }
        
    # Averages
    avg_pages = round(total_pages / total_docs, 2) if total_docs > 0 else 0.0
    avg_chunks = round(total_chunks / total_docs, 2) if total_docs > 0 else 0.0
    
    embed_times = [doc.get("embedding_time", 0.0) for doc in active_docs if doc.get("embedding_time", 0.0) > 0.0]
    avg_embed_time = round(sum(embed_times) / len(embed_times), 4) if embed_times else 0.0
    
    # 2. Average Retrieval & Chat Times
    ret_times = getattr(RetrievalService, "_retrieval_times", [])
    avg_ret_time = round(sum(ret_times) / len(ret_times), 4) if ret_times else 0.0
    
    chat_times = getattr(DocumentService, "_chat_times", [])
    avg_chat_time = round(sum(chat_times) / len(chat_times), 4) if chat_times else 0.0
    
    # 3. Storage Used calculation
    # PDFs Folder size
    upload_dir = settings.upload_folder_path
    pdf_size = 0
    if os.path.exists(upload_dir):
        for f in os.listdir(upload_dir):
            fp = os.path.join(upload_dir, f)
            if os.path.isfile(fp):
                pdf_size += os.path.getsize(fp)
                
    # ChromaDB Folder size
    db_path = settings.CHROMA_DB_PATH
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(os.path.join(BACKEND_DIR, db_path))
    chroma_size = 0
    if os.path.exists(db_path):
        for dirpath, dirnames, filenames in os.walk(db_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    chroma_size += os.path.getsize(fp)
                    
    # SQLite DB size
    registry_path = settings.DOCUMENT_REGISTRY_PATH
    if not os.path.isabs(registry_path):
        registry_path = os.path.abspath(os.path.join(BACKEND_DIR, registry_path))
    sqlite_size = os.path.getsize(registry_path) if os.path.exists(registry_path) else 0
    
    total_storage_mb = round((pdf_size + chroma_size + sqlite_size) / (1024 * 1024), 2)
    
    # 4. Documents By Status breakdown
    all_records = doc_service.repository.get_all_documents_including_deleted()
    status_counts = {}
    for doc in all_records:
        status_val = doc.get("status")
        status_counts[status_val] = status_counts.get(status_val, 0) + 1

    # 5. Sprint 9 Conversation Quality Metrics & Chat Analytics
    from app.services.conversation_service import ConversationService
    conv_service = ConversationService(settings)
    chat_analytics = conv_service.get_conversation_quality_metrics()
        
    return {
        "total_documents": total_docs,
        "total_pages": total_pages,
        "total_chunks": total_chunks,
        "total_embeddings": total_embeddings,
        "largest_document": largest_doc,
        "smallest_document": smallest_doc,
        "average_pages": avg_pages,
        "average_chunks": avg_chunks,
        "average_embedding_time_seconds": avg_embed_time,
        "average_retrieval_time_seconds": avg_ret_time,
        "average_chat_time_seconds": avg_chat_time,
        "storage_used_mb": total_storage_mb,
        "documents_by_status": status_counts,
        "chat_analytics": chat_analytics
    }

