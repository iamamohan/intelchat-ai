import unittest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

# Add app to path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Settings
from app.services.prompt_service import PromptService
from app.services.llm_service import LLMService
from app.services.answer_service import AnswerService
from app.models.response_models import RetrievedChunk

class TestRAGPipeline(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = Settings()
        self.settings.GEMINI_API_KEY = "test_key_123"
        self.settings.LLM_PROVIDER = "gemini"
        self.settings.LLM_MODEL = "gemini-2.5-flash"
        
        self.prompt_service = PromptService()

    def test_prompt_generation_success(self):
        """PromptService should format prompt with source chunks and instructions."""
        chunks = [
            RetrievedChunk(
                document_id="doc1",
                chunk_id=1,
                page_number=2,
                document_name="doc_a.pdf",
                text="ChromaDB is a vector database.",
                character_count=29,
                similarity_score=0.88
            )
        ]
        prompt = self.prompt_service.build_grounded_prompt("What is ChromaDB?", chunks)
        
        self.assertIn("SYSTEM INSTRUCTIONS:", prompt)
        self.assertIn("--- SOURCE CHUNK 1 ---", prompt)
        self.assertIn("Document: doc_a.pdf (Page 2)", prompt)
        self.assertIn("Content: ChromaDB is a vector database.", prompt)
        self.assertIn("USER QUESTION:\nWhat is ChromaDB?", prompt)
        self.assertIn("I couldn't find sufficient information", prompt)

    def test_prompt_generation_empty_query(self):
        """PromptService should reject empty query."""
        with self.assertRaises(HTTPException) as ctx:
            self.prompt_service.build_grounded_prompt("", [MagicMock()])
        self.assertEqual(ctx.exception.status_code, 400)

    def test_prompt_generation_empty_context(self):
        """PromptService should reject empty context chunks."""
        with self.assertRaises(HTTPException) as ctx:
            self.prompt_service.build_grounded_prompt("query", [])
        self.assertEqual(ctx.exception.status_code, 400)

    @patch('google.generativeai.GenerativeModel')
    @patch('google.generativeai.configure')
    def test_llm_service_initialization(self, mock_configure, mock_model_class):
        """LLMService should initialize configure and GenerativeModel singletons exactly once."""
        # Reset class attributes
        LLMService._configured = False
        LLMService._model_instance = None
        
        llm_service = LLMService(self.settings)
        
        mock_configure.assert_called_once_with(api_key="test_key_123")
        mock_model_class.assert_called_once_with("gemini-2.5-flash")
        
        # Instantiate second time - should not call configure or model creation again
        llm_service2 = LLMService(self.settings)
        mock_configure.assert_called_once()
        mock_model_class.assert_called_once()

    @patch('google.generativeai.GenerativeModel')
    @patch('google.generativeai.configure')
    def test_llm_service_generate_response_success(self, mock_configure, mock_model_class):
        """LLMService should send prompt and return stripped text output."""
        LLMService._configured = True
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "  ChromaDB is a database.  "
        mock_model.generate_content.return_value = mock_response
        LLMService._model_instance = mock_model
        
        llm_service = LLMService(self.settings)
        result = llm_service.generate_response("Test prompt")
        
        self.assertEqual(result, "ChromaDB is a database.")
        mock_model.generate_content.assert_called_once()

    @patch('google.generativeai.GenerativeModel')
    @patch('google.generativeai.configure')
    def test_llm_service_generate_response_blocked_fallback(self, mock_configure, mock_model_class):
        """LLMService should return fallback text if generation is blocked or fails property access."""
        LLMService._configured = True
        mock_model = MagicMock()
        mock_response = MagicMock()
        
        # Simulating property raise when response is blocked or safety triggers
        type(mock_response).text = property(lambda self: (_ for _ in ()).throw(ValueError("Blocked content")))
        mock_model.generate_content.return_value = mock_response
        LLMService._model_instance = mock_model
        
        llm_service = LLMService(self.settings)
        result = llm_service.generate_response("Test prompt")
        
        self.assertEqual(result, "I couldn't find sufficient information in the uploaded documents to answer this question.")

    @patch('app.services.answer_service.RetrievalService')
    @patch('app.services.answer_service.LLMService')
    async def test_answer_service_no_retrieval_matches_fallback(self, mock_llm_class, mock_retrieval_class):
        """AnswerService should return grounded fallback response immediately if retrieval is empty."""
        mock_retrieval = MagicMock()
        # Simulate HTTPException 404 (No matching chunks found)
        mock_retrieval.retrieve_relevant_chunks.side_effect = HTTPException(status_code=404, detail="No matching documents")
        mock_retrieval_class.return_value = mock_retrieval
        
        answer_service = AnswerService(self.settings)
        resp = await answer_service.generate_grounded_answer("Unrelated topic")
        
        self.assertTrue(resp.success)
        self.assertEqual(resp.answer, "I couldn't find sufficient information in the uploaded documents to answer this question.")
        self.assertEqual(resp.retrieval_confidence, "LOW")
        self.assertEqual(len(resp.sources), 0)

if __name__ == "__main__":
    unittest.main()
