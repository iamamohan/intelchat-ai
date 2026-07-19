"""
Deep diagnostic: check what docs are in ChromaDB vs document registry, 
and test retrieval for resume-related queries.
"""
import asyncio
import logging
logging.basicConfig(level=logging.WARNING)  # quiet mode

from app.config import settings
from app.services.chroma_service import ChromaService
from app.services.embedding_service import EmbeddingService

async def main():
    chroma = ChromaService(settings)
    emb = EmbeddingService(settings)

    total = chroma.get_collection_count()
    print(f"\n=== ChromaDB Vector Count: {total} ===")

    # List all unique documents in ChromaDB
    print("\n=== All documents in ChromaDB ===")
    raw = chroma.get_collection().get(include=["metadatas"])
    doc_map = {}
    for meta in raw["metadatas"]:
        doc_id = meta.get("document_id")
        doc_name = meta.get("document_name")
        if doc_id not in doc_map:
            doc_map[doc_id] = {"name": doc_name, "chunks": 0}
        doc_map[doc_id]["chunks"] += 1

    for doc_id, info in doc_map.items():
        print(f"  doc_id={doc_id[:8]}... | name={info['name']} | chunks={info['chunks']}")

    # Test queries related to resume
    queries = [
        "tell me about this resume person",
        "resume",
        "name education experience skills",
        "who is this person",
        "curriculum vitae",
    ]

    print("\n=== Retrieval scores for queries ===")
    for query in queries:
        q_emb = emb.generate_query_embedding(query)
        results = chroma.query_collection(query_embedding=q_emb, top_k=3)
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        print(f"\n  Query: '{query}'")
        if not ids:
            print("    -> NO RESULTS")
        for i, (rid, dist, meta) in enumerate(zip(ids, distances, metas)):
            sim = max(0.0, min(1.0, 1.0 - float(dist) / 2.0))
            print(f"    [{i}] sim={sim:.3f} | doc={meta.get('document_name','?')[:40]} | text={meta.get('text','')[:60]}...")

    print(f"\n=== MIN_SIMILARITY_SCORE threshold: {settings.MIN_SIMILARITY_SCORE} ===")

if __name__ == "__main__":
    asyncio.run(main())
