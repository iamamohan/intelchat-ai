import unittest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

# Add app to path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Settings
from app.services.retrieval_service import RetrievalService
from app.models.response_models import RetrievedChunk

class TestRetrievalService(unittest.TestCase):
    def setUp(self):
        self.settings = Settings()
        self.settings.TOP_K_RESULTS = 3
        self.settings.MIN_SIMILARITY_SCORE = 0.40
        self.settings.CANDIDATE_MULTIPLIER = 2
        
        # Patch external dependencies (EmbeddingService, ChromaService)
        self.patcher_emb = patch('app.services.retrieval_service.EmbeddingService')
        self.patcher_chroma = patch('app.services.retrieval_service.ChromaService')
        
        self.mock_emb_class = self.patcher_emb.start()
        self.mock_chroma_class = self.patcher_chroma.start()
        
        self.mock_emb = MagicMock()
        self.mock_chroma = MagicMock()
        
        self.mock_emb_class.return_value = self.mock_emb
        self.mock_chroma_class.return_value = self.mock_chroma
        
        self.retrieval_service = RetrievalService(self.settings)

    def tearDown(self):
        self.patcher_emb.stop()
        self.patcher_chroma.stop()

    def test_query_validation_empty(self):
        """Query validation should reject empty or whitespace-only queries."""
        with self.assertRaises(HTTPException) as ctx:
            self.retrieval_service._validate_query("")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("cannot be empty", ctx.exception.detail)

        with self.assertRaises(HTTPException) as ctx:
            self.retrieval_service._validate_query("   ")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_query_validation_too_short(self):
        """Query validation should reject queries shorter than 3 characters."""
        with self.assertRaises(HTTPException) as ctx:
            self.retrieval_service._validate_query("ab")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("too short", ctx.exception.detail)

    def test_query_validation_too_long(self):
        """Query validation should reject queries longer than 1000 characters."""
        long_query = "a" * 1001
        with self.assertRaises(HTTPException) as ctx:
            self.retrieval_service._validate_query(long_query)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("too long", ctx.exception.detail)

    def test_query_validation_valid(self):
        """Query validation should pass and return stripped query for valid inputs."""
        res = self.retrieval_service._validate_query("  What is Cloud Computing?  ")
        self.assertEqual(res, "What is Cloud Computing?")

    def test_metadata_validation_success(self):
        """Metadata validation should pass if all required fields are present."""
        valid_metadata = {
            "document_id": "doc123",
            "chunk_id": 1,
            "page_number": 2,
            "document_name": "unit_1.pdf",
            "text": "sample text content",
            "character_count": 19
        }
        # Should not raise any exception
        self.retrieval_service._validate_metadata(valid_metadata)

    def test_metadata_validation_missing_fields(self):
        """Metadata validation should raise 500 HTTPException if a field is missing or None."""
        invalid_metadata = {
            "document_id": "doc123",
            "chunk_id": None, # Should trigger validation error
            "page_number": 2,
            "document_name": "unit_1.pdf",
            "text": "sample text content",
            "character_count": 19
        }
        with self.assertRaises(HTTPException) as ctx:
            self.retrieval_service._validate_metadata(invalid_metadata)
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("missing required field 'chunk_id'", ctx.exception.detail)

        # Check metadata is None
        with self.assertRaises(HTTPException) as ctx:
            self.retrieval_service._validate_metadata(None)
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("metadata object is None", ctx.exception.detail)

    def test_compute_confidence(self):
        """Should return HIGH, MEDIUM, or LOW depending on the score threshold (HIGH >= 0.70, MEDIUM >= 0.50)."""
        self.assertEqual(self.retrieval_service._compute_confidence(0.85), "HIGH")
        self.assertEqual(self.retrieval_service._compute_confidence(0.70), "HIGH")
        self.assertEqual(self.retrieval_service._compute_confidence(0.69), "MEDIUM")
        self.assertEqual(self.retrieval_service._compute_confidence(0.50), "MEDIUM")
        self.assertEqual(self.retrieval_service._compute_confidence(0.49), "LOW")
        self.assertEqual(self.retrieval_service._compute_confidence(0.10), "LOW")

    def test_apply_ranking_boost(self):
        """Lexical ranking boost should correctly identify definition cues and term matching."""
        # Query: "What is Cloud Computing?"
        # Chunk 1 contains both key terms ("cloud", "computing") and definition indicator ("is the")
        text1 = "Introduction. Cloud Computing is the delivery of computing services..."
        score1 = 0.71
        boosted1 = self.retrieval_service._apply_ranking_boost("What is Cloud Computing?", text1, score1)
        # Term match: +0.04, Definition cue: +0.03. Total = +0.07. Expected = 0.78
        self.assertAlmostEqual(boosted1, 0.78)

        # Chunk 2 contains "cloud" but not "computing" and no definition indicators
        text2 = "A cloud platform enables easy web deployment."
        score2 = 0.75
        boosted2 = self.retrieval_service._apply_ranking_boost("What is Cloud Computing?", text2, score2)
        # Only "cloud" matches (1 of 2 key terms). Ratio = 0.5 -> boost +0.02. No definition cue -> boost +0.0. Expected = 0.77
        self.assertAlmostEqual(boosted2, 0.77)

    async def test_retrieve_relevant_chunks_flow(self):
        """Tests the complete retrieval flow including deduplication, thresholding, and stats."""
        # Setup mock db and embed returns
        self.mock_chroma.collection_exists.return_value = True
        self.mock_chroma.get_collection_count.return_value = 1000
        self.mock_emb.generate_query_embedding.return_value = [0.1, 0.2, 0.3]
        
        # Mock database search results containing duplicates and low scores.
        # We query top_k * CANDIDATE_MULTIPLIER = 3 * 2 = 6 candidates.
        # Distances:
        # 1. dist = 0.50 (sim = 1 - 0.5/2 = 0.75), text="cloud introduction", id="c1"
        # 2. dist = 0.50 (sim = 1 - 0.5/2 = 0.75), text="cloud introduction", id="c1" (duplicate text and doc/chunk id)
        # 3. dist = 0.55 (sim = 1 - 0.55/2 = 0.725), text="cloud characteristics", id="c2"
        # 4. dist = 0.60 (sim = 1 - 0.6/2 = 0.70), text="cloud delivery models", id="c3"
        # 5. dist = 1.40 (sim = 1 - 1.4/2 = 0.30), text="unrelated content", id="c4" (below similarity score threshold of 0.40)
        # 6. dist = 0.60 (sim = 1 - 0.6/2 = 0.70), text="cloud introduction", id="c5" (duplicate text of chunk 1)
        search_results = {
            "ids": [["c1", "c2", "c3", "c4", "c5", "c6"]],
            "distances": [[0.50, 0.50, 0.55, 0.60, 1.40, 0.60]],
            "metadatas": [[
                {"document_id": "doc1", "chunk_id": 1, "page_number": 1, "document_name": "u1.pdf", "text": "cloud introduction", "character_count": 18},
                {"document_id": "doc1", "chunk_id": 1, "page_number": 1, "document_name": "u1.pdf", "text": "cloud introduction", "character_count": 18},
                {"document_id": "doc1", "chunk_id": 2, "page_number": 1, "document_name": "u1.pdf", "text": "cloud characteristics", "character_count": 21},
                {"document_id": "doc1", "chunk_id": 3, "page_number": 2, "document_name": "u1.pdf", "text": "cloud delivery models", "character_count": 21},
                {"document_id": "doc2", "chunk_id": 1, "page_number": 1, "document_name": "u2.pdf", "text": "unrelated content", "character_count": 17},
                {"document_id": "doc1", "chunk_id": 4, "page_number": 2, "document_name": "u1.pdf", "text": "cloud introduction", "character_count": 18},
            ]]
        }
        self.mock_chroma.query_collection.return_value = search_results

        # Run E2E retrieval
        resp = await self.retrieval_service.retrieve_relevant_chunks("What is Cloud?")
        
        self.assertTrue(resp.success)
        self.assertEqual(resp.query, "What is Cloud?")
        self.assertEqual(resp.top_k, 3)
        self.assertEqual(resp.total_candidates, 6)
        
        # After filtering:
        # - "unrelated content" (Similarity 0.30) skipped because of threshold.
        # - Duplicate c2 ("cloud introduction", doc1, 1) skipped.
        # - Duplicate c6 (different ID, but identical text "cloud introduction") skipped.
        # Remaining: "cloud introduction" (0.75 + boost), "cloud characteristics" (0.725 + boost), "cloud delivery models" (0.70 + boost).
        self.assertEqual(resp.returned_results, 3)
        self.assertEqual(resp.filtered_candidates, 3) # 6 - 3 = 3
        
        self.assertEqual(len(resp.results), 3)
        self.assertEqual(resp.results[0].text, "cloud introduction")
        self.assertEqual(resp.results[1].text, "cloud characteristics")
        self.assertEqual(resp.results[2].text, "cloud delivery models")
        
        # Highest score is > 0.70, so confidence should be HIGH
        self.assertEqual(resp.retrieval_confidence, "HIGH")

async def run_async_test():
    import asyncio
    suite = unittest.TestSuite()
    suite.addTest(TestRetrievalService('test_query_validation_empty'))
    suite.addTest(TestRetrievalService('test_query_validation_too_short'))
    suite.addTest(TestRetrievalService('test_query_validation_too_long'))
    suite.addTest(TestRetrievalService('test_query_validation_valid'))
    suite.addTest(TestRetrievalService('test_metadata_validation_success'))
    suite.addTest(TestRetrievalService('test_metadata_validation_missing_fields'))
    suite.addTest(TestRetrievalService('test_compute_confidence'))
    suite.addTest(TestRetrievalService('test_apply_ranking_boost'))
    
    ts = TestRetrievalService()
    ts.setUp()
    try:
        await ts.test_retrieve_relevant_chunks_flow()
        print("test_retrieve_relevant_chunks_flow: PASSED")
    finally:
        ts.tearDown()
        
    runner = unittest.TextTestRunner()
    runner.run(suite)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_async_test())
