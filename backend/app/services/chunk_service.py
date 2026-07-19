import os
import logging
import time
from typing import List
from fastapi import HTTPException, status
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.models.response_models import PDFExtractionResponse, ChunkResponse, Chunk
from app.config import settings

logger = logging.getLogger("app.services.chunk_service")

class ChunkService:
    """Service that converts extracted PDF pages into structured text chunks.

    Configuration (chunk size & overlap) is read from the application settings.
    """

    def __init__(self):
        self.chunk_size = getattr(settings, "CHUNK_SIZE", 500)
        self.chunk_overlap = getattr(settings, "CHUNK_OVERLAP", 100)
        logger.info(
            f"ChunkService initialized with size={self.chunk_size}, overlap={self.chunk_overlap}"
        )

    def create_chunks(self, extraction: PDFExtractionResponse) -> ChunkResponse:
        start_time = time.time()
        logger.info(
            f"Chunking started for document '{extraction.filename}' with {extraction.total_pages} pages"
        )

        if not extraction.pages:
            logger.error("Empty document: no pages to chunk")
            raise HTTPException(
                status_code=422,
                detail="Document contains no extractable pages."
            )

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
        )

        chunks: List[Chunk] = []
        chunk_id_counter = 1
        for page in extraction.pages:
            page_text = page.text or ""
            if not page_text.strip():
                logger.warning(
                    f"Page {page.page_number} of '{extraction.filename}' is empty; skipping chunking."
                )
                continue
            # Split the page text into chunks
            page_chunks = splitter.split_text(page_text)
            for txt in page_chunks:
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id_counter,
                        document_id=extraction.document_id,
                        page_number=page.page_number,
                        document_name=extraction.filename,
                        text=txt,
                        character_count=len(txt),
                    )
                )
                chunk_id_counter += 1

        total_chunks = len(chunks)
        avg_chunk_size = (
            sum(c.character_count for c in chunks) / total_chunks if total_chunks > 0 else 0
        )
        processing_time = time.time() - start_time

        logger.info(
            f"Chunking completed: {total_chunks} chunks created (avg size {avg_chunk_size:.1f} chars) in {processing_time:.2f}s"
        )

        return ChunkResponse(
            success=True,
            filename=extraction.filename,
            document_id=extraction.document_id,
            total_pages=extraction.total_pages,
            total_chunks=total_chunks,
            chunks=chunks,
        )
