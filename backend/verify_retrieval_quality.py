import sys
import os
import asyncio

# Setup app import paths
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.chroma_service import ChromaService
from app.services.retrieval_service import RetrievalService

async def main():
    print("==========================================================")
    print("AI Knowledge Assistant — Sprint 6.6 Verification Utility")
    print("==========================================================")
    
    emb_svc = EmbeddingService(settings)
    chroma_svc = ChromaService(settings)
    retrieval_svc = RetrievalService(settings)
    
    # Check collection size
    if not chroma_svc.collection_exists():
        print("Error: ChromaDB collection is not initialized.")
        return
        
    collection_size = chroma_svc.get_collection_count()
    print(f"Database Collection Size: {collection_size} chunks\n")
    
    # Representative queries
    queries = [
        "What is Cloud Computing?",
        "Advantages of cloud computing",
        "Eucalyptus private cloud software",
        "random unrelated text query"
    ]
    
    for i, q in enumerate(queries, 1):
        print(f"\nQuery {i}: \"{q}\"")
        print("=" * 60)
        
        # 1. Raw ChromaDB query details
        try:
            q_emb = emb_svc.generate_query_embedding(q.strip())
            # Fetch raw candidates (up to top_k * multiplier)
            top_k = settings.TOP_K_RESULTS
            multiplier = getattr(settings, "CANDIDATE_MULTIPLIER", 2)
            raw_k = min(collection_size, top_k * multiplier)
            
            raw_res = chroma_svc.query_collection(q_emb, raw_k)
            raw_ids = raw_res.get("ids", [[]])[0]
            raw_distances = raw_res.get("distances", [[]])[0]
            raw_metadatas = raw_res.get("metadatas", [[]])[0]
            
            print("Raw ChromaDB Query Results:")
            if not raw_ids:
                print("  No raw candidates found.")
            else:
                for idx, (cid, dist, meta) in enumerate(zip(raw_ids, raw_distances, raw_metadatas), 1):
                    raw_similarity = 1.0 - float(dist) / 2.0
                    boosted_similarity = retrieval_svc._apply_ranking_boost(q, meta["text"], raw_similarity)
                    print(f"  Candidate {idx}:")
                    print(f"    Chunk ID: {meta['chunk_id']} | Doc Name: {meta['document_name']}")
                    print(f"    Raw Distance (L2): {dist:.6f}")
                    print(f"    Calculated Similarity (raw cosine): {raw_similarity:.4f}")
                    print(f"    Boosted Similarity (lexical boost): {boosted_similarity:.4f}")
                    print(f"    Text: {repr(meta['text'][:100])}...")
        except Exception as e:
            print(f"  Failed raw query inspection: {str(e)}")
            
        print("-" * 60)
        
        # 2. Optimized Retrieval Response Flow
        try:
            resp = await retrieval_svc.retrieve_relevant_chunks(q)
            print("E2E Calibrated Retrieval Response:")
            print(f"  Success: {resp.success}")
            print(f"  Top K setting: {resp.top_k}")
            print(f"  Confidence Level: {resp.retrieval_confidence}")
            print(f"  Total Candidates: {resp.total_candidates}")
            print(f"  Filtered Candidates (skipped/below threshold): {resp.filtered_candidates}")
            print(f"  Returned Results: {resp.returned_results}")
            print(f"  Retrieval Time: {resp.retrieval_time:.4f} s")
            
            print("\n  Final Ranked Results:")
            if not resp.results:
                print("    No results returned.")
            else:
                for rank, chunk in enumerate(resp.results, 1):
                    print(f"    Rank {rank}:")
                    print(f"      Document: {chunk.document_name} (Page {chunk.page_number})")
                    print(f"      Chunk ID: {chunk.chunk_id} | Document ID: {chunk.document_id}")
                    print(f"      Similarity Score: {chunk.similarity_score:.3f}")
                    print(f"      Character Count: {chunk.character_count}")
                    print(f"      Text Preview: {repr(chunk.text[:120])}...")
        except Exception as e:
            print(f"  E2E retrieval flow failed: {str(e)}")
            
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
