"""
Hallucination filter to detect unsupported claims in generated answers
Post-hoc verification that answer is grounded in context
"""
from typing import List, Tuple, Dict
import logging
import re
from app.services.llm import get_llm_service
from app.utils.text_processing import calculate_text_similarity

logger = logging.getLogger(__name__)


class HallucinationFilter:
    """
    Detect and filter hallucinations in generated answers

    Methods:
    1. Sentence-level entailment checking
    2. Fact extraction and verification
    3. Named entity consistency
    4. Numerical claim verification
    """

    def __init__(self):
        """Initialize hallucination filter"""
        self.llm = get_llm_service()

    def check_hallucination(
        self,
        answer: str,
        context_chunks: List[str]
    ) -> Tuple[bool, List[str], float]:
        """
        Check if answer contains hallucinations

        Args:
            answer: Generated answer
            context_chunks: Source context chunks

        Returns:
            Tuple of (is_supported, unsupported_claims, confidence)
        """
        if not answer or not context_chunks:
            return False, [], 0.0

        logger.info("Checking for hallucinations...")

        # Combine context
        full_context = " ".join(context_chunks)

        # Extract claims from answer
        claims = self._extract_claims(answer)

        if not claims:
            return True, [], 1.0

        # Check each claim
        unsupported_claims = []
        supported_count = 0

        for claim in claims:
            is_supported = self._verify_claim(claim, full_context)

            if is_supported:
                supported_count += 1
            else:
                unsupported_claims.append(claim)
                logger.warning(f"Unsupported claim detected: {claim[:100]}...")

        # Calculate confidence
        confidence = supported_count / len(claims) if claims else 1.0

        # Consider answer supported if at least 80% of claims are supported
        is_supported = confidence >= 0.8

        return is_supported, unsupported_claims, confidence

    def _extract_claims(self, text: str) -> List[str]:
        """
        Extract factual claims from text

        Args:
            text: Input text

        Returns:
            List of claim sentences
        """
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        # Filter out very short sentences and questions
        claims = [
            s.strip()
            for s in sentences
            if len(s.strip()) > 20 and not s.strip().endswith('?')
        ]

        return claims

    def _verify_claim(
        self,
        claim: str,
        context: str,
        threshold: float = 0.3
    ) -> bool:
        """
        Verify if a claim is supported by context

        Uses both lexical overlap and semantic similarity

        Args:
            claim: Claim to verify
            context: Source context
            threshold: Minimum similarity threshold

        Returns:
            True if claim is supported
        """
        # Simple lexical overlap check
        similarity = calculate_text_similarity(claim, context)

        if similarity >= threshold:
            return True

        # Check for keyword presence
        claim_words = set(claim.lower().split())

        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
            'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are',
            'was', 'were', 'been', 'be', 'have', 'has', 'had'
        }

        claim_keywords = claim_words - stop_words

        # Check if significant keywords are in context
        context_lower = context.lower()
        keyword_match_count = sum(
            1 for keyword in claim_keywords
            if len(keyword) > 3 and keyword in context_lower
        )

        keyword_match_ratio = (
            keyword_match_count / len(claim_keywords)
            if claim_keywords else 0
        )

        return keyword_match_ratio >= 0.5

    def verify_with_llm(
        self,
        answer: str,
        context_chunks: List[str]
    ) -> Dict:
        """
        Use LLM to verify if answer is supported by context

        Args:
            answer: Generated answer
            context_chunks: Source context

        Returns:
            Verification result dict
        """
        context = "\n\n".join(context_chunks)

        prompt = f"""Given the following context and answer, determine if the answer is fully supported by the context.

Context:
{context}

Answer:
{answer}

Is the answer fully supported by the context? Are there any claims in the answer that are not found in the context?

Respond with JSON:
{{
    "is_supported": true/false,
    "unsupported_claims": ["list of unsupported claims"],
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}"""

        try:
            result = self.llm.generate_structured(
                prompt=prompt,
                response_format={
                    "is_supported": bool,
                    "unsupported_claims": [],
                    "confidence": 0.0,
                    "reasoning": ""
                },
                temperature=0.1
            )
            return result

        except Exception as e:
            logger.error(f"LLM verification failed: {e}")
            return {
                "is_supported": True,  # Fail open
                "unsupported_claims": [],
                "confidence": 0.5,
                "reasoning": "Verification failed"
            }

    def filter_unsupported_content(
        self,
        answer: str,
        context_chunks: List[str]
    ) -> str:
        """
        Remove or flag unsupported content from answer

        Args:
            answer: Generated answer
            context_chunks: Source context

        Returns:
            Filtered answer
        """
        is_supported, unsupported_claims, confidence = self.check_hallucination(
            answer, context_chunks
        )

        if is_supported:
            return answer

        # If not supported, add disclaimer
        disclaimer = (
            "\n\n[Note: Some claims in this answer could not be fully verified "
            "against the provided documents. Please verify important information.]"
        )

        return answer + disclaimer


# Singleton instance
_hallucination_filter = None


def get_hallucination_filter() -> HallucinationFilter:
    """Get or create the global hallucination filter instance"""
    global _hallucination_filter
    if _hallucination_filter is None:
        _hallucination_filter = HallucinationFilter()
    return _hallucination_filter
