import logging
from typing import List, Tuple
from app.models.response_models import RetrievedChunk
from fastapi import HTTPException, status

logger = logging.getLogger("app.services.prompt_service")

# Specialized formatting rules for different question types
FORMATTING_RULES = {
    "Definition": (
        "Format the answer as a Definition: Start with a clear Markdown Heading (## Definition) "
        "followed by a concise, accurate definition paragraph. Bold key terms on first mention."
    ),
    "Explanation": (
        "Format the answer as an Explanation: Use a clear Markdown Heading (## Explanation) and explain "
        "the concepts in detail using logical paragraphs, subheadings (###), and bold key terms."
    ),
    "Advantages": (
        "Format the answer as a list of Advantages: Use a bulleted list where each advantage has a "
        "bold title and a brief description (e.g., - **Advantage Name**: Description)."
    ),
    "Disadvantages": (
        "Format the answer as a list of Disadvantages: Use a bulleted list where each disadvantage has a "
        "bold title and a brief description (e.g., - **Disadvantage Name**: Description)."
    ),
    "Comparison": (
        "Format the answer as a Comparison: Use a Markdown table to compare the key aspects side-by-side. "
        "Ensure columns are clearly labeled and the table is properly formatted."
    ),
    "Difference": (
        "Format the answer as a Difference: Highlight the differences using a Markdown table or a "
        "structured comparative list with bold headings comparing the items."
    ),
    "List": (
        "Format the answer as a List: Use a bulleted or numbered list to present the items clearly, "
        "bolding the key items or terms."
    ),
    "Steps / Procedure": (
        "Format the answer as a Steps/Procedure: Use a numbered list (1., 2., 3.) detailing the "
        "sequential steps or instructions to be followed."
    ),
    "Architecture": (
        "Format the answer as an Architecture explanation: Provide a component-wise or layer-by-layer "
        "explanation. Use subheadings (###) for each component and describe its role/structure."
    ),
    "Features": (
        "Format the answer as a list of Features: Use a bulleted list with bold titles for each "
        "feature and a brief explanation."
    ),
    "Working Process": (
        "Format the answer as a Working Process: Use a numbered list (1., 2., 3.) or sequential flow "
        "description with bold keywords to explain how the system or process works."
    ),
    "Components": (
        "Format the answer as Components: Provide a component-wise description, using subheadings (###) "
        "or a bulleted list with bold component names."
    ),
    "Example": (
        "Format the answer as an Example: Provide concrete examples or illustrations from the context. "
        "Use code blocks or blockquotes if relevant, and bold key elements."
    ),
    "Summary": (
        "Format the answer as a Summary: Provide a short, concise paragraph summarizing the key points "
        "of the context. Keep it high-level."
    ),
    "UNKNOWN": (
        "Format the answer using clear and structured Markdown. Use appropriate headings, bold text, "
        "or lists to make the answer highly readable and professional."
    )
}

class PromptService:
    """Minimal PromptService. Responsible only for question classification and RAG prompt layout assembly."""

    PROMPT_VERSION = "7.5.0"

    def classify_question(self, question: str) -> str:
        """Lightweight rule-based question classifier.
        
        Returns one of the supported question types, defaulting to 'UNKNOWN'.
        """
        q = question.lower().strip()
        
        # 1. Difference & Comparison
        if any(p in q for p in ["difference between", "differences between", "distinguish between", "diff between"]):
            return "Difference"
        if any(p in q for p in ["compare", "comparison", " versus", " vs ", " vs. ", "contrast"]):
            return "Comparison"
            
        # 2. Steps / Procedure / Working Process
        if any(p in q for p in ["how to", "steps to", "procedure for", "step-by-step", "process of"]):
            return "Steps / Procedure"
        if any(p in q for p in ["how does", "how do", "working of", "working process", "mechanism of"]):
            return "Working Process"
            
        # 3. Advantages & Disadvantages
        if any(p in q for p in ["disadvantage", "drawback", "con of", "cons of", "limitation", "weakness"]):
            return "Disadvantages"
        if any(p in q for p in ["advantage", "benefit", "pro of", "pros of", "plus point", "strength"]):
            return "Advantages"
            
        # 4. Definition
        if any(q.startswith(p) for p in ["what is", "what are", "define", "meaning of", "definition of"]):
            return "Definition"
        if any(p in q for p in [" what is ", " what are ", " meaning of ", " definition of "]):
            return "Definition"
            
        # 5. Architecture & Components
        if any(p in q for p in ["architecture", "design of", "structural layout"]):
            return "Architecture"
        if any(p in q for p in ["component", "part of", "parts of", "element", "module"]):
            return "Components"
            
        # 6. List
        if any(p in q for p in ["list of", "list the", "enumerate", "name the", "types of", "kinds of"]):
            return "List"
            
        # 7. Features
        if any(p in q for p in ["features", "characteristic", "property", "properties"]):
            return "Features"
            
        # 8. Example
        if any(p in q for p in ["example", "illustration", "instance", "sample"]):
            return "Example"
            
        # 9. Summary
        if any(p in q for p in ["summarize", "summary", "brief of", "overview of", "synopsis"]):
            return "Summary"
            
        # 10. Explanation (catch-all for explanation-seeking questions)
        if any(p in q for p in ["explain", "describe", "why ", "how is", "how are"]):
            return "Explanation"
            
        return "UNKNOWN"

    def build_grounded_prompt(
        self, 
        question: str, 
        chunks: List[RetrievedChunk],
        conversation_summary: str | None = None,
        recent_messages: List[dict] | None = None
    ) -> Tuple[str, str, int]:
        """Assembles the final grounding RAG prompt from the provided cleaned chunks, summary, and history.
        
        Args:
            question: The user's query.
            chunks: A list of already cleaned, ranked, and sorted context chunks.
            conversation_summary: Optional cumulative conversation summary.
            recent_messages: Optional list of recent messages.
            
        Returns:
            A tuple of (prompt_string, question_type, context_character_length).
        """
        if not question or not question.strip():
            logger.error("Prompt generation failed: User question is empty.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User question cannot be empty for prompt construction."
            )
            
        if not chunks:
            logger.error("Prompt generation failed: Retrieved chunks list is empty.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No context chunks available for prompt construction."
            )

        logger.info("Prompt generation started. Version: %s", self.PROMPT_VERSION)

        # Classify question type to fetch appropriate formatting instructions
        question_type = self.classify_question(question)
        logger.info("Question classified as: %s", question_type)

        # Simple linear assembly of context blocks without modifications
        context_entries = []
        for idx, chunk in enumerate(chunks, 1):
            context_entries.append(
                f"--- SOURCE CHUNK {idx} ---\n"
                f"Document: {chunk.document_name} (Page {chunk.page_number})\n"
                f"Content: {chunk.text}\n"
            )
        context_str = "\n".join(context_entries)
        context_char_len = len(context_str)

        formatting_rules = FORMATTING_RULES.get(question_type, FORMATTING_RULES["UNKNOWN"])

        # Format recent history
        history_str = ""
        if recent_messages:
            history_lines = []
            for msg in recent_messages:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_lines.append(f"{role}: {msg['content']}")
            history_str = "\n".join(history_lines)
        else:
            history_str = "No recent messages."

        summary_str = conversation_summary if conversation_summary else "No summary available."

        prompt = (
            "SYSTEM: You are a precise AI assistant. Answer using ONLY the provided CONTEXT.\n"
            "If the context lacks the answer, reply EXACTLY: "
            "\"I couldn't find sufficient information in the uploaded documents to answer this question.\"\n\n"
            f"SUMMARY:\n{summary_str}\n\n"
            f"HISTORY:\n{history_str}\n\n"
            f"FORMAT: {formatting_rules}\n\n"
            "CONTEXT:\n"
            f"{context_str}\n\n"
            "QUESTION:\n"
            f"{question}\n\n"
            "ANSWER:"
        )
        
        logger.info("Prompt generated successfully. Length: %d characters. Context Length: %d characters.", 
                    len(prompt), context_char_len)
        return prompt, question_type, context_char_len

