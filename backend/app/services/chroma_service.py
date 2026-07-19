import os
import time
import logging
from typing import List
import chromadb
from fastapi import HTTPException, status

from app.config import Settings
from app.models.response_models import EmbeddingResponse, StorageResponse

logger = logging.getLogger("app.services.chroma_service")

class ChromaService:
    """Service to handle interactions with ChromaDB vector database."""
    
    _client = None
    _collection = None

    def __init__(self, settings: Settings):
        self.settings = settings
        if ChromaService._client is None:
            self._init_db()

    def _init_db(self) -> None:
        try:
            logger.info("ChromaDB initialization: Starting PersistentClient...")
            db_path = self.settings.CHROMA_DB_PATH
            collection_name = self.settings.CHROMA_COLLECTION
            
            # Resolve db_path to an absolute path relative to backend root if it's relative
            from app.config import BACKEND_DIR
            if not os.path.isabs(db_path):
                abs_db_path = os.path.abspath(os.path.join(BACKEND_DIR, db_path))
            else:
                abs_db_path = db_path
                
            os.makedirs(abs_db_path, exist_ok=True)
            
            ChromaService._client = chromadb.PersistentClient(path=abs_db_path)
            logger.info("ChromaDB initialization: Client initialized successfully at %s", abs_db_path)
            
            logger.info("ChromaDB collection loading: Retrieving or creating collection '%s'", collection_name)
            ChromaService._collection = ChromaService._client.get_or_create_collection(
                name=collection_name
            )
            logger.info("ChromaDB collection loading: Collection '%s' is loaded and ready", collection_name)
        except Exception as e:
            logger.exception("Database initialization failure in ChromaService")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ChromaDB vector database failed to initialize."
            )

    def store_embeddings(self, embedding_resp: EmbeddingResponse) -> StorageResponse:
        """Stores embeddings in ChromaDB and preserves all metadata."""
        if not embedding_resp.embeddings:
            logger.error("Storage failure: Empty embedding list.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No embeddings provided to store."
            )

        logger.info(
            "Storage started: Storing %d vectors in collection '%s'",
            len(embedding_resp.embeddings),
            self.settings.CHROMA_COLLECTION
        )
        
        start_time = time.time()
        
        ids: List[str] = []
        embeddings: List[List[float]] = []
        metadatas: List[dict] = []
        documents: List[str] = []
        
        for emb in embedding_resp.embeddings:
            # Format: document_id_chunk_id
            vector_id = f"{emb.document_id}_chunk_{emb.chunk_id}"
            ids.append(vector_id)
            embeddings.append(emb.embedding)
            
            metadata = {
                "document_id": emb.document_id,
                "chunk_id": emb.chunk_id,
                "page_number": emb.page_number,
                "document_name": emb.document_name,
                "character_count": emb.character_count,
                "text": emb.text
            }
            metadatas.append(metadata)
            documents.append(emb.text)
            
        # Check for duplicate IDs
        if len(ids) != len(set(ids)):
            logger.error("Storage failure: Duplicate IDs found in embedding batch.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate chunk IDs found in the embedding payload."
            )
            
        try:
            total_vectors = len(ids)
            batch_size = 500  # Process in batches to ensure scalability
            
            for i in range(0, total_vectors, batch_size):
                batch_ids = ids[i:i + batch_size]
                batch_embeddings = embeddings[i:i + batch_size]
                batch_metadatas = metadatas[i:i + batch_size]
                batch_documents = documents[i:i + batch_size]
                
                ChromaService._collection.upsert(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    metadatas=batch_metadatas,
                    documents=batch_documents
                )
                
            elapsed_time = time.time() - start_time
            total_vectors_in_col = ChromaService._collection.count()
            
            logger.info(
                "Storage completed: Stored %d vectors in %.4f seconds. Total vectors in collection: %d",
                total_vectors,
                elapsed_time,
                total_vectors_in_col
            )
            
            return StorageResponse(
                success=True,
                filename=embedding_resp.filename,
                document_id=embedding_resp.document_id,
                collection_name=self.settings.CHROMA_COLLECTION,
                stored_chunks=total_vectors,
                vector_dimension=embedding_resp.vector_dimension,
                storage_time=round(elapsed_time, 4)
            )
            
        except Exception as e:
            logger.exception("Storage failure in ChromaService")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store embeddings: {str(e)}"
            )

    def query_collection(self, query_embedding: List[float], top_k: int, document_id: str | None = None) -> dict:
        """Queries the ChromaDB collection using a vector embedding and returns top_k results, optionally filtered by document_id."""
        if ChromaService._collection is None:
            logger.error("ChromaDB query failed: collection not initialized.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ChromaDB collection is not initialized."
            )
            
        try:
            from app.config import document_filter_context
            doc_filter = document_id or document_filter_context.get()
            
            # Normalize doc_filter (treating "all", "None", and empty values as None)
            if doc_filter in ("all", "None", "", None):
                doc_filter = None
                
            where_clause = {"document_id": doc_filter} if doc_filter else None
            
            if where_clause:
                logger.info("ChromaDB query started: fetching top %d results filtered by document_id '%s'.", top_k, doc_filter)
            else:
                logger.info("ChromaDB query started: fetching top %d results (global search).", top_k)
                
            results = ChromaService._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            return results
        except Exception as e:
            logger.exception("ChromaDB query execution failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"ChromaDB search failed: {str(e)}"
            )

    def delete_document_vectors(self, document_id: str) -> int:
        """Deletes all vector embeddings associated with a document_id and returns the count of deleted items."""
        if ChromaService._collection is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ChromaDB collection is not initialized."
            )
        try:
            logger.info("ChromaDB deletion: Querying vector count for document_id '%s'...", document_id)
            results = ChromaService._collection.get(where={"document_id": document_id})
            count = len(results.get("ids", []))
            if count > 0:
                logger.info("ChromaDB deletion: Deleting %d vectors for document_id '%s'...", count, document_id)
                ChromaService._collection.delete(where={"document_id": document_id})
            else:
                logger.warning("ChromaDB deletion: No vectors found for document_id '%s'.", document_id)
            return count
        except Exception as e:
            logger.exception("ChromaDB deletion failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete document vectors from vector database: {str(e)}"
            )

    def get_collection_count(self) -> int:
        """Returns the number of documents in the collection."""
        if ChromaService._collection is None:
            logger.error("Failed to get count: collection not initialized.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ChromaDB collection is not initialized."
            )
        try:
            return ChromaService._collection.count()
        except Exception as e:
            logger.exception("Failed to get collection count from ChromaDB")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to query collection count: {str(e)}"
            )

    def collection_exists(self) -> bool:
        """Checks if the ChromaDB collection is loaded/initialized."""
        return ChromaService._collection is not None

    def get_collection(self):
        """Returns the raw collection object."""
        if ChromaService._collection is None:
            logger.error("Failed to get collection: collection not initialized.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ChromaDB collection is not initialized."
            )
        return ChromaService._collection
