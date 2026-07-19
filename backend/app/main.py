import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
from app.routes import health, upload, chat, retrieve, documents, statistics

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("app.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for server start and stop."""
    logger.info("Initializing AI Knowledge Assistant Backend service...")
    logger.info(f"Service Name: {settings.APP_NAME}")
    logger.info(f"Service Version: {settings.APP_VERSION}")
    logger.info(f"Resolved Upload Folder: {settings.upload_folder_path}")
    logger.info(f"Configured Max Upload Size: {settings.MAX_UPLOAD_SIZE} bytes")
    logger.info(f"CORS Allowed Origins: {settings.cors_origins}")
    
    # Initialize services and log registry version and health status
    from app.services.document_service import DocumentService
    from app.services.chroma_service import ChromaService
    from app.services.conversation_service import ConversationService
    doc_service = DocumentService(settings)
    chroma_service = ChromaService(settings)
    conv_service = ConversationService(settings)
    logger.info(f"Document Registry Version: {doc_service.DOCUMENT_REGISTRY_VERSION}")
    doc_service.run_startup_health_checks(chroma_service)

    
    api_key_status = "Configured" if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip() else "Missing"
    logger.info(f"LLM Provider Selected: {settings.LLM_PROVIDER}")
    logger.info(f"LLM Model: {settings.LLM_MODEL}")
    logger.info(f"LLM API Key Status: {api_key_status}")
    yield
    logger.info("Shutting down AI Knowledge Assistant Backend service...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API Foundation for the AI Knowledge Assistant (RAG) platform.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(retrieve.router)
app.include_router(documents.router)
app.include_router(statistics.router)

# --- Global Exception Handlers for Standardized Outputs ---

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Catches FastAPI HTTPExceptions (like validation limits, 404s, etc.),
    logs them appropriately, and formats them into the standard error schema.
    """
    if exc.status_code >= 500:
        logger.error(f"Internal HTTP exception at {request.method} {request.url.path}: {exc.detail}")
    else:
        logger.warning(f"HTTP exception at {request.method} {request.url.path} (Status {exc.status_code}): {exc.detail}")
        
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Catches Pydantic request validation exceptions (missing headers, body parsing errors),
    logs details, and returns a sanitized bad request response.
    """
    errors = exc.errors()
    logger.warning(f"Request validation error at {request.method} {request.url.path}: {errors}")
    
    # Construct a descriptive error list
    error_details = []
    for error in errors:
        loc = ".".join(str(element) for element in error.get("loc", []))
        msg = error.get("msg", "Validation failed")
        error_details.append(f"Field '{loc}' - {msg}")
    
    joined_msg = "; ".join(error_details) if error_details else "Invalid request body content."
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": joined_msg
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Wildcard exception handler to prevent leak of raw traceback details.
    Logs the exception with stack trace.
    """
    logger.error(f"Unhandled exception at {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error."
        }
    )

# EOF12
