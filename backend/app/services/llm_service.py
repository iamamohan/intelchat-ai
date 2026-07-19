import logging
import time
import ollama
from fastapi import HTTPException, status
from app.config import Settings

logger = logging.getLogger("app.services.llm_service")

class LLMService:
    """Service to handle interactions with the local Ollama LLM."""

    _instance = None

    def __new__(cls, settings: Settings):
        if cls._instance is None:
            cls._instance = super(LLMService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, settings: Settings):
        if self._initialized:
            logger.info("Using existing LLMService instance.")
            return
            
        self.settings = settings
        model_name = self.settings.LLM_MODEL or "qwen2.5:7b"
        logger.info("LLMService initialized once at startup. Provider: %s, Model: %s",
                    self.settings.LLM_PROVIDER, model_name)
        self._initialized = True

    def generate_response(self, prompt: str) -> str:
        """Sends the grounding prompt to Ollama and returns the generated text.
        
        Args:
            prompt: The full assembled grounding prompt.
            
        Returns:
            The text response from the model.
        """
        if not prompt or not prompt.strip():
            logger.error("Response generation failed: empty prompt.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assembled prompt is empty."
            )

        model_name = self.settings.LLM_MODEL or "qwen2.5:7b"
        logger.info("Ollama request started. Model: %s", model_name)
        start_time = time.time()
        
        try:
            stream = ollama.chat(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                stream=True,
                options={
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "num_predict": 512,
                    "repeat_penalty": 1.1
                }
            )
            
            # Assemble the streamed response before returning it
            full_text = ""
            for chunk in stream:
                if "message" in chunk and "content" in chunk["message"]:
                    full_text += chunk["message"]["content"]
            
            elapsed = time.time() - start_time
            logger.info("Ollama response assembled in %.4f seconds.", elapsed)
            
            text = full_text

            if not text or not text.strip():
                logger.warning("Ollama returned an empty response text.")
                return "I couldn't find sufficient information in the uploaded documents to answer this question."
                
            logger.info("LLM Execution Complete - Model: %s, Prompt Length: %d chars, Generation Time: %.4fs, Tokens Generated: approx %d", 
                        model_name, len(prompt), elapsed, len(text) // 4)
                
            return text.strip()
            
        except Exception as e:
            elapsed = time.time() - start_time
            err_msg = str(e)
            logger.error("Unexpected error during Ollama execution after %.4f seconds: %s", elapsed, err_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate answer from LLM: {err_msg}"
            )
