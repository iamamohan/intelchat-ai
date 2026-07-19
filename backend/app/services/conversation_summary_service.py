import logging
import time
import uuid
from typing import List, Dict, Any
from app.config import Settings
from app.services.llm_service import LLMService

logger = logging.getLogger("app.services.conversation_summary_service")

SUMMARIZE_PROMPT = """SYSTEM ROLE:
You are an expert conversation summarizer. Your task is to update a running summary of a chat session between a User and an Assistant, incorporating new messages while preserving all critical facts, topics, context, and entities discussed.

GUIDELINES:
1. Write a cohesive, high-level summary paragraph. Keep it factual and professional.
2. Focus on what was asked, what was answered, and what topics/documents were referenced.
3. Incorporate the existing summary if provided. Ensure the new summary covers both the old context and the new messages.
4. Keep the summary under 300 words.
5. Do NOT include preamble, explanations, or quotes. Output ONLY the summary paragraph.

INPUTS:
[Existing Summary]
{existing_summary}

[New Messages to Summarize]
{new_messages}

NEW COMBINED SUMMARY:"""

class ConversationSummaryService:
    """Service to coordinate conversation summarization of older chat history using the local LLM."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm_service = LLMService(settings)
        # Quality metrics tracking
        self.summaries_generated = 0
        self.total_summary_length = 0

    def should_summarize(self, unsummarized_messages: List[Dict[str, Any]]) -> bool:
        """Determines if the unsummarized message block exceeds configured thresholds."""
        if not self.settings.ENABLE_CONVERSATION_SUMMARIZATION:
            return False

        msg_count = len(unsummarized_messages)
        if msg_count <= self.settings.SUMMARY_TRIGGER_MESSAGES:
            return False

        # If token count is also tracked and exceeds MAX_HISTORY_TOKENS
        total_tokens = sum(m.get("prompt_tokens", 0) + m.get("completion_tokens", 0) for m in unsummarized_messages)
        if total_tokens > self.settings.MAX_HISTORY_TOKENS:
            logger.info("Summarization triggered by token count (%d > %d)", total_tokens, self.settings.MAX_HISTORY_TOKENS)
            return True

        logger.info("Summarization triggered by message count (%d > %d)", msg_count, self.settings.SUMMARY_TRIGGER_MESSAGES)
        return True

    def generate_summary(self, session_id: str, unsummarized_messages: List[Dict[str, Any]], existing_summary: str | None = None) -> str | None:
        """Summarizes older messages, updates the session's summary, and marks messages as summarized."""
        if not unsummarized_messages:
            return existing_summary

        # We keep the last 2 messages (1 user question, 1 assistant answer) as active context
        # and summarize all preceding unsummarized messages.
        messages_to_summarize = unsummarized_messages[:-2]
        if not messages_to_summarize:
            logger.info("Not enough messages to summarize (keeping 2 active).")
            return existing_summary

        start_time = time.time()

        # Format messages for the summarization prompt
        msg_lines = []
        for msg in messages_to_summarize:
            role = "User" if msg["role"] == "user" else "Assistant"
            msg_lines.append(f"{role}: {msg['content']}")
        new_messages_text = "\n".join(msg_lines)

        existing_summary_text = existing_summary if existing_summary else "No existing summary."

        prompt = SUMMARIZE_PROMPT.format(
            existing_summary=existing_summary_text,
            new_messages=new_messages_text
        )

        try:
            logger.info("Calling LLM to summarize %d messages for session %s...", len(messages_to_summarize), session_id)
            new_summary = self.llm_service.generate_response(prompt)
            new_summary_clean = new_summary.strip()
            
            if "quota exceeded" in new_summary_clean.lower() or "information notice" in new_summary_clean.lower():
                logger.warning("Conversation summary returned quota message. Keeping existing summary.")
                return existing_summary
                
            elapsed = time.time() - start_time
            logger.info("Conversation summary generated in %.4fs (Length: %d chars)", elapsed, len(new_summary_clean))
            
            self.summaries_generated += 1
            self.total_summary_length += len(new_summary_clean)
            
            return new_summary_clean
        except Exception as e:
            logger.error("Failed to generate conversation summary for session %s: %s", session_id, e)
            return None

    def get_summarized_ids(self, unsummarized_messages: List[Dict[str, Any]]) -> List[str]:
        """Returns the IDs of the messages that should be marked as summarized (all but the last 2)."""
        if len(unsummarized_messages) <= 2:
            return []
        return [m["message_id"] for m in unsummarized_messages[:-2]]

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Returns metrics about conversation summaries generated."""
        avg_summary_len = round(self.total_summary_length / self.summaries_generated, 2) if self.summaries_generated > 0 else 0.0
        return {
            "total_summaries_generated": self.summaries_generated,
            "average_summary_length_chars": avg_summary_len
        }
