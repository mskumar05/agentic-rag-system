"""
Citation validator to ensure sufficient evidence for answers
Implements citation requirements and similarity thresholds
"""
from typing import List, Tuple, Optional
import logging
from app.models.schemas import SearchResult, Citation
from app.core.config import settings

logger = logging.getLogger(__name__)


class CitationValidator:
    """
    Validate citations and ensure sufficient evidence

    Features:
    1. Check if top-k chunks meet similarity threshold
    2. Return "insufficient evidence" if below threshold
    3. Generate proper citations with metadata
    """

    def __init__(self, similarity_threshold: float = None):
        """
        Initialize citation validator

        Args:
            similarity_threshold: Minimum similarity score for valid citations
        """
        self.similarity_threshold = similarity_threshold or settings.SIMILARITY_THRESHOLD

    def validate_results(
        self,
        results: List[SearchResult]
    ) -> Tuple[bool, str]:
        """
        Validate if search results have sufficient evidence

        Args:
            results: Search results to validate

        Returns:
            Tuple of (is_valid, message)
        """
        if not results:
            return False, "No relevant information found in the knowledge base."

        # Check if top result meets threshold
        top_score = results[0].score

        if top_score < self.similarity_threshold:
            logger.warning(
                f"Top result score {top_score:.3f} below threshold "
                f"{self.similarity_threshold}"
            )
            return False, (
                f"Insufficient evidence to answer this question. "
                f"The most relevant document has a similarity score of "
                f"{top_score:.2f}, which is below the confidence threshold of "
                f"{self.similarity_threshold:.2f}."
            )

        # Check if we have supporting documents
        valid_results = [r for r in results if r.score >= self.similarity_threshold]

        if len(valid_results) < 1:
            logger.warning(f"Only {len(valid_results)} result(s) meet threshold")
            return False, (
                "Insufficient evidence to provide a reliable answer. "
                "Please try rephrasing your question or check if the information "
                "exists in the uploaded documents."
            )

        logger.info(f"Validation passed: {len(valid_results)} results above threshold")
        return True, ""

    def generate_citations(
        self,
        results: List[SearchResult],
        max_citations: int = 5
    ) -> List[Citation]:
        """
        Generate citation objects from search results

        Args:
            results: Search results
            max_citations: Maximum number of citations to generate

        Returns:
            List of Citation objects
        """
        citations = []

        for result in results[:max_citations]:
            if result.score >= self.similarity_threshold:
                citation = Citation(
                    document_name=result.chunk.document_name,
                    page_number=result.chunk.page_number,
                    chunk_text=self._truncate_text(result.chunk.text, max_length=200),
                    relevance_score=result.score
                )
                citations.append(citation)

        return citations

    def _truncate_text(self, text: str, max_length: int = 200) -> str:
        """
        Truncate text for citation display

        Args:
            text: Full text
            max_length: Maximum length

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= max_length:
            return text

        return text[:max_length].rsplit(' ', 1)[0] + "..."

    def filter_by_threshold(
        self,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Filter results by similarity threshold

        Args:
            results: Search results

        Returns:
            Filtered results above threshold
        """
        filtered = [
            r for r in results
            if r.score >= self.similarity_threshold
        ]

        logger.info(
            f"Filtered {len(results)} results to {len(filtered)} "
            f"above threshold {self.similarity_threshold}"
        )

        return filtered

    def requires_specific_evidence(self, query: str) -> bool:
        """
        Determine if query requires specific factual evidence

        Some queries like definitions, specific facts, dates, etc.
        require higher confidence

        Args:
            query: User query

        Returns:
            True if high confidence required
        """
        # Keywords that indicate need for specific evidence
        specific_keywords = [
            'when', 'where', 'who', 'what date', 'how many',
            'define', 'definition', 'what is', 'what are',
            'specific', 'exactly', 'precisely'
        ]

        query_lower = query.lower()

        return any(keyword in query_lower for keyword in specific_keywords)


# Singleton instance
_citation_validator = None


def get_citation_validator() -> CitationValidator:
    """Get or create the global citation validator instance"""
    global _citation_validator
    if _citation_validator is None:
        _citation_validator = CitationValidator()
    return _citation_validator
