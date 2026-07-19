import time
import logging
import uuid
from typing import List, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status


from app.config import Settings, settings, document_filter_context
from app.dependencies import get_settings
from app.services.answer_service import AnswerService
from app.services.document_service import DocumentService
from app.services.conversation_service import ConversationService
from app.models.response_models import (
    AnswerRequest,
    AnswerResponse,
    ErrorResponse,
    ChatSessionResponse,
    CreateSessionRequest,
    RenameSessionRequest,
    SearchResponse,
    SearchMessageResult
)

logger = logging.getLogger("app.routes.chat")
router = APIRouter(prefix="/api")

def get_answer_service(settings: Settings = Depends(get_settings)) -> AnswerService:
    """Dependency provider for the answer service."""
    return AnswerService(settings)

def get_conversation_service(settings: Settings = Depends(get_settings)) -> ConversationService:
    """Dependency provider for the conversation service."""
    return ConversationService(settings)

@router.post(
    "/chat",
    response_model=AnswerResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation failed: empty or malformed query"},
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        502: {"model": ErrorResponse, "description": "Bad gateway (Gemini API error)"},
    },
    summary="Grounded AI Assistant Chat",
    description="Accepts a user question, retrieves context, and returns a grounded response. Supports multi-turn memory if session_id is provided."
)
async def chat(
    payload: AnswerRequest,
    answer_service: AnswerService = Depends(get_answer_service),
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> AnswerResponse:
    """Handles single-turn or multi-turn conversational RAG queries."""
    start_time = time.time()
    
    session_id = payload.session_id
    question = payload.question.strip()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question string cannot be empty."
        )

    # 1. Multi-turn Session Flow
    if session_id:
        # Load active history & summary
        history_data = conversation_service.load_active_history(session_id)
        if history_data is None or not conversation_service.repository.get_session(session_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session '{session_id}' not found."
            )
            
        history = history_data["messages"]
        summary = history_data["summary"]
        
        # Resolve document filter: payload takes precedence over session filter
        doc_filter = payload.document_id if payload.document_id else history_data["document_filter"]
        if doc_filter in ("all", "None", "", None):
            doc_filter = None
        
        # Bind document filter context variable for the duration of retrieval
        token = document_filter_context.set(doc_filter)
        
        try:
            # Detect follow-up and rewrite query
            rewritten_query = conversation_service.rewrite_user_query(question, history, summary)
            
            # Orchestrate RAG answer generation
            response = await answer_service.generate_grounded_answer(
                question=question,
                rewritten_query=rewritten_query,
                conversation_summary=summary,
                recent_messages=history
            )
            
            # Record user message in DB
            user_msg_id = str(uuid.uuid4())
            user_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            conversation_service.repository.add_message({
                "message_id": user_msg_id,
                "session_id": session_id,
                "role": "user",
                "content": question,
                "timestamp": user_timestamp,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "response_time": 0.0,
                "is_summarized": False,
                "citations": []
            })
            
            # Token accounting (approx 1 token ≈ 4 characters)
            prompt_tokens = len(question) // 4
            completion_tokens = len(response.answer) // 4
            
            # Record assistant message in DB
            assistant_msg_id = str(uuid.uuid4())
            assistant_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            
            # Map AnswerSource to list of dicts for SQLite json storage
            citations_list = [
                {
                    "document_name": c.document_name,
                    "page_number": c.page_number,
                    "chunk_id": c.chunk_id,
                    "similarity_score": c.similarity_score
                }
                for c in response.sources
            ]
            
            elapsed = time.time() - start_time
            conversation_service.repository.add_message({
                "message_id": assistant_msg_id,
                "session_id": session_id,
                "role": "assistant",
                "content": response.answer,
                "timestamp": assistant_timestamp,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "response_time": elapsed,
                "is_summarized": False,
                "citations": citations_list
            })
            
            # Trigger title generation on the first turn
            if len(history) == 0:
                conversation_service.handle_title_generation(session_id, question)
                
            # Trigger summarization check
            conversation_service.handle_summarization_trigger(session_id)
            
            # Record chat time stats
            DocumentService.record_chat_time(elapsed)
            response.session_id = session_id
            return response
            
        finally:
            document_filter_context.reset(token)

    # 2. Backward-compatible Single-turn Flow (Default)
    single_doc_filter = payload.document_id
    if single_doc_filter in ("all", "None", "", None):
        single_doc_filter = None
    token = document_filter_context.set(single_doc_filter)
    try:
        response = await answer_service.generate_grounded_answer(question)
        elapsed = time.time() - start_time
        DocumentService.record_chat_time(elapsed)
        return response
    finally:
        document_filter_context.reset(token)

# --- Session Management Endpoints ---

@router.post(
    "/chat/session",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Chat Session",
    description="Creates a new chat session to enable conversational memory."
)
async def create_session(
    payload: CreateSessionRequest,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> ChatSessionResponse:
    session = conversation_service.create_session(
        title=payload.title,
        document_filter=payload.document_filter
    )
    return ChatSessionResponse(**session)

@router.get(
    "/chat/sessions",
    response_model=List[ChatSessionResponse],
    summary="List Chat Sessions",
    description="Lists all chat sessions ordered by pinned status and access time."
)
async def list_sessions(
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> List[ChatSessionResponse]:
    sessions = conversation_service.list_sessions()
    return [ChatSessionResponse(**s) for s in sessions]

@router.get(
    "/chat/session/{session_id}",
    summary="Retrieve Session History",
    description="Retrieves session metadata along with its full conversation history including citations."
)
async def get_session_history(
    session_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    session = conversation_service.repository.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session '{session_id}' not found."
        )
    messages = conversation_service.get_full_history(session_id)
    return {
        "success": True,
        "session": ChatSessionResponse(**session),
        "history": messages
    }

@router.patch(
    "/chat/session/{session_id}",
    response_model=ChatSessionResponse,
    summary="Update Session Metadata",
    description="Rename a session title or toggle favorite, pinned, or archived flags."
)
async def update_session(
    session_id: str,
    payload: RenameSessionRequest,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> ChatSessionResponse:
    session = conversation_service.repository.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session '{session_id}' not found."
        )
    updated = conversation_service.update_session_metadata(session_id, payload.model_dump())
    return ChatSessionResponse(**updated)

@router.delete(
    "/chat/session/{session_id}",
    summary="Delete Chat Session",
    description="Permanently deletes a chat session and all its associated messages and summaries."
)
async def delete_session(
    session_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    session = conversation_service.repository.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session '{session_id}' not found."
        )
    conversation_service.delete_session(session_id)
    return {
        "success": True,
        "message": f"Chat session '{session_id}' was successfully deleted."
    }

# --- Full Text Search (FTS) Endpoint ---

@router.get(
    "/chat/search",
    response_model=SearchResponse,
    summary="Search Chat History (FTS)",
    description="Uses SQLite FTS5 index to search across message contents, optionally filtered by session."
)
async def search_chat(
    query: str,
    session_id: str | None = None,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> SearchResponse:
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty."
        )
    matches = conversation_service.search_chat_history(query, session_id)
    
    results = []
    for m in matches:
        results.append(
            SearchMessageResult(
                message_id=m["message_id"],
                session_id=m["session_id"],
                session_title=m["session_title"],
                role=m["role"],
                content=m["content"],
                timestamp=m["timestamp"]
            )
        )
    return SearchResponse(
        success=True,
        query=query,
        matches=results
    )
