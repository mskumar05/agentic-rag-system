"""
Hybrid search combining semantic and keyword-based retrieval
No external search libraries - custom implementation
"""
from typing import List, Tuple, Dict
import logging
import numpy as np
from rank_bm25 import BM25Okapi
from app.models.schemas import DocumentChunk, SearchResult
from app.core.vector_store import get_vector_store
from app.core.embeddings import get_embedding_generator
from app.services.query_transformer import get_query_transformer

logger = logging.getLogger(__name__)


class HybridSearch:
    """
    Hybrid search combining:
    1. Semantic search (dense vector similarity)
    2. Keyword search (BM25 algorithm)
    3. Weighted combination of results
    """

    def __init__(
        self,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4
    ):
        """
        Initialize hybrid search

        Args:
            semantic_weight: Weight for semantic search results (0-1)
            keyword_weight: Weight for keyword search results (0-1)
        """
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

        self.vector_store = get_vector_store()
        self.embedding_gen = get_embedding_generator()
        self.query_transformer = get_query_transformer()

        # BM25 index (built on demand)
        self.bm25_index = None
        self.bm25_chunks = []

    def search(
        self,
        query: str,
        top_k: int = 5,
        use_semantic: bool = True,
        use_keyword: bool = True
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining semantic and keyword approaches

        Args:
            query: Search query
            top_k: Number of results to return
            use_semantic: Enable semantic search
            use_keyword: Enable keyword search

        Returns:
            List of SearchResult objects sorted by relevance
        """
        logger.info(f"Hybrid search for: {query[:100]}...")

        # Transform query for better retrieval
        enhanced_query = self.query_transformer.transform(query)

        results = []

        # Semantic search
        if use_semantic:
            semantic_results = self._semantic_search(enhanced_query, top_k * 2)
            results.extend(semantic_results)

        # Keyword search
        if use_keyword:
            keyword_results = self._keyword_search(enhanced_query, top_k * 2)
            results.extend(keyword_results)

        # Merge and deduplicate
        merged = self._merge_results(results)

        # Sort by final score
        merged.sort(key=lambda x: x.score, reverse=True)

        return merged[:top_k]

    def _semantic_search(
        self,
        query: str,
        top_k: int
    ) -> List[SearchResult]:
        """
        Perform semantic search using vector similarity

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of SearchResult objects
        """
        # Enhance query for semantic search
        semantic_query = self.query_transformer.enhance_for_semantic_search(query)

        # Generate query embedding
        query_embedding = self.embedding_gen.embed_text(semantic_query)

        # Search vector store
        results = self.vector_store.search(query_embedding, top_k=top_k)

        # Convert to SearchResult objects
        search_results = [
            SearchResult(
                chunk=chunk,
                score=score * self.semantic_weight,
                search_type="semantic"
            )
            for chunk, score in results
        ]

        logger.debug(f"Semantic search returned {len(search_results)} results")
        return search_results

    def _keyword_search(
        self,
        query: str,
        top_k: int
    ) -> List[SearchResult]:
        """
        Perform keyword-based search using BM25

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of SearchResult objects
        """
        # Build or update BM25 index
        self._build_bm25_index()

        if not self.bm25_index or not self.bm25_chunks:
            logger.warning("No documents in BM25 index")
            return []

        # Enhance query for keyword search
        keyword_query = self.query_transformer.enhance_for_keyword_search(query)

        # Tokenize query
        query_tokens = keyword_query.lower().split()

        # Get BM25 scores
        scores = self.bm25_index.get_scores(query_tokens)

        # Get top-k indices
        top_k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[-top_k:][::-1]

        # Convert to SearchResult objects
        search_results = []
        for idx in top_indices:
            idx = int(idx)
            score = float(scores[idx])

            # Only include results with positive scores
            if score > 0:
                search_results.append(
                    SearchResult(
                        chunk=self.bm25_chunks[idx],
                        score=score * self.keyword_weight,
                        search_type="keyword"
                    )
                )

        logger.debug(f"Keyword search returned {len(search_results)} results")
        return search_results

    def _build_bm25_index(self) -> None:
        """
        Build or rebuild BM25 index from vector store chunks
        """
        current_chunks = self.vector_store.chunks

        # Check if we need to rebuild
        if len(current_chunks) == len(self.bm25_chunks):
            return  # Index is up to date

        logger.info(f"Building BM25 index for {len(current_chunks)} chunks...")

        self.bm25_chunks = current_chunks

        # Tokenize all chunks
        tokenized_chunks = [
            chunk.text.lower().split()
            for chunk in self.bm25_chunks
        ]

        # Build BM25 index
        if tokenized_chunks:
            self.bm25_index = BM25Okapi(tokenized_chunks)
            logger.info("BM25 index built successfully")
        else:
            self.bm25_index = None
            logger.warning("No chunks to index")

    def _merge_results(
        self,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Merge and deduplicate search results from different sources

        Strategy:
        1. Group by chunk_id
        2. For duplicates, take the maximum score
        3. Update search_type to "hybrid" for combined results

        Args:
            results: List of search results to merge

        Returns:
            Merged and deduplicated results
        """
        # Group by chunk_id
        chunk_scores: Dict[str, Tuple[DocumentChunk, float, List[str]]] = {}

        for result in results:
            chunk_id = result.chunk.chunk_id

            if chunk_id in chunk_scores:
                # Combine scores (take maximum)
                existing_chunk, existing_score, existing_types = chunk_scores[chunk_id]
                combined_score = max(existing_score, result.score)

                # Track search types
                if result.search_type not in existing_types:
                    existing_types.append(result.search_type)

                chunk_scores[chunk_id] = (result.chunk, combined_score, existing_types)
            else:
                chunk_scores[chunk_id] = (result.chunk, result.score, [result.search_type])

        # Convert back to SearchResult objects
        merged = []
        for chunk, score, search_types in chunk_scores.values():
            search_type = "hybrid" if len(search_types) > 1 else search_types[0]

            merged.append(
                SearchResult(
                    chunk=chunk,
                    score=score,
                    search_type=search_type
                )
            )

        return merged


# Singleton instance
_hybrid_search = None


def get_hybrid_search() -> HybridSearch:
    """Get or create the global hybrid search instance"""
    global _hybrid_search
    if _hybrid_search is None:
        _hybrid_search = HybridSearch()
    return _hybrid_search
