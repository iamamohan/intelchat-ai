import os
import uuid
import time
import logging
from typing import List, Dict, Any
from app.config import Settings, BACKEND_DIR
from app.services.conversation_repository import ConversationRepository
from app.services.conversation_query_service import ConversationQueryService
from app.services.conversation_summary_service import ConversationSummaryService
from app.services.llm_service import LLMService

logger = logging.getLogger("app.services.conversation_service")

TITLE_PROMPT = """SYSTEM ROLE:
You are a session title generator. Your task is to generate a concise, professional title (maximum 4 words) based on the user's first question. Do NOT use quotes, punctuation, or preamble. Return ONLY the title.

QUESTION:
{question}

TITLE:"""

class ConversationService:
    """Service to coordinate session lifecycles, follow-up detection, query rewriting, summaries, and metrics."""

    _repo_instance = None
    # Class-level running totals for metrics not easily gathered from DB
    _follow_up_count = 0
    _total_queries = 0
    _prompt_sizes = []
    _context_sizes = []
    _sources_used = []
    _fallback_count = 0

    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Resolve DB path and instantiate repository singleton
        if ConversationService._repo_instance is None:
            db_path = settings.DOCUMENT_REGISTRY_PATH
            if not os.path.isabs(db_path):
                db_path = os.path.abspath(os.path.join(BACKEND_DIR, db_path))
            ConversationService._repo_instance = ConversationRepository(db_path)
            
        self.repository = ConversationService._repo_instance
        self.query_service = ConversationQueryService(settings)
        self.summary_service = ConversationSummaryService(settings)
        self.llm_service = LLMService(settings)

    # --- Session CRUD ---

    def create_session(self, title: str | None = None, document_filter: str | None = None) -> Dict[str, Any]:
        """Creates a new session and persists it in SQLite."""
        session_id = str(uuid.uuid4())
        created_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        session_dict = {
            "session_id": session_id,
            "title": title if title else "New Chat",
            "created_time": created_time,
            "updated_time": created_time,
            "message_count": 0,
            "document_filter": document_filter,
            "summary": None,
            "status": "active",
            "last_accessed": created_time,
            "total_tokens": 0,
            "favorite": False,
            "archived": False,
            "pinned": False
        }
        self.repository.create_session(session_dict)
        logger.info("Session Created: ID=%s, Title='%s'", session_id, session_dict["title"])
        return session_dict

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Retrieves a session's details and updates its last_accessed timestamp."""
        session = self.repository.get_session(session_id)
        if not session:
            logger.warning("Session %s not found.", session_id)
            return None
        
        # Update last_accessed timestamp
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.repository.update_session(session_id, {"last_accessed": now})
        session["last_accessed"] = now
        logger.info("Session Access: ID=%s, Title='%s'", session_id, session["title"])
        return session

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lists all sessions from the database."""
        return self.repository.list_sessions()

    def update_session_metadata(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates session title or metadata flags (pinned, favorite, archived)."""
        session = self.repository.get_session(session_id)
        if not session:
            return None
            
        allowed_updates = ["title", "favorite", "pinned", "archived"]
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_updates and v is not None}
        
        if not filtered_updates:
            return session
            
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        filtered_updates["updated_time"] = now
        self.repository.update_session(session_id, filtered_updates)
        
        # Log meta updates
        for field in ["pinned", "favorite", "archived"]:
            if field in filtered_updates:
                logger.info("Pinned/Favorite Status Updates: Session %s field '%s' updated to %s", session_id, field, filtered_updates[field])
        if "title" in filtered_updates:
            logger.info("Session Renamed: Session %s title updated to '%s'", session_id, filtered_updates["title"])
            
        return self.repository.get_session(session_id)

    def delete_session(self, session_id: str) -> None:
        """Permanently deletes a session and its cascading child records."""
        self.repository.delete_session(session_id)
        logger.info("Session Deleted: ID=%s", session_id)

    # --- History Loading & Processing ---

    def load_active_history(self, session_id: str) -> Dict[str, Any]:
        """Loads cumulative summary and unsummarized messages for active context building."""
        session = self.repository.get_session(session_id)
        if not session:
            return {"summary": None, "messages": []}
            
        messages = self.repository.get_session_messages(session_id, include_summarized=False)
        logger.info("History Loaded: Session %s loaded %d active messages.", session_id, len(messages))
        return {
            "summary": session["summary"],
            "messages": messages,
            "document_filter": session["document_filter"]
        }

    def get_full_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Loads all messages for the session including summarized ones (used for chat transcript display)."""
        return self.repository.get_session_messages(session_id, include_summarized=True)

    # --- Query Rewriting & Follow-up ---

    def is_follow_up_question(self, question: str) -> bool:
        """Determines if the question is a follow-up query based on patterns and lengths."""
        q = question.strip().lower()
        import re
        q_clean = re.sub(r'[^\w\s\?]', '', q)
        words = q_clean.split()
        
        # Very short questions or single words are follow-ups
        if len(words) <= 3:
            ConversationService._follow_up_count += 1
            logger.info("Follow-up Detected (Short query): '%s'", question)
            return True
            
        generic_indicators = [
            "what is this document about", "summarize this document",
            "explain this file", "what is this", "tell me about this document",
            "summarize the file"
        ]
        if any(g in q_clean for g in generic_indicators):
            return False
            
        # Follow-up indicators
        indicators = [
            "advantages", "disadvantages", "features", "components", "architecture",
            "working", "process", "difference", "differences", "comparison", "compare",
            "working process", "working mechanism", "example", "examples", "explain more",
            "elaborate", "give example", "tell me more", "how about", "what about",
            "why", "how", "pros", "cons", "drawbacks", "benefits", "continue", "yes", "no"
        ]
        if any(indicator in q_clean for indicator in indicators):
            ConversationService._follow_up_count += 1
            logger.info("Follow-up Detected (Keyword match): '%s'", question)
            return True
            
        return False

    def rewrite_user_query(self, question: str, history: List[Dict[str, Any]], summary: str | None = None) -> str:
        """Coordinates standalone query generation."""
        ConversationService._total_queries += 1
        is_follow_up = self.is_follow_up_question(question)
        
        if is_follow_up or self.settings.ENABLE_QUERY_REWRITE:
            rewritten = self.query_service.rewrite_query(question, history, summary)
            logger.info("Conversation Query Rewrite: Original '%s' -> Standalone '%s'", question, rewritten)
            return rewritten
            
        return question

    # --- Summarization Coordination ---

    def handle_summarization_trigger(self, session_id: str) -> None:
        """Checks if active history exceeds limits, generating and persisting summary if needed."""
        active_history = self.repository.get_session_messages(session_id, include_summarized=False)
        
        # Calculate active history token length
        # Using 1 token ≈ 4 characters approximation for triggers
        total_chars = sum(len(m["content"]) for m in active_history)
        approx_tokens = total_chars // 4
        
        # Fake token fields just in case they are 0
        total_tokens = sum(m.get("prompt_tokens", 0) + m.get("completion_tokens", 0) for m in active_history)
        token_count = max(total_tokens, approx_tokens)

        # Build a temporary settings context mapping
        exceeds_messages = len(active_history) > self.settings.SUMMARY_TRIGGER_MESSAGES
        exceeds_tokens = token_count > self.settings.MAX_HISTORY_TOKENS
        
        if self.settings.ENABLE_CONVERSATION_SUMMARIZATION and (exceeds_messages or exceeds_tokens):
            session = self.repository.get_session(session_id)
            new_summary = self.summary_service.generate_summary(session_id, active_history, session["summary"])
            
            if new_summary:
                now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                summary_id = str(uuid.uuid4())
                
                # Save summary to SQLite
                self.repository.add_summary(summary_id, session_id, new_summary, now)
                
                # Mark old messages as summarized
                summarized_ids = self.summary_service.get_summarized_ids(active_history)
                self.repository.mark_messages_as_summarized(session_id, summarized_ids)
                logger.info("Conversation Summary Created: Session %s updated summary.", session_id)

    # --- Title Generation ---

    def handle_title_generation(self, session_id: str, first_question: str) -> None:
        """Automatically generates session title on the first user message using the local LLM."""
        if not self.settings.AUTO_TITLE_GENERATION:
            return
            
        session = self.repository.get_session(session_id)
        if not session or session["title"] != "New Chat":
            return
            
        try:
            prompt = TITLE_PROMPT.format(question=first_question)
            title = self.llm_service.generate_response(prompt)
            clean_title = title.strip().strip('"').strip("'").strip()
            
            if "quota exceeded" in clean_title.lower() or "information notice" in clean_title.lower():
                logger.warning("Auto-title generation returned quota message. Skipping title update.")
                return
                
            if clean_title:
                # Limit title length to 5 words
                clean_title = " ".join(clean_title.split()[:5])
                self.repository.update_session(session_id, {"title": clean_title})
                logger.info("Session Title Auto-Generated: '%s' for session %s", clean_title, session_id)
        except Exception as e:
            logger.error("Failed to auto-generate session title: %s", e)

    # --- FTS Search ---

    def search_chat_history(self, query: str, session_id: str | None = None) -> List[Dict[str, Any]]:
        """Invokes full-text search across messages."""
        logger.info("FTS Search: query='%s', session_id=%s", query, session_id)
        return self.repository.search_messages(query, session_id)

    # --- Token Budget Management ---

    def calculate_token_budget(self, summary: str | None, history: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculates dynamic context space allocations based on configured limits."""
        total_limit = self.settings.TOTAL_MODEL_CONTEXT_LIMIT
        safety_buffer = self.settings.SAFETY_BUFFER_TOKENS
        reserved_output = self.settings.RESERVED_OUTPUT_TOKENS

        # Estimate summary tokens (approx 1 token ≈ 4 characters)
        summary_tokens = len(summary) // 4 if summary else 0
        
        # Estimate recent history tokens
        history_tokens = sum(len(m["content"]) for m in history) // 4
        
        # Calculate available budget for RAG context
        available_budget = total_limit - safety_buffer - reserved_output - summary_tokens - history_tokens
        
        # Ensure available budget is never negative
        available_budget = max(0, available_budget)
        
        # We also enforce that history shouldn't consume the entire window
        max_history_budget = self.settings.MAX_HISTORY_TOKENS
        
        logger.info(
            "Token Budget Management:\n"
            "  Total Context Limit: %d tokens\n"
            "  Safety Buffer: %d tokens\n"
            "  Reserved Output: %d tokens\n"
            "  Summary Context: %d tokens\n"
            "  History Context: %d tokens (Max Limit: %d)\n"
            "  Available Context Budget: %d tokens",
            total_limit, safety_buffer, reserved_output, summary_tokens, history_tokens, max_history_budget, available_budget
        )
        
        return {
            "total_limit": total_limit,
            "safety_buffer": safety_buffer,
            "reserved_output": reserved_output,
            "summary_tokens": summary_tokens,
            "history_tokens": history_tokens,
            "available_budget": available_budget
        }

    # --- Quality Metrics & Statistics ---

    @classmethod
    def record_pipeline_metrics(cls, prompt_chars: int, context_chars: int, source_count: int, is_fallback: bool) -> None:
        """Records metrics for average calculations."""
        cls._prompt_sizes.append(prompt_chars)
        cls._context_sizes.append(context_chars)
        cls._sources_used.append(source_count)
        if is_fallback:
            cls._fallback_count += 1
            
        # Cap list sizes at 100 entries to prevent memory growth
        for metric_list in [cls._prompt_sizes, cls._context_sizes, cls._sources_used]:
            if len(metric_list) > 100:
                metric_list.pop(0)

    def get_conversation_quality_metrics(self) -> Dict[str, Any]:
        """Compiles quality metrics for Sprint 9 dashboard statistics."""
        # 1. Base DB stats
        db_stats = self.repository.get_chat_analytics()
        
        # 2. Add class-level averages
        avg_prompt = round(sum(self._prompt_sizes) / len(self._prompt_sizes), 2) if self._prompt_sizes else 0.0
        avg_context = round(sum(self._context_sizes) / len(self._context_sizes), 2) if self._context_sizes else 0.0
        avg_sources = round(sum(self._sources_used) / len(self._sources_used), 2) if self._sources_used else 0.0
        
        # 3. Add Query Rewriting metrics
        rewrite_metrics = self.query_service.get_rewrite_metrics()
        
        # 4. Add summary metrics
        summary_metrics = self.summary_service.get_summary_metrics()
        
        # 5. Follow-up detection rate
        follow_up_rate = round(ConversationService._follow_up_count / max(1, ConversationService._total_queries), 4)

        # Merge all metrics
        metrics = {
            **db_stats,
            **rewrite_metrics,
            **summary_metrics,
            "average_prompt_size_chars": avg_prompt,
            "average_retrieved_context_size_chars": avg_context,
            "average_number_of_sources_used": avg_sources,
            "follow_up_detection_rate": follow_up_rate,
            "fallback_response_rate": db_stats.get("fallback_response_rate", 0.0)
        }
        
        logger.info("Conversation Quality Metrics fetched successfully.")
        return metrics
