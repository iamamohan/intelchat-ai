import logging
import time
import re
from typing import List
from fastapi import HTTPException, status
from app.config import Settings
from app.services.retrieval_service import RetrievalService
from app.services.prompt_service import PromptService
from app.services.llm_service import LLMService
from app.models.response_models import AnswerResponse, AnswerSource

logger = logging.getLogger("app.services.answer_service")

class AnswerService:
    """Service to coordinate the full RAG pipeline: retrieval, prompt building, LLM execution, and response validation."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.retrieval_service = RetrievalService(settings)
        self.prompt_service = PromptService()
        self.llm_service = LLMService(settings)

    def validate_answer_keywords(self, answer: str, context_text: str, question: str = "") -> bool:
        """Extracts and verifies that generated answer keywords appear in the retrieved context or query."""
        # Only true grammatical/function stop words — do NOT include domain/topic words here.
        # Domain words (cloud, computing, features, etc.) must remain so the grounding check works.
        stop_words = {
            "what", "is", "are", "the", "a", "an", "of", "to", "in", "for", "with",
            "on", "at", "by", "about", "how", "why", "where", "who", "would",
            "should", "could", "from", "this", "that", "these", "those",
            "them", "then", "there", "they", "been", "have", "were", "will", "your",
            "cannot", "however", "under", "other", "thereby", "therefore",
            "here", "above", "below", "following", "also", "which", "their",
            "when", "than", "more", "some", "such", "into", "over", "after"
        }
        
        # Extract words of 4+ characters
        answer_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', answer.lower()))
        answer_keywords = {w for w in answer_words if w not in stop_words}
        
        context_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', context_text.lower()))
        context_keywords = {w for w in context_words if w not in stop_words}
        
        question_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', question.lower()))
        question_keywords = {w for w in question_words if w not in stop_words}
        
        # Combined allowed keywords from context and the question itself
        allowed_keywords = context_keywords.union(question_keywords)
        
        if not answer_keywords:
            return True  # Short answers/fallback or no keywords to validate
            
        matched_keywords = answer_keywords.intersection(allowed_keywords)
        match_ratio = len(matched_keywords) / len(answer_keywords)
        
        logger.info("Answer keywords check: Matched %d/%d (Ratio: %.2f) of generated keywords against allowed keywords.", 
                    len(matched_keywords), len(answer_keywords), match_ratio)
        
        # Require that at least 15% of answer's keywords exist in the allowed set.
        # LLMs rephrase and synthesize — a strict threshold incorrectly discards valid grounded answers.
        if match_ratio < 0.15:
            logger.warning("Answer validation failed: generated words fail grounding threshold. Unmatched words: %s", 
                           answer_keywords - allowed_keywords)
            return False
            
        return True

    def validate_answer(self, answer: str, context_text: str, question: str = "") -> bool:
        """Runs validation checks on LLM generated answers to ensure grounding and formatting health."""
        if not answer or not answer.strip():
            logger.warning("Answer validation failed: Empty or whitespace response.")
            return False
            
        fallback_msg = "I couldn't find sufficient information in the uploaded documents to answer this question."
        if answer.strip().lower() == fallback_msg.lower():
            return True
            
        # 1. Check for duplicate paragraphs
        paragraphs = [p.strip() for p in answer.split("\n\n") if p.strip()]
        seen_paragraphs = set()
        for p in paragraphs:
            if p.lower() in seen_paragraphs:
                logger.warning("Answer validation failed: Repeated paragraph detected.")
                return False
            seen_paragraphs.add(p.lower())
            
        # 2. Check for duplicate sentences
        for p in paragraphs:
            sentences = re.split(r'(?<=[.!?])\s+', p)
            seen_sentences = set()
            for s in sentences:
                s_clean = s.strip()
                if not s_clean:
                    continue
                if s_clean.lower() in seen_sentences:
                    logger.warning("Answer validation failed: Repeated sentence detected: '%s'", s_clean[:50])
                    return False
                seen_sentences.add(s_clean.lower())
                
        # 3. Check for grounded keywords mapping to context
        if not self.validate_answer_keywords(answer, context_text, question):
            return False
            
        return True

    async def generate_grounded_answer(
        self, 
        question: str,
        rewritten_query: str | None = None,
        conversation_summary: str | None = None,
        recent_messages: List[dict] | None = None
    ) -> AnswerResponse:
        """Coordinates RAG pipeline to generate grounded answer for user question.
        
        Args:
            question: The user's original question query.
            rewritten_query: Optional standalone rewritten question for retrieval.
            conversation_summary: Optional conversation summary.
            recent_messages: Optional list of recent messages.
            
        Returns:
            AnswerResponse detailing success status, original query, generated answer,
            retrieval confidence, sources, and total pipeline response time.
        """
        start_time = time.time()
        fallback_msg = "I couldn't find sufficient information in the uploaded documents to answer this question."
        logger.info("RAG chat pipeline started for question: '%s'", question)

        query_for_retrieval = rewritten_query if rewritten_query else question

        # 1. Retrieval
        retrieval_start = time.time()
        try:
            retrieval_resp = await self.retrieval_service.retrieve_relevant_chunks(query_for_retrieval)
            retrieval_time = time.time() - retrieval_start
            logger.info("Retrieval phase complete using query: '%s'. Found %d sources. Confidence: %s. Retrieval Time: %.4fs", 
                        query_for_retrieval, len(retrieval_resp.results), retrieval_resp.retrieval_confidence, retrieval_time)
        except HTTPException as e:
            if e.status_code == status.HTTP_404_NOT_FOUND:
                logger.warning("No documents retrieved for question: '%s'", question)
                elapsed = round(time.time() - start_time, 4)
                return AnswerResponse(
                    success=True,
                    question=question,
                    answer=fallback_msg,
                    retrieval_confidence="LOW",
                    sources=[],
                    response_time=elapsed
                )
            raise e
        except Exception as e:
            logger.exception("Unexpected failure during retrieval phase of RAG pipeline.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Retrieval phase failed: {str(e)}"
            )

        if not retrieval_resp.results:
            elapsed = round(time.time() - start_time, 4)
            return AnswerResponse(
                success=True,
                question=question,
                answer=fallback_msg,
                retrieval_confidence="LOW",
                sources=[],
                response_time=elapsed
            )

        # 2. Multi-factor Confidence/Weak Retrieval Check
        highest_score = retrieval_resp.results[0].similarity_score if retrieval_resp.results else 0.0
        is_weak_confidence = retrieval_resp.retrieval_confidence == "LOW"
        is_weak_similarity = highest_score < 0.25
        is_few_sources = len(retrieval_resp.results) <= 1

        is_weak_retrieval = is_weak_confidence and is_weak_similarity and is_few_sources
        
        if is_weak_retrieval:
            logger.info("Multi-factor check determined weak retrieval (Confidence: %s, Max similarity: %.3f, Source count: %d). Returning fallback response.",
                        retrieval_resp.retrieval_confidence, highest_score, len(retrieval_resp.results))
            elapsed = round(time.time() - start_time, 4)
            return AnswerResponse(
                success=True,
                question=question,
                answer=fallback_msg,
                retrieval_confidence=retrieval_resp.retrieval_confidence,
                sources=[
                    AnswerSource(
                        document_name=chunk.document_name,
                        page_number=chunk.page_number,
                        chunk_id=chunk.chunk_id,
                        similarity_score=chunk.similarity_score
                    )
                    for chunk in retrieval_resp.results
                ],
                response_time=elapsed
            )

        # 3. Prompt Builder
        prompt_build_start = time.time()
        try:
            prompt, question_type, context_char_len = self.prompt_service.build_grounded_prompt(
                question, retrieval_resp.results, conversation_summary, recent_messages
            )
            prompt_build_time = time.time() - prompt_build_start
        except Exception as e:
            logger.exception("Failed to build prompt.")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Prompt builder failed: {str(e)}"
            )

        # 4. LLM execution
        llm_start = time.time()
        try:
            answer = self.llm_service.generate_response(prompt)
            llm_time = time.time() - llm_start
        except Exception as e:
            logger.exception("Failed to generate answer from LLM.")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"LLM execution failed: {str(e)}"
            )

        # Combine source texts for keyword verification
        combined_context_text = " ".join([c.text for c in retrieval_resp.results])

        # 5. Answer Validation Check
        if "information notice" in answer.lower() and "quota exceeded" in answer.lower():
            is_answer_valid = True
        else:
            is_answer_valid = self.validate_answer(answer, combined_context_text, question)
        
        # If the LLM returned a partial fallback or validation check failed, force standard fallback
        if "couldn't find sufficient information" in answer.lower() or not is_answer_valid:
            logger.warning("Generated answer failed validation or matches fallback text. Overriding with standard fallback.")
            answer = fallback_msg

        # 6. Final Response and Source Attribution
        sources = [
            AnswerSource(
                document_name=chunk.document_name,
                page_number=chunk.page_number,
                chunk_id=chunk.chunk_id,
                similarity_score=chunk.similarity_score
            )
            for chunk in retrieval_resp.results
        ]
        
        elapsed_time = round(time.time() - start_time, 4)
        
        # Log Pipeline Metrics concisely
        logger.info(
            "RAG Pipeline execution metrics:\n"
            "  Question Type: %s\n"
            "  Prompt Length: %d characters\n"
            "  Context Length: %d characters\n"
            "  Retrieved Source Count: %d\n"
            "  LLM Response Time: %.4f seconds\n"
            "  Generated Answer Length: %d characters\n"
            "  Total Pipeline Time: %.4f seconds",
            question_type,
            len(prompt),
            context_char_len,
            len(sources),
            llm_time,
            len(answer),
            elapsed_time
        )

        # Record conversation quality metrics
        is_fallback = answer == fallback_msg
        from app.services.conversation_service import ConversationService
        ConversationService.record_pipeline_metrics(
            prompt_chars=len(prompt),
            context_chars=context_char_len,
            source_count=len(sources),
            is_fallback=is_fallback
        )
        
        return AnswerResponse(
            success=True,
            question=question,
            answer=answer,
            retrieval_confidence=retrieval_resp.retrieval_confidence,
            sources=sources,
            response_time=elapsed_time
        )

    async def stream_grounded_answer(
        self,
        question: str,
        rewritten_query: str | None = None,
        conversation_summary: str | None = None,
        recent_messages: List[dict] | None = None
    ):
        """Asynchronous generator stub for streaming grounded answers.
        
        This is prepared for Sprint 10 to yield token chunks.
        """
        # For now, raising NotImplementedError satisfies future-proof placeholder requirements
        raise NotImplementedError("Streaming answers is planned for Sprint 10.")

