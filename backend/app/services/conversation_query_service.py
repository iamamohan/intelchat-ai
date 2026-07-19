import logging
import time
from typing import List, Dict, Any
from app.config import Settings
from app.services.llm_service import LLMService

logger = logging.getLogger("app.services.conversation_query_service")

REWRITE_PROMPT = """SYSTEM ROLE:
You are an expert search query generator. Your task is to analyze a conversation history and a user's follow-up question, and rewrite the follow-up question into a single, standalone query that contains all necessary context for a document retrieval system.

GUIDELINES:
1. Do NOT answer the question. Only output the rewritten standalone query.
2. The standalone query must stand on its own without needing the conversation history.
3. Incorporate key topics, entities, and context from the conversation summary and recent messages.
4. Keep the rewritten query concise, factual, and search-optimized (e.g. "What are the advantages of Cloud Computing?" instead of "What are its advantages?").
5. If the follow-up question is already standalone or if the history does not add any relevant context to it, return the user's current question EXACTLY as-is.
6. Do NOT add any quotes, preamble, formatting, or explanation. Only return the final query.

INPUTS:
[Conversation Summary]
{summary}

[Recent Messages]
{history}

[Current Question]
{question}

STANDALONE QUERY:"""

class ConversationQueryService:
    """Service responsible only for transforming follow-up queries into standalone retrieval queries."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm_service = LLMService(settings)
        # Statistics tracking
        self.rewrite_attempts = 0
        self.rewrite_successes = 0
        self.total_rewrite_length = 0

    def rewrite_query(self, question: str, history: List[Dict[str, Any]], summary: str | None = None) -> str:
        """Transforms a follow-up question into a standalone query using Gemini."""
        if not self.settings.ENABLE_QUERY_REWRITE:
            logger.info("Query rewriting is disabled. Using original question.")
            return question

        if not history:
            logger.info("History is empty. Query rewriting skipped, using original question.")
            return question

        start_time = time.time()
        self.rewrite_attempts += 1

        # Format recent history (limit to last 3 messages)
        recent_messages = history[-3:]
        history_lines = []
        for msg in recent_messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_lines.append(f"{role}: {msg['content']}")
        history_text = "\n".join(history_lines)

        summary_text = summary if summary else "No summary available."

        prompt = REWRITE_PROMPT.format(
            summary=summary_text,
            history=history_text,
            question=question
        )

        try:
            rewritten = self.llm_service.generate_response(prompt)
            # Remove any wrapping double/single quotes that LLM sometimes outputs
            rewritten_clean = rewritten.strip().strip('"').strip("'").strip()
            
            if "quota exceeded" in rewritten_clean.lower() or "information notice" in rewritten_clean.lower():
                logger.warning("Query rewrite returned quota message. Falling back to original question.")
                return question
            
            elapsed = time.time() - start_time
            logger.info("Query rewrite completed in %.4fs. Original: '%s' -> Standalone: '%s'", elapsed, question, rewritten_clean)
            
            self.rewrite_successes += 1
            self.total_rewrite_length += len(rewritten_clean)
            return rewritten_clean
        except Exception as e:
            logger.error("Failed to rewrite query using Gemini, fallback to original question. Error: %s", e)
            return question

    def get_rewrite_metrics(self) -> Dict[str, Any]:
        """Returns metrics about query rewriting performance."""
        avg_len = round(self.total_rewrite_length / self.rewrite_successes, 2) if self.rewrite_successes > 0 else 0.0
        success_rate = round(self.rewrite_successes / self.rewrite_attempts, 4) if self.rewrite_attempts > 0 else 1.0
        return {
            "average_query_rewrite_length": avg_len,
            "query_rewrite_success_rate": success_rate,
            "query_rewrite_attempts": self.rewrite_attempts
        }
