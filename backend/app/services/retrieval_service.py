import time
import logging
import re
from typing import List, Dict, Any, Set, Tuple
from fastapi import HTTPException, status

from app.config import Settings
from app.services.embedding_service import EmbeddingService
from app.services.chroma_service import ChromaService
from app.models.response_models import RetrievedChunk, RetrievalResponse
from app.services.prompt_service import PromptService

logger = logging.getLogger("app.services.retrieval_service")

# Keywords for Intent Matching boost and chunk classification
INTENT_KEYWORDS = {
    "Definition": ["define", "definition", "meaning", "is defined as", "refers to", "means"],
    "Explanation": ["explain", "explanation", "describe", "why", "because", "how"],
    "Advantages": ["advantage", "advantages", "benefit", "benefits", "pro", "pros", "strength", "strengths"],
    "Disadvantages": ["disadvantage", "disadvantages", "drawback", "drawbacks", "con", "cons", "limitation", "limitations"],
    "Comparison": ["compare", "comparison", "versus", "vs", "contrast"],
    "Difference": ["difference", "differences", "distinguish", "differ", "differs", "contrast"],
    "List": ["list", "enumerate", "types", "kinds", "categories"],
    "Steps / Procedure": ["step", "steps", "procedure", "process", "sequence", "how to"],
    "Architecture": ["architecture", "design", "layout", "structure"],
    "Features": ["feature", "features", "characteristic", "characteristics", "property", "properties"],
    "Working Process": ["work", "works", "how does", "mechanism", "process", "flow"],
    "Components": ["component", "components", "part", "parts", "element", "elements"],
    "Example": ["example", "examples", "e.g.", "such as", "instance", "illustration"],
    "Summary": ["summary", "summarize", "overview", "brief", "outline"]
}

class RetrievalCache:
    """In-memory LRU cache with TTL expiration for query retrieval responses."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = {}  # key -> (response_val, expiry_time, last_accessed_time)

    def _normalize_key(self, question: str) -> str:
        """Normalizes query key to prevent whitespace/case mismatches."""
        if not question:
            return ""
        q = question.lower().strip()
        q = re.sub(r'[^\w\s]', '', q)
        return " ".join(q.split())

    def get(self, question: str) -> RetrievalResponse | None:
        key = self._normalize_key(question)
        if not key:
            return None
        if key in self.cache:
            val, expiry, _ = self.cache[key]
            if time.time() > expiry:
                del self.cache[key]
                return None
            # Update access time for LRU tracking
            self.cache[key] = (val, expiry, time.time())
            return val
        return None

    def set(self, question: str, response: RetrievalResponse) -> None:
        key = self._normalize_key(question)
        if not key:
            return
        # Evict oldest entry if size is exceeded
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][2])
            del self.cache[oldest_key]
        expiry = time.time() + self.ttl_seconds
        self.cache[key] = (response, expiry, time.time())


class RetrievalService:
    """Service to coordinate query embedding generation and semantic search against ChromaDB."""

    RETRIEVAL_VERSION = "8.0.0"
    _cache_instance = None
    _retrieval_times = []

    def __init__(self, settings: Settings):
        self.settings = settings
        self.embedding_service = EmbeddingService(settings)
        self.chroma_service = ChromaService(settings)
        self.prompt_service = PromptService()
        
        # Share cache across service reinstantiations
        if RetrievalService._cache_instance is None:
            RetrievalService._cache_instance = RetrievalCache(
                max_size=settings.CACHE_SIZE,
                ttl_seconds=settings.CACHE_TTL_SECONDS
            )
        self.cache = RetrievalService._cache_instance

    def _validate_query(self, query: str) -> str:
        """Validates the input search query according to length constraints."""
        if not query or not query.strip():
            logger.warning("Query validation failed: Empty or whitespace-only query.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query string cannot be empty or whitespace-only."
            )
            
        query_stripped = query.strip()
        
        if len(query_stripped) < 3:
            logger.warning("Query validation failed: Query is too short (%d chars).", len(query_stripped))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query is too short. Minimum length is 3 characters (provided: {len(query_stripped)})."
            )
            
        if len(query_stripped) > 1000:
            logger.warning("Query validation failed: Query is too long (%d chars).", len(query_stripped))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query is too long. Maximum length is 1000 characters (provided: {len(query_stripped)})."
            )
            
        return query_stripped

    def _validate_metadata(self, metadata: Dict[str, Any] | None) -> None:
        """Validates that all required fields exist in ChromaDB document metadata."""
        if metadata is None:
            logger.error("Corrupted metadata detected: metadata object is None")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Corrupted retrieval metadata: metadata object is None."
            )
            
        required_fields = [
            "document_id",
            "chunk_id",
            "page_number",
            "document_name",
            "text",
            "character_count"
        ]
        for field in required_fields:
            if field not in metadata or metadata[field] is None:
                logger.error("Corrupted metadata detected. Missing required field: '%s' in metadata: %s", field, metadata)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Corrupted retrieval metadata: missing required field '{field}'."
                )

    def _compute_confidence(self, highest_score: float) -> str:
        """Computes retrieval confidence level based on highest similarity score."""
        if highest_score >= 0.70:
            return "HIGH"
        elif highest_score >= 0.50:
            return "MEDIUM"
        else:
            return "LOW"

    def get_chunk_category(self, text: str) -> str:
        """Classifies a chunk text into one of the key categories for diversity filtering."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["architecture", "design", "layout", "structure"]):
            return "Architecture"
        if any(w in text_lower for w in ["step", "steps", "procedure", "process", "sequence", "how to"]):
            return "Procedure"
        if any(w in text_lower for w in ["define", "definition", "meaning", "is defined as", "refers to", "means"]):
            return "Definition"
        if any(w in text_lower for w in ["example", "examples", "e.g.", "such as", "instance", "illustration"]):
            return "Example"
        if any(w in text_lower for w in ["explain", "explanation", "describe", "why", "because", "how"]):
            return "Explanation"
        return "Other"

    def calculate_weighted_score(self, query: str, text: str, similarity_score: float, question_type: str) -> Tuple[float, dict]:
        """Calculates a composite ranking score based on weighted criteria."""
        text_lower = text.lower()
        
        # 1. Similarity Score (65% weight)
        sim_component = similarity_score * 0.65
        
        # 2. Question Intent Match (15% weight)
        intent_match = False
        if question_type != "UNKNOWN" and question_type in INTENT_KEYWORDS:
            intent_match = any(word in text_lower for word in INTENT_KEYWORDS[question_type])
        intent_component = 0.15 if intent_match else 0.0
        
        # 3. Heading Match (10% weight)
        heading_match = any(line.strip().startswith('#') for line in text.split('\n') if line.strip())
        heading_component = 0.10 if heading_match else 0.0
        
        # 4. Definition Detection (5% weight)
        has_def = any(pattern in text_lower for pattern in ["is defined as", "refers to", "defined as", "meaning of", "definition of"])
        def_component = 0.05 if has_def else 0.0
        
        # 5. Keyword Density (5% weight)
        query_words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
        stop_words = {"what", "is", "are", "the", "a", "an", "of", "to", "in", "for", "with", "on", "at", "by", "about"}
        keywords = [w for w in query_words if w not in stop_words]
        if keywords:
            matches = sum(1 for kw in keywords if kw in text_lower)
            density = matches / len(keywords)
        else:
            density = 0.0
        density_component = density * 0.05
        
        weighted_score = sim_component + intent_component + heading_component + def_component + density_component
        
        breakdown = {
            "similarity": round(sim_component, 4),
            "intent": round(intent_component, 4),
            "heading": round(heading_component, 4),
            "definition": round(def_component, 4),
            "density": round(density_component, 4),
            "total": round(weighted_score, 4)
        }
        
        return weighted_score, breakdown

    def apply_diversity_filter(self, chunks: List[RetrievedChunk], top_k: int) -> List[RetrievedChunk]:
        """Applies limits to category composition to ensure context diversity (max 2 per key category)."""
        if not chunks or len(chunks) <= 2:
            return chunks
            
        selected: List[RetrievedChunk] = []
        category_counts = {
            "Definition": 0,
            "Explanation": 0,
            "Example": 0,
            "Architecture": 0,
            "Procedure": 0,
            "Other": 0
        }
        
        # First pass: Collect up to 2 items per category to preserve diversity
        for chunk in chunks:
            cat = self.get_chunk_category(chunk.text)
            # Enforce limit of 2 for key categories (except 'Other' which is unconstrained here)
            if cat == "Other" or category_counts[cat] < 2:
                selected.append(chunk)
                category_counts[cat] += 1
                if len(selected) >= top_k:
                    break
                    
        # Fill remaining slots up to top_k from the sorted candidate pool
        if len(selected) < top_k:
            for chunk in chunks:
                if chunk not in selected:
                    selected.append(chunk)
                    if len(selected) >= top_k:
                        break
                        
        return selected

    def compress_chunks(self, chunks: List[RetrievedChunk]) -> Tuple[List[RetrievedChunk], int]:
        """Performs sentence-level overlap removal and compression without merging chunks."""
        seen_sentences = set()
        seen_paragraphs = set()
        seen_headings = set()
        
        compressed_chunks = []
        duplicate_count = 0
        
        for chunk in chunks:
            paragraphs = chunk.text.split("\n\n")
            unique_paragraphs = []
            
            for p in paragraphs:
                p_clean = p.strip()
                if not p_clean:
                    continue
                    
                # Remove repeated paragraphs
                p_lower = p_clean.lower()
                if p_lower in seen_paragraphs:
                    duplicate_count += 1
                    continue
                seen_paragraphs.add(p_lower)
                
                # Check for repeated headings
                is_heading = p_clean.startswith('#') or (len(p_clean) < 60 and '\n' not in p_clean and any(p_clean.startswith(c) for c in ['1.', '2.', '3.']))
                if is_heading:
                    if p_lower in seen_headings:
                        duplicate_count += 1
                        continue
                    seen_headings.add(p_lower)
                
                # Sentence-level overlap checking
                sentences = re.split(r'(?<=[.!?])\s+', p_clean)
                unique_sentences = []
                
                for s in sentences:
                    s_clean = s.strip()
                    if not s_clean:
                        continue
                    s_lower = s_clean.lower()
                    # Normalize string to strip punctuation/spaces for matching robustness
                    s_norm = re.sub(r'[^\w]', '', s_lower)
                    if not s_norm:
                        continue
                        
                    if s_norm in seen_sentences:
                        duplicate_count += 1
                        continue
                    seen_sentences.add(s_norm)
                    unique_sentences.append(s_clean)
                    
                if unique_sentences:
                    unique_paragraphs.append(" ".join(unique_sentences))
                    
            if unique_paragraphs:
                cleaned_text = "\n\n".join(unique_paragraphs)
                compressed_chunk = RetrievedChunk(
                    document_id=chunk.document_id,
                    chunk_id=chunk.chunk_id,
                    page_number=chunk.page_number,
                    document_name=chunk.document_name,
                    text=cleaned_text,
                    character_count=len(cleaned_text),
                    similarity_score=chunk.similarity_score
                )
                compressed_chunks.append(compressed_chunk)
                
        return compressed_chunks, duplicate_count

    def enforce_context_limits(self, chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        """Enforces MAX_CONTEXT_CHUNKS and MAX_CONTEXT_CHARACTERS constraints strictly."""
        # 1. Respect count limit
        chunks_pool = chunks[:self.settings.MAX_CONTEXT_CHUNKS]
        
        # 2. Respect character limit (discarding lowest-ranked chunks completely if they exceed the size)
        selected_chunks = []
        current_chars = 0
        
        for chunk in chunks_pool:
            overhead = len(f"--- SOURCE CHUNK {len(selected_chunks) + 1} ---\nDocument: {chunk.document_name} (Page {chunk.page_number})\nContent: \n\n")
            chunk_len = len(chunk.text) + overhead
            
            if current_chars + chunk_len <= self.settings.MAX_CONTEXT_CHARACTERS:
                selected_chunks.append(chunk)
                current_chars += chunk_len
            else:
                logger.info("Context size limit exceeded. Discarding remaining %d chunks completely to maintain integrity.", 
                            len(chunks_pool) - len(selected_chunks))
                break
                
        return selected_chunks

    def calculate_context_quality_score(self, chunks: List[RetrievedChunk], initial_chars: int, duplicate_removed: int) -> int:
        """Calculates context quality score between 0 and 100 based on composite metrics."""
        if not chunks:
            return 0
            
        # Component 1: Average similarity (40%)
        avg_similarity = sum(c.similarity_score for c in chunks) / len(chunks)
        sim_score = avg_similarity * 40
        
        # Component 2: Context Diversity (20%)
        categories = {self.get_chunk_category(c.text) for c in chunks}
        # Score scales with unique categories present up to 5 categories
        diversity_score = (min(5, len(categories)) / 5.0) * 20
        
        # Component 3: Compression ratio (20%)
        final_chars = sum(len(c.text) for c in chunks)
        compression_ratio = max(0.0, 1.0 - (final_chars / max(1, initial_chars)))
        compression_score = compression_ratio * 20
        
        # Component 4: Duplicate removal rate (20%)
        total_elements = sum(len(re.split(r'(?<=[.!?])\s+', c.text)) for c in chunks) + duplicate_removed
        dup_rate = duplicate_removed / max(1, total_elements)
        dup_score = min(20.0, dup_rate * 20)
        
        quality_score = int(sim_score + diversity_score + compression_score + dup_score)
        return max(0, min(100, quality_score))

    async def retrieve_relevant_chunks(self, query: str, document_id: str | None = None) -> RetrievalResponse:
        """Coordinates retrieval, ranking, diversity filtering, compression, caching, and diagnostics, with optional document filtering."""
        logger.info("Retrieval started. Version: %s", self.RETRIEVAL_VERSION)
        start_time = time.time()

        # 1. Cache Lookup (Bypass cache if document_id filter is applied to prevent caching collision)
        if self.settings.ENABLE_RETRIEVAL_CACHE and not document_id:
            cached_resp = self.cache.get(query)
            if cached_resp:
                logger.info("Retrieval Cache HIT for query: '%s'", query)
                if hasattr(cached_resp, "retrieval_time"):
                    cached_resp.retrieval_time = round(time.time() - start_time, 4)
                return cached_resp
            logger.info("Retrieval Cache MISS for query: '%s'", query)

        # 2. Validate query
        query_stripped = self._validate_query(query)

        # 3. Check db collections count
        try:
            if not self.chroma_service.collection_exists():
                logger.error("Retrieval failed: ChromaDB collection is not initialized.")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Vector database collection is not initialized."
                )
            
            collection_count = self.chroma_service.get_collection_count()
            if collection_count == 0:
                logger.warning("Retrieval failed: ChromaDB collection is empty.")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No indexed documents found."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Failed to verify collection status")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database connectivity issue: {str(e)}"
            )

        # 4. Sizing Adaptive TOP-K Query Size
        question_type = self.prompt_service.classify_question(query_stripped)
        adaptive_top_k = self.settings.ADAPTIVE_TOP_K.get(question_type, self.settings.DEFAULT_TOP_K)
        logger.info("Adaptive TOP-K size determined: %d chunks for type '%s'", adaptive_top_k, question_type)

        # Fetch extra candidates from database to rank and filter them
        multiplier = getattr(self.settings, "CANDIDATE_MULTIPLIER", 2)
        candidates_to_retrieve = min(collection_count, adaptive_top_k * multiplier)

        # 5. Query ChromaDB
        db_start = time.time()
        attempt = 1
        max_attempts = 3
        unique_chunks: List[RetrievedChunk] = []
        raw_candidates_count = 0
        pre_duplicate_removed = 0
        
        try:
            query_embedding = self.embedding_service.generate_query_embedding(query_stripped)
            while len(unique_chunks) < adaptive_top_k and candidates_to_retrieve <= collection_count and attempt <= max_attempts:
                logger.info("ChromaDB search started. Attempt %d: Fetching top %d candidate vectors.", attempt, candidates_to_retrieve)
                search_results = self.chroma_service.query_collection(
                    query_embedding=query_embedding,
                    top_k=candidates_to_retrieve,
                    document_id=document_id
                )
                
                ids = search_results.get("ids", [[]])[0]
                metadatas = search_results.get("metadatas", [[]])[0]
                distances = search_results.get("distances", [[]])[0]
                
                raw_candidates_count = len(ids)
                if not ids:
                    break
                    
                seen_texts = set()
                seen_ids = set()
                current_unique = []
                temp_dup = 0
                
                for doc_id, metadata, distance in zip(ids, metadatas, distances):
                    self._validate_metadata(metadata)
                    
                    text_key = metadata["text"].strip().lower()
                    id_key = (metadata["document_id"], int(metadata["chunk_id"]))
                    if text_key in seen_texts or id_key in seen_ids:
                        temp_dup += 1
                        continue
                    seen_texts.add(text_key)
                    seen_ids.add(id_key)
                    
                    similarity_score = max(0.0, min(1.0, 1.0 - float(distance) / 2.0))
                    similarity_score = round(similarity_score, 3)
                    
                    if similarity_score < self.settings.MIN_SIMILARITY_SCORE:
                        continue
                    
                    chunk = RetrievedChunk(
                        document_id=metadata["document_id"],
                        chunk_id=int(metadata["chunk_id"]),
                        page_number=int(metadata["page_number"]),
                        document_name=metadata["document_name"],
                        text=metadata["text"],
                        character_count=int(metadata["character_count"]),
                        similarity_score=similarity_score
                    )
                    current_unique.append(chunk)
                    
                unique_chunks = current_unique
                pre_duplicate_removed = temp_dup
                
                if len(unique_chunks) >= adaptive_top_k or candidates_to_retrieve >= collection_count:
                    break
                    
                attempt += 1
                candidates_to_retrieve = min(collection_count, candidates_to_retrieve * 2)
                
        except Exception as e:
            logger.exception("ChromaDB query execution failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to execute semantic search in database: {str(e)}"
            )
            
        retrieval_time_elapsed = time.time() - db_start
        retrieved_candidates = raw_candidates_count
        raw_chunks = unique_chunks

        if not raw_chunks:
            logger.warning("No matching documents found in ChromaDB.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No matching document chunks found for the query."
            )

        # 6. Weighted Chunk Ranking
        ranking_start = time.time()
        scored_candidates: List[Tuple[RetrievedChunk, float]] = []
        for chunk in raw_chunks:
            weighted_score, breakdown = self.calculate_weighted_score(
                query_stripped, chunk.text, chunk.similarity_score, question_type
            )
            logger.info("Ranked Chunk ID %d: Weighted Score: %.4f, Breakdown: %s", 
                        chunk.chunk_id, weighted_score, breakdown)
            scored_candidates.append((chunk, weighted_score))

        # Sort candidate list descending using weighted score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        ranked_chunks = [item[0] for item in scored_candidates]
        ranking_time_elapsed = time.time() - ranking_start

        # 7. Context Diversity Filter
        if self.settings.ENABLE_DIVERSITY_FILTER:
            filtered_chunks = self.apply_diversity_filter(ranked_chunks, adaptive_top_k)
        else:
            filtered_chunks = ranked_chunks[:adaptive_top_k]

        # Keep initial character count for compression ratio calculations
        initial_chars = sum(len(c.text) for c in filtered_chunks)

        # 8. Context Compression (Overlap and sentence removal)
        compression_start = time.time()
        duplicate_removed = 0
        if self.settings.ENABLE_CONTEXT_COMPRESSION:
            compressed_chunks, duplicate_removed = self.compress_chunks(filtered_chunks)
        else:
            compressed_chunks = filtered_chunks
        compression_time_elapsed = time.time() - compression_start
        total_duplicate_removed = pre_duplicate_removed + duplicate_removed

        # 9. Enforce limits (Respect MAX_CONTEXT_CHUNKS and MAX_CONTEXT_CHARACTERS)
        final_chunks = self.enforce_context_limits(compressed_chunks)

        # Sort and inject document-aware context grouping headers
        final_chunks.sort(key=lambda x: (x.document_name, x.page_number, x.chunk_id))
        seen_docs = {}
        doc_counter = 1
        for chunk in final_chunks:
            if chunk.document_name not in seen_docs:
                seen_docs[chunk.document_name] = doc_counter
                chunk.text = f"===== DOCUMENT =====\n{chunk.document_name}\n\n{chunk.text}"
                doc_counter += 1

        # 10. Diagnostics and Context Quality Score
        final_chars = sum(len(c.text) for c in final_chunks)
        compression_ratio = round(1.0 - (final_chars / max(1, initial_chars)), 4) if initial_chars > 0 else 0.0
        
        quality_score = self.calculate_context_quality_score(final_chunks, initial_chars, total_duplicate_removed)
        
        highest_similarity = final_chunks[0].similarity_score if final_chunks else 0.0
        lowest_similarity = final_chunks[-1].similarity_score if final_chunks else 0.0
        avg_similarity = sum(c.similarity_score for c in final_chunks) / len(final_chunks) if final_chunks else 0.0
        confidence = self._compute_confidence(highest_similarity)

        total_time_elapsed = time.time() - start_time

        # Log diagnostics metrics concisely
        logger.info(
            "Retrieval Diagnostics Log:\n"
            "  Retrieval Version: %s\n"
            "  Question Type: %s\n"
            "  Adaptive TOP-K: %d\n"
            "  Retrieved Candidates: %d\n"
            "  Duplicate Chunks Removed: %d\n"
            "  Context Compression Ratio: %.4f\n"
            "  Final Chunk Count: %d\n"
            "  Final Context Characters: %d\n"
            "  Average Similarity: %.4f\n"
            "  Highest Similarity: %.4f\n"
            "  Lowest Similarity: %.4f\n"
            "  Context Quality Score: %d\n"
            "  Retrieval Time: %.4fs\n"
            "  Ranking Time: %.4fs\n"
            "  Compression Time: %.4fs\n"
            "  Total Retrieval Time: %.4fs",
            self.RETRIEVAL_VERSION,
            question_type,
            adaptive_top_k,
            retrieved_candidates,
            total_duplicate_removed,
            compression_ratio,
            len(final_chunks),
            final_chars,
            avg_similarity,
            highest_similarity,
            lowest_similarity,
            quality_score,
            retrieval_time_elapsed,
            ranking_time_elapsed,
            compression_time_elapsed,
            total_time_elapsed
        )

        response = RetrievalResponse(
            success=True,
            query=query_stripped,
            top_k=adaptive_top_k,
            retrieval_time=round(total_time_elapsed, 4),
            total_candidates=retrieved_candidates,
            filtered_candidates=retrieved_candidates - len(final_chunks),
            returned_results=len(final_chunks),
            retrieval_confidence=confidence,
            results=final_chunks
        )

        # 11. Cache response (Only cache global searches, skip filter queries)
        if self.settings.ENABLE_RETRIEVAL_CACHE and not document_id:
            self.cache.set(query, response)

        # Record retrieval time statistics
        RetrievalService._retrieval_times.append(total_time_elapsed)
        if len(RetrievalService._retrieval_times) > 50:
            RetrievalService._retrieval_times.pop(0)

        return response
