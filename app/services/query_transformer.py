"""
Query transformation to improve retrieval performance
"""
import re
from typing import List
import logging

logger = logging.getLogger(__name__)


class QueryTransformer:
    """
    Transform user queries to improve retrieval

    Transformations:
    1. Expand abbreviations
    2. Add context keywords
    3. Rephrase for better matching
    4. Generate multiple query variations
    """

    def __init__(self):
        """Initialize query transformer"""

        # Common abbreviations and expansions
        self.abbreviations = {
            'ai': 'artificial intelligence',
            'ml': 'machine learning',
            'dl': 'deep learning',
            'nlp': 'natural language processing',
            'api': 'application programming interface',
            'ui': 'user interface',
            'ux': 'user experience',
            'db': 'database',
            'cpu': 'central processing unit',
            'gpu': 'graphics processing unit',
        }

    def transform(self, query: str) -> str:
        """
        Transform a single query for better retrieval

        Args:
            query: Original query

        Returns:
            Transformed query
        """
        if not query or not query.strip():
            return query

        transformed = query.strip()

        # Expand abbreviations
        transformed = self._expand_abbreviations(transformed)

        # Clean up extra whitespace
        transformed = re.sub(r'\s+', ' ', transformed).strip()

        return transformed

    def generate_variations(self, query: str, max_variations: int = 3) -> List[str]:
        """
        Generate multiple variations of a query for improved recall

        Args:
            query: Original query
            max_variations: Maximum number of variations to generate

        Returns:
            List of query variations (includes original)
        """
        variations = [query]

        # Add transformed version
        transformed = self.transform(query)
        if transformed != query and transformed not in variations:
            variations.append(transformed)

        # Add question reformulations
        if '?' in query:
            # Remove question mark and rephrase
            declarative = query.replace('?', '').strip()
            if declarative not in variations:
                variations.append(declarative)

        # Add keyword extraction version (remove question words)
        keywords = self._extract_keywords(query)
        if keywords and keywords not in variations:
            variations.append(keywords)

        return variations[:max_variations]

    def _expand_abbreviations(self, text: str) -> str:
        """
        Expand common abbreviations in text

        Args:
            text: Input text

        Returns:
            Text with expanded abbreviations
        """
        words = text.split()
        expanded_words = []

        for word in words:
            word_lower = word.lower().strip('.,!?;:')

            if word_lower in self.abbreviations:
                # Add both abbreviation and expansion
                expanded_words.append(word)
                expanded_words.append(self.abbreviations[word_lower])
            else:
                expanded_words.append(word)

        return ' '.join(expanded_words)

    def _extract_keywords(self, query: str) -> str:
        """
        Extract important keywords from query

        Args:
            query: Input query

        Returns:
            Keywords string
        """
        # Remove question words
        question_words = {
            'what', 'when', 'where', 'who', 'why', 'how', 'which',
            'is', 'are', 'was', 'were', 'do', 'does', 'did',
            'can', 'could', 'would', 'should', 'will',
            'the', 'a', 'an'
        }

        words = query.lower().split()
        keywords = [
            word.strip('.,!?;:')
            for word in words
            if word.strip('.,!?;:') not in question_words and len(word) > 2
        ]

        return ' '.join(keywords)

    def enhance_for_semantic_search(self, query: str) -> str:
        """
        Enhance query specifically for semantic search

        Args:
            query: Original query

        Returns:
            Enhanced query for semantic search
        """
        # For semantic search, we want complete sentences
        enhanced = self.transform(query)

        # Ensure it ends with proper punctuation for better sentence embedding
        if not enhanced[-1] in '.?!':
            enhanced += '?'

        return enhanced

    def enhance_for_keyword_search(self, query: str) -> str:
        """
        Enhance query specifically for keyword search

        Args:
            query: Original query

        Returns:
            Enhanced query for keyword search (focused on important terms)
        """
        # For keyword search, extract and expand important terms
        transformed = self.transform(query)
        keywords = self._extract_keywords(transformed)

        return keywords if keywords else transformed


# Singleton instance
_query_transformer = None


def get_query_transformer() -> QueryTransformer:
    """Get or create the global query transformer instance"""
    global _query_transformer
    if _query_transformer is None:
        _query_transformer = QueryTransformer()
    return _query_transformer
