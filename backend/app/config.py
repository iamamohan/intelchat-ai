import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

# Resolve backend root directory (parent of the app directory)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE_PATH = os.path.join(BACKEND_DIR, ".env")

class Settings(BaseSettings):
    APP_NAME: str = "AI Knowledge Assistant"
    APP_VERSION: str = "1.0.0"
    UPLOAD_FOLDER: str = "uploads"
    MAX_UPLOAD_SIZE: int = 20971520  # 20MB in bytes
    CHUNK_SIZE: int = 500  # default chunk size, can be overridden via .env
    CHUNK_OVERLAP: int = 100  # default chunk overlap, can be overridden via .env
    # ChromaDB configuration
    CHROMA_DB_PATH: str = "chroma_db"
    CHROMA_COLLECTION: str = "documents"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"  # can be overridden via .env
    EMBEDDING_BATCH_SIZE: int = 32  # can be overridden via .env
    TOP_K_RESULTS: int = 5  # can be overridden via .env
    MIN_SIMILARITY_SCORE: float = 0.40  # can be overridden via .env
    CANDIDATE_MULTIPLIER: int = 2  # can be overridden via .env
    GEMINI_API_KEY: str | None = None  # loaded from .env
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "qwen2.5:7b"
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    # LLM Generation parameters
    TEMPERATURE: float = 0.0
    TOP_P: float = 0.95
    TOP_K: int = 40
    MAX_OUTPUT_TOKENS: int = 1024

    # Sprint 7.6 Retrieval & Compression parameters
    MAX_CONTEXT_CHARACTERS: int = 1500
    MAX_CONTEXT_CHUNKS: int = 2
    ENABLE_CONTEXT_COMPRESSION: bool = True
    ENABLE_DIVERSITY_FILTER: bool = True
    DEFAULT_TOP_K: int = 5
    ENABLE_RETRIEVAL_CACHE: bool = True
    CACHE_SIZE: int = 100
    CACHE_TTL_SECONDS: int = 300

    # Sprint 8 Document Management configurations
    MAX_DOCUMENTS: int = 100
    MAX_TOTAL_STORAGE_MB: float = 500.0
    ENABLE_DOCUMENT_FILTER: bool = True
    ENABLE_DUPLICATE_DETECTION: bool = True
    DOCUMENT_REGISTRY_PATH: str = "document_registry.db"

    # Sprint 9 Conversational Memory & Multi-Turn RAG parameters
    MAX_HISTORY_MESSAGES: int = 10
    MAX_HISTORY_TOKENS: int = 2000
    ENABLE_CONVERSATION_SUMMARIZATION: bool = True
    SUMMARY_TRIGGER_MESSAGES: int = 10
    AUTO_TITLE_GENERATION: bool = True
    ENABLE_QUERY_REWRITE: bool = True
    RESERVED_OUTPUT_TOKENS: int = 1024
    TOTAL_MODEL_CONTEXT_LIMIT: int = 32768
    SAFETY_BUFFER_TOKENS: int = 2000


    # Adaptive TOP_K mapping based on question types
    ADAPTIVE_TOP_K: dict = {
        "Definition": 2,
        "Explanation": 2,
        "Advantages": 2,
        "Disadvantages": 2,
        "Features": 2,
        "Components": 2,
        "Architecture": 3,
        "Comparison": 3,
        "Working Process": 3,
        "Procedure": 3,
        "Summary": 3,
        "UNKNOWN": 2
    }

    @property
    def cors_origins(self) -> List[str]:
        """Parses allowed origins into a list of strings."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def upload_folder_path(self) -> str:
        """Resolves UPLOAD_FOLDER to an absolute path relative to the backend root."""
        if os.path.isabs(self.UPLOAD_FOLDER):
            return self.UPLOAD_FOLDER
        return os.path.abspath(os.path.join(BACKEND_DIR, self.UPLOAD_FOLDER))

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Pre-instantiated settings object for easy import
settings = Settings()

import contextvars
document_filter_context = contextvars.ContextVar("document_filter_context", default=None)
