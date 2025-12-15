"""
Re-ranking service to improve retrieval quality
Post-processes search results for better relevance
"""
from typing import List
import numpy as np
import logging
from app.models.schemas import SearchResult, DocumentChunk
from app.core.embeddings import get_embedding_generator
from app.utils.text_processing import calculate_text_similarity

logger = logging.getLogger(__name__)


class Reranker:
    """
    Re-rank search results using multiple signals:
    1. Cross-encoder style relevance scoring
    2. Diversity to avoid redundant chunks
    3. Position-aware scoring
    """

    def __init__(self):
        """Initialize reranker"""
        self.embedding_gen = get_embedding_generator()

    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        diversity_weight: float = 0.2
    ) -> List[SearchResult]:
        """
        Re-rank search results

        Args:
            query: Original query
            results: Initial search results
            diversity_weight: Weight for diversity in ranking (0-1)

        Returns:
            Re-ranked search results
        """
        if not results:
            return results

        logger.info(f"Re-ranking {len(results)} results")

        # Generate query embedding once
        query_embedding = self.embedding_gen.embed_text(query)

        # Score each result
        scored_results = []

        for result in results:
            # Calculate cross-attention score
            chunk_embedding = self.embedding_gen.embed_text(result.chunk.text)
            cross_score = self.embedding_gen.cosine_similarity(
                query_embedding,
                chunk_embedding
            )

            # Calculate lexical overlap
            lexical_score = calculate_text_similarity(query, result.chunk.text)

            # Combine scores
            relevance_score = (
                0.7 * cross_score +
                0.3 * lexical_score
            )

            # Blend with original score
            final_score = (
                0.6 * relevance_score +
                0.4 * result.score
            )

            scored_results.append((result, final_score))

        # Apply diversity
        if diversity_weight > 0:
            scored_results = self._apply_diversity(
                scored_results,
                diversity_weight
            )

        # Sort by final score
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # Update scores and return
        reranked = []
        for result, score in scored_results:
            result.score = score
            reranked.append(result)

        return reranked

    def _apply_diversity(
        self,
        scored_results: List[tuple],
        diversity_weight: float
    ) -> List[tuple]:
        """
        Apply diversity penalty to avoid redundant results

        Args:
            scored_results: List of (SearchResult, score) tuples
            diversity_weight: Weight for diversity penalty

        Returns:
            Results with diversity-adjusted scores
        """
        if len(scored_results) <= 1:
            return scored_results

        adjusted = []
        selected_texts = []

        for result, score in scored_results:
            # Calculate similarity to already selected results
            if selected_texts:
                similarities = [
                    calculate_text_similarity(result.chunk.text, text)
                    for text in selected_texts
                ]
                max_similarity = max(similarities)

                # Apply diversity penalty
                diversity_penalty = max_similarity * diversity_weight
                adjusted_score = score * (1 - diversity_penalty)
            else:
                adjusted_score = score

            adjusted.append((result, adjusted_score))
            selected_texts.append(result.chunk.text)

        return adjusted

    def filter_by_threshold(
        self,
        results: List[SearchResult],
        threshold: float
    ) -> List[SearchResult]:
        """
        Filter results by minimum score threshold

        Args:
            results: Search results
            threshold: Minimum score threshold

        Returns:
            Filtered results
        """
        filtered = [r for r in results if r.score >= threshold]

        logger.info(
            f"Filtered {len(results)} results to {len(filtered)} "
            f"with threshold {threshold}"
        )

        return filtered

    def merge_overlapping_chunks(
        self,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Merge chunks from the same document and consecutive pages

        Args:
            results: Search results

        Returns:
            Results with merged chunks where appropriate
        """
        if len(results) <= 1:
            return results

        merged = []
        i = 0

        while i < len(results):
            current = results[i]

            # Look ahead for mergeable chunks
            merge_candidates = [current]
            j = i + 1

            while j < len(results):
                next_result = results[j]

                # Check if same document and consecutive
                if (
                    next_result.chunk.document_id == current.chunk.document_id and
                    next_result.chunk.page_number is not None and
                    current.chunk.page_number is not None and
                    abs(next_result.chunk.page_number - current.chunk.page_number) <= 1
                ):
                    merge_candidates.append(next_result)
                    j += 1
                else:
                    break

            # Merge if we found candidates
            if len(merge_candidates) > 1:
                merged_result = self._merge_chunks(merge_candidates)
                merged.append(merged_result)
                i = j
            else:
                merged.append(current)
                i += 1

        return merged

    def _merge_chunks(
        self,
        results: List[SearchResult]
    ) -> SearchResult:
        """
        Merge multiple search results into one

        Args:
            results: Results to merge

        Returns:
            Merged SearchResult
        """
        # Combine texts
        combined_text = " ".join([r.chunk.text for r in results])

        # Average scores
        avg_score = sum(r.score for r in results) / len(results)

        # Use first chunk as base
        base_chunk = results[0].chunk

        # Create merged chunk
        merged_chunk = DocumentChunk(
            chunk_id=f"{base_chunk.chunk_id}_merged",
            document_id=base_chunk.document_id,
            document_name=base_chunk.document_name,
            text=combined_text,
            page_number=base_chunk.page_number,
            chunk_index=base_chunk.chunk_index,
            metadata={
                **base_chunk.metadata,
                'merged': True,
                'num_chunks_merged': len(results)
            }
        )

        return SearchResult(
            chunk=merged_chunk,
            score=avg_score,
            search_type="hybrid"
        )


# Singleton instance
_reranker = None


def get_reranker() -> Reranker:
    """Get or create the global reranker instance"""
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker
