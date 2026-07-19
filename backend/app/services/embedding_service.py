import logging
import time
from typing import List

from sentence_transformers import SentenceTransformer
from fastapi import HTTPException, status

from app.config import Settings
from app.models.response_models import ChunkResponse, Embedding, EmbeddingResponse

logger = logging.getLogger("app.services.embedding_service")

class EmbeddingService:
    """Singleton service that generates embeddings for chunks.

    The model is loaded once when the service is first instantiated and reused for all
    subsequent calls. This ensures minimal overhead and high throughput.
    """

    _model: SentenceTransformer | None = None
    _model_name: str | None = None
    _vector_dim: int | None = None

    def __init__(self, settings: Settings):
        self.settings = settings
        if not EmbeddingService._model:
            self._load_model()
        else:
            logger.info(
                "Reusing previously loaded embedding model: %s (dim=%s)",
                EmbeddingService._model_name,
                EmbeddingService._vector_dim,
            )

    def _load_model(self) -> None:
        model_name = self.settings.EMBEDDING_MODEL
        logger.info("Loading embedding model: %s", model_name)
        start = time.time()
        try:
            EmbeddingService._model = SentenceTransformer(model_name)
            EmbeddingService._model_name = model_name
            EmbeddingService._vector_dim = EmbeddingService._model.get_embedding_dimension()
            elapsed = time.time() - start
            logger.info(
                "Embedding model loaded successfully in %.2f seconds. Model: %s, Dimension: %s",
                elapsed,
                model_name,
                EmbeddingService._vector_dim,
            )
        except Exception as e:
            logger.exception("Failed to load embedding model %s: %s", model_name, e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load embedding model.",
            )

    def generate_embeddings(self, chunk_resp: ChunkResponse) -> EmbeddingResponse:
        if not chunk_resp.chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No chunks available for embedding generation.",
            )

        texts: List[str] = [chunk.text for chunk in chunk_resp.chunks]
        logger.info(
            "Generating embeddings for %d chunks (batch size %d).",
            len(texts),
            self.settings.EMBEDDING_BATCH_SIZE,
        )
        start = time.time()
        try:
            # Batch encoding – returns a NumPy array of shape (n_chunks, dim)
            embeddings_np = EmbeddingService._model.encode(
                texts,
                batch_size=self.settings.EMBEDDING_BATCH_SIZE,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        except Exception as e:
            logger.exception("Embedding generation failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Embedding generation failed.",
            )
        total_time = time.time() - start
        avg_time = total_time / len(texts) if texts else 0
        logger.info(
            "Embedding generation completed in %.2f seconds (avg %.4f s per chunk).",
            total_time,
            avg_time,
        )

        # Convert each embedding to list of floats for JSON serialization
        embedding_list: List[Embedding] = []
        for chunk, vec in zip(chunk_resp.chunks, embeddings_np):
            embedding = Embedding(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                page_number=chunk.page_number,
                document_name=chunk.document_name,
                text=chunk.text,
                character_count=chunk.character_count,
                embedding=vec.tolist(),
                vector_dimension=EmbeddingService._vector_dim,
            )
            embedding_list.append(embedding)

        response = EmbeddingResponse(
            success=True,
            filename=chunk_resp.filename,
            document_id=chunk_resp.document_id,
            embedding_model=EmbeddingService._model_name,
            vector_dimension=EmbeddingService._vector_dim,
            total_chunks=len(embedding_list),
            embeddings=embedding_list,
        )
        return response

    def generate_query_embedding(self, query: str) -> List[float]:
        """Generates exactly one embedding for the user's question query.
        
        Reuses the loaded singleton model.
        """
        if not query or not query.strip():
            logger.error("Query embedding generation failed: empty query.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty query string provided."
            )
        
        if not EmbeddingService._model:
            logger.info("Embedding model not yet initialized, loading model...")
            self._load_model()
            
        logger.info("Generating query embedding for query string: '%s'", query)
        start = time.time()
        try:
            # Generate exactly one embedding
            embedding_np = EmbeddingService._model.encode(
                query,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            elapsed = time.time() - start
            logger.info(
                "Query embedding generated successfully in %.4f seconds (dim=%d).",
                elapsed,
                len(embedding_np),
            )
            return embedding_np.tolist()
        except Exception as e:
            logger.exception("Query embedding generation failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Query embedding generation failed."
            )
