from pydantic import BaseModel, Field
from typing import List

class HealthResponse(BaseModel):
    """Schema for service health check response."""
    status: str = Field(default="running", description="Current status of the service")
    service: str = Field(default="AI Knowledge Assistant Backend", description="Service name")
    version: str = Field(default="1.0.0", description="Application version")

class PDFPage(BaseModel):
    """Schema for a single PDF page text extraction."""
    page_number: int = Field(..., description="Page number starting at 1")
    text: str = Field(..., description="Extracted text content of the page")

class PDFExtractionResponse(BaseModel):
    """Schema for PDF extraction response after upload."""
    success: bool = Field(default=True, description="Indicates successful extraction")
    filename: str = Field(..., description="Uploaded PDF file name")
    document_id: str = Field(..., description="Unique identifier for the uploaded document")
    total_pages: int = Field(..., description="Total number of pages in the PDF")
    pages: List[PDFPage] = Field(..., description="List of extracted pages with text")

class Chunk(BaseModel):
    """Metadata for a single text chunk derived from a PDF page."""
    chunk_id: int = Field(..., description="Sequential identifier for the chunk across the document")
    document_id: str = Field(..., description="Unique identifier for the uploaded document")
    page_number: int = Field(..., description="The source page number (starting at 1)")
    document_name: str = Field(..., description="Original PDF filename")
    text: str = Field(..., description="Chunk text content")
    character_count: int = Field(..., description="Number of characters in the chunk")

class ChunkResponse(BaseModel):
    """Response model returned after chunking a PDF document."""
    success: bool = Field(default=True, description="Indicates successful chunk generation")
    filename: str = Field(..., description="Uploaded PDF file name")
    document_id: str = Field(..., description="Unique identifier for the uploaded document")
    total_pages: int = Field(..., description="Number of pages in the PDF")
    total_chunks: int = Field(..., description="Total number of generated chunks")
    chunks: List[Chunk] = Field(..., description="List of generated chunks with metadata")

class ChatRequest(BaseModel):
    """Schema for client chat request payload."""
    question: str = Field(..., description="The user query or question")

class ChatResponse(BaseModel):
    """Schema for dummy/future assistant responses."""
    answer: str = Field(default="Backend connection successful.", description="Assistant's text response")
    citations: List[str] = Field(default_factory=list, description="List of source file names or document chunks cited")

class ErrorResponse(BaseModel):
    """Standardized API error response schema."""
    success: bool = Field(default=False, description="Always False for failures")
    message: str = Field(..., description="User-friendly error message description")

class Embedding(BaseModel):
    """Metadata and vector for a single text chunk embedding."""
    chunk_id: int = Field(..., description="Sequential identifier for the chunk across the document")
    document_id: str = Field(..., description="Unique identifier for the uploaded document")
    page_number: int = Field(..., description="Source page number of the chunk")
    document_name: str = Field(..., description="Original PDF filename")
    text: str = Field(..., description="Chunk text content")
    character_count: int = Field(..., description="Number of characters in the chunk")
    embedding: List[float] = Field(..., description="Semantic vector embedding for the chunk")
    vector_dimension: int = Field(..., description="Dimension of the embedding vector")

class EmbeddingResponse(BaseModel):
    """Response model returned after generating embeddings."""
    success: bool = Field(default=True, description="Indicates successful embedding generation")
    filename: str = Field(..., description="Uploaded PDF file name")
    document_id: str = Field(..., description="Unique identifier for the uploaded document")
    embedding_model: str = Field(..., description="Name of the embedding model used")
    vector_dimension: int = Field(..., description="Dimension of the generated embeddings")
    total_chunks: int = Field(..., description="Total number of chunks embedded")
    embeddings: List[Embedding] = Field(..., description="List of embeddings with metadata")

class StorageResponse(BaseModel):
    """Response model after storing embeddings in ChromaDB."""
    success: bool = Field(default=True, description="Indicates successful storage")
    filename: str = Field(..., description="Uploaded PDF file name")
    document_id: str = Field(..., description="Unique identifier for the uploaded document")
    collection_name: str = Field(..., description="Name of the ChromaDB collection used")
    stored_chunks: int = Field(..., description="Number of vectors stored")
    vector_dimension: int = Field(..., description="Dimension of the stored vectors")
    storage_time: float = Field(..., description="Time taken to store vectors in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "filename": "sample.pdf",
                "document_id": "a0ccf2cc-ee3f-4a04-b601",
                "collection_name": "documents",
                "stored_chunks": 74,
                "vector_dimension": 384,
                "storage_time": 0.31,
            }
        }

class RetrievalRequest(BaseModel):
    """Request payload schema for semantic search query."""
    query: str = Field(..., description="The query/question string to search for in ChromaDB")

class RetrievedChunk(BaseModel):
    """Schema for a single retrieved chunk with its similarity score and metadata."""
    document_id: str = Field(..., description="Unique identifier for the uploaded document")
    chunk_id: int = Field(..., description="Sequential identifier for the chunk across the document")
    page_number: int = Field(..., description="The source page number (starting at 1)")
    document_name: str = Field(..., description="Original PDF filename")
    text: str = Field(..., description="Chunk text content")
    character_count: int = Field(..., description="Number of characters in the chunk")
    similarity_score: float = Field(..., description="Similarity score of the chunk to the query")

class RetrievalResponse(BaseModel):
    """Response schema containing the search query, top_k configuration, and retrieved results."""
    success: bool = Field(default=True, description="Indicates successful retrieval")
    query: str = Field(..., description="The query searched for")
    top_k: int = Field(..., description="Top K results retrieved")
    retrieval_time: float = Field(..., description="Total retrieval time in seconds")
    total_candidates: int = Field(..., description="Total candidate chunks retrieved from database before filtering")
    filtered_candidates: int = Field(..., description="Number of candidate chunks filtered out due to deduplication or similarity threshold")
    returned_results: int = Field(..., description="Number of results returned to the client")
    retrieval_confidence: str = Field(..., description="Retrieval confidence level (HIGH, MEDIUM, or LOW)")
    results: List[RetrievedChunk] = Field(..., description="List of retrieved chunks ordered by relevance")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "query": "What is Cloud Computing?",
                "top_k": 5,
                "retrieval_time": 0.124,
                "total_candidates": 10,
                "filtered_candidates": 5,
                "returned_results": 5,
                "retrieval_confidence": "HIGH",
                "results": [
                    {
                        "document_id": "abc123",
                        "chunk_id": 1,
                        "page_number": 1,
                        "document_name": "unit_1.pdf",
                        "text": "Cloud Computing is...",
                        "character_count": 487,
                        "similarity_score": 0.982
                    },
                    {
                        "document_id": "abc123",
                        "chunk_id": 2,
                        "page_number": 2,
                        "document_name": "unit_1.pdf",
                        "text": "Cloud Architecture...",
                        "character_count": 465,
                        "similarity_score": 0.941
                    }
                ]
            }
        }

class AnswerRequest(BaseModel):
    """Schema for client RAG chat request payload."""
    question: str = Field(..., description="The query/question string to ask the AI assistant")
    document_id: str | None = Field(default=None, description="Optional document ID filter to restrict search")
    session_id: str | None = Field(default=None, description="Optional session ID to continue a conversation")

class AnswerSource(BaseModel):
    """Schema for a source document chunk cited in the answer."""
    document_name: str = Field(..., description="Original PDF filename")
    page_number: int = Field(..., description="The source page number (starting at 1)")
    chunk_id: int = Field(..., description="Sequential identifier for the chunk across the document")
    similarity_score: float = Field(..., description="Similarity score of the chunk to the query")

class AnswerResponse(BaseModel):
    """Schema for a grounded bot response containing the generated answer and cited sources.
    
    NOTE: Under Sprint 7.5, the schema structure remains strictly stable to avoid breaking downstream consumers.
    """
    success: bool = Field(default=True, description="Indicates successful generation")
    question: str = Field(..., description="The original question asked")
    answer: str = Field(..., description="The grounded answer generated by the LLM")
    retrieval_confidence: str = Field(..., description="Retrieval confidence level (HIGH, MEDIUM, or LOW)")
    sources: List[AnswerSource] = Field(..., description="List of document sources cited for the answer")
    response_time: float = Field(..., description="Total pipeline response time in seconds")
    session_id: str | None = Field(default=None, description="Optional session ID of the conversation session")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "question": "What is Cloud Computing?",
                "answer": "Cloud Computing is the delivery of computing services such as servers, storage, databases, networking, software, analytics, and intelligence over the Internet. It provides an alternative to maintaining on-premises infrastructure and enables on-demand access to computing resources.",
                "retrieval_confidence": "HIGH",
                "sources": [
                    {
                        "document_name": "unit_1.pdf",
                        "page_number": 1,
                        "chunk_id": 2,
                        "similarity_score": 0.779
                    }
                ],
                "response_time": 1.24,
                "session_id": "8f8b80ab-c377-4b71-b0db-bcf61e27a6f2"
            }
        }

# --- Sprint 9 Chat Session Models ---

class ChatSessionResponse(BaseModel):
    """Schema for a single chat session metadata and details."""
    session_id: str = Field(..., description="Unique session identifier")
    title: str = Field(..., description="Auto-generated or custom session title")
    created_time: str = Field(..., description="Session creation ISO timestamp")
    updated_time: str = Field(..., description="Session last updated ISO timestamp")
    message_count: int = Field(default=0, description="Total messages in the session")
    document_filter: str | None = Field(default=None, description="Optional document ID used as a filter")
    summary: str | None = Field(default=None, description="Current cumulative conversation summary")
    status: str = Field(default="active", description="Status of the session (active, archived)")
    last_accessed: str = Field(..., description="Timestamp of when the session was last loaded or messaged")
    total_tokens: int = Field(default=0, description="Cumulative tokens used by the session")
    favorite: bool = Field(default=False, description="Whether the session is marked as favorite")
    archived: bool = Field(default=False, description="Whether the session is archived")
    pinned: bool = Field(default=False, description="Whether the session is pinned to top")

class CreateSessionRequest(BaseModel):
    """Schema for creating a new chat session."""
    title: str | None = Field(default=None, description="Optional custom title for the session")
    document_filter: str | None = Field(default=None, description="Optional document ID filter to restrict queries")

class RenameSessionRequest(BaseModel):
    """Schema for renaming or toggling session metadata flags."""
    title: str | None = Field(default=None, description="New title for the session")
    favorite: bool | None = Field(default=None, description="Mark as favorite or not")
    pinned: bool | None = Field(default=None, description="Pin session to top or not")
    archived: bool | None = Field(default=None, description="Archive session or not")

class SearchQueryRequest(BaseModel):
    """Schema for FTS keyword history search."""
    query: str = Field(..., min_length=1, description="Keyword search query")
    session_id: str | None = Field(default=None, description="Optional filter to search only in specific session")

class SearchMessageResult(BaseModel):
    """FTS message match result with context."""
    message_id: str = Field(..., description="Unique message ID")
    session_id: str = Field(..., description="Parent session ID")
    session_title: str = Field(..., description="Title of parent session")
    role: str = Field(..., description="Role of message sender (user/assistant)")
    content: str = Field(..., description="Message text content containing match")
    timestamp: str = Field(..., description="ISO timestamp of message")

class SearchResponse(BaseModel):
    """FTS search matches response."""
    success: bool = Field(default=True)
    query: str = Field(..., description="Original search query")
    matches: List[SearchMessageResult] = Field(default_factory=list, description="List of matching messages")

