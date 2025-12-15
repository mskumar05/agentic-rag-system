"""
Query intent detection to determine if knowledge base search is needed
Uses LLM-based detection for nuanced and context-aware classification
"""
import re
import json
from typing import Tuple, Optional
import logging
from app.models.schemas import QueryIntent

logger = logging.getLogger(__name__)


class IntentDetector:
    """
    Detect user query intent to determine if RAG retrieval is necessary

    Uses LLM for intelligent, context-aware intent detection instead of
    simple regex pattern matching.

    Intents:
    - GREETING: Simple greetings (no search needed)
    - CHITCHAT: Casual conversation (no search needed)
    - QUESTION: Actual questions requiring knowledge base
    - COMMAND: Commands or requests
    - UNCLEAR: Cannot determine intent
    """

    def __init__(self, llm_service=None):
        """
        Initialize intent detector

        Args:
            llm_service: Optional LLM service instance (lazy loaded if not provided)
        """
        self._llm_service = llm_service

        # Fast-path regex patterns for obvious cases (optional optimization)
        # These can catch very simple greetings without LLM call
        self.simple_greeting_patterns = [
            r'^(hi+|he(l+o+)+|hey+)[\s\!\.\?]*$',  # Matches hi, hii, hello, helloo, hellooo, hey, heyy
            r'^(hi|hello|hey)\s+(there|all|everyone)[\s\!\.\?]*$',  # hi there, hello all, etc.
            r'^(good morning|good afternoon|good evening)[\s\!\.\?]*$'
        ]

        self.simple_goodbye_patterns = [
            r'^(bye|goodbye|see you|cya|later)[\s\!\.\?]*$',
            r'^(thanks?|thank you|thx)[\s\!\.\?]*$'  # Thanks should be chitchat, not search
        ]

    @property
    def llm_service(self):
        """Lazy load LLM service to avoid circular imports"""
        if self._llm_service is None:
            from app.services.llm import get_llm_service
            self._llm_service = get_llm_service()
        return self._llm_service

    def detect_intent(self, query: str) -> Tuple[QueryIntent, float]:
        """
        Detect the intent of a user query using LLM

        Args:
            query: User query text

        Returns:
            Tuple of (intent, confidence_score)
        """
        if not query or not query.strip():
            return QueryIntent.UNCLEAR, 0.0

        query_lower = query.lower().strip()

        # Fast-path: Check for very simple greetings using regex
        if self._matches_patterns(query_lower, self.simple_greeting_patterns):
            logger.info(f"Fast-path greeting detected: {query}")
            return QueryIntent.GREETING, 0.95

        if self._matches_patterns(query_lower, self.simple_goodbye_patterns):
            logger.info(f"Fast-path goodbye detected: {query}")
            return QueryIntent.CHITCHAT, 0.95

        # Use LLM for nuanced intent detection
        return self._detect_intent_with_llm(query)

    def _detect_intent_with_llm(self, query: str) -> Tuple[QueryIntent, float]:
        """
        Use LLM to detect query intent with context awareness

        Args:
            query: User query

        Returns:
            Tuple of (intent, confidence)
        """
        prompt = f"""Analyze the following user input and classify its intent.

User Input: "{query}"

Classify into ONE of these intents:
1. GREETING - Simple greetings like "hi", "hello", "good morning" (user just saying hello)
2. CHITCHAT - Casual conversation like "how are you", "thanks", "that's cool" (not requesting information)
3. QUESTION - Real questions that need information from a knowledge base (asking for facts, explanations, data)
4. COMMAND - Commands or requests like "show me", "list", "find" (requesting an action)
5. UNCLEAR - Cannot determine clear intent

Respond ONLY with valid JSON in this exact format:
{{
    "intent": "GREETING|CHITCHAT|QUESTION|COMMAND|UNCLEAR",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation"
}}

Examples:
- "hello" → {{"intent": "GREETING", "confidence": 0.95, "reasoning": "Simple greeting"}}
- "helloo" → {{"intent": "GREETING", "confidence": 0.95, "reasoning": "Greeting with typo"}}
- "hi there" → {{"intent": "GREETING", "confidence": 0.95, "reasoning": "Friendly greeting"}}
- "how are you" → {{"intent": "CHITCHAT", "confidence": 0.9, "reasoning": "Casual conversation"}}
- "thanks" → {{"intent": "CHITCHAT", "confidence": 0.9, "reasoning": "Expressing gratitude"}}
- "what is python" → {{"intent": "QUESTION", "confidence": 0.95, "reasoning": "Asking for information"}}
- "tell me about the candidate" → {{"intent": "QUESTION", "confidence": 0.95, "reasoning": "Requesting specific information"}}
- "show all documents" → {{"intent": "COMMAND", "confidence": 0.9, "reasoning": "Requesting action"}}

Respond with JSON only, no markdown formatting."""

        try:
            response = self.llm_service.generate(
                prompt=prompt,
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=150
            )

            # Parse JSON response
            result = self._parse_json_response(response)

            if result:
                intent_str = result.get('intent', 'UNCLEAR').upper()
                confidence = float(result.get('confidence', 0.5))
                reasoning = result.get('reasoning', 'No reasoning provided')

                # Map string to enum
                intent_map = {
                    'GREETING': QueryIntent.GREETING,
                    'CHITCHAT': QueryIntent.CHITCHAT,
                    'QUESTION': QueryIntent.QUESTION,
                    'COMMAND': QueryIntent.COMMAND,
                    'UNCLEAR': QueryIntent.UNCLEAR
                }

                intent = intent_map.get(intent_str, QueryIntent.UNCLEAR)

                logger.info(f"LLM intent detection: {intent} (confidence: {confidence:.2f}) - {reasoning}")

                return intent, confidence

        except Exception as e:
            logger.error(f"Error in LLM intent detection: {e}", exc_info=True)

        # Fallback: assume it's a question if it's reasonably long
        words = query.split()
        if len(words) >= 3:
            return QueryIntent.QUESTION, 0.5

        return QueryIntent.UNCLEAR, 0.3

    def _parse_json_response(self, response: str) -> Optional[dict]:
        """
        Parse JSON from LLM response, handling markdown code blocks

        Args:
            response: LLM response text

        Returns:
            Parsed JSON dict or None
        """
        try:
            # Remove markdown code blocks if present
            cleaned = response.strip()

            # Remove ```json and ``` markers
            if cleaned.startswith('```'):
                # Find the actual JSON content
                lines = cleaned.split('\n')
                json_lines = []
                in_code_block = False

                for line in lines:
                    if line.strip().startswith('```'):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block or (not line.strip().startswith('```')):
                        json_lines.append(line)

                cleaned = '\n'.join(json_lines).strip()

            # Parse JSON
            return json.loads(cleaned)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response was: {response}")
            return None

    def _matches_patterns(self, text: str, patterns: list) -> bool:
        """
        Check if text matches any of the given regex patterns

        Args:
            text: Input text
            patterns: List of regex patterns

        Returns:
            True if any pattern matches
        """
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

    def should_search_kb(self, query: str) -> bool:
        """
        Determine if the query should trigger a knowledge base search

        Args:
            query: User query

        Returns:
            True if knowledge base search should be performed
        """
        intent, confidence = self.detect_intent(query)

        # Only search for questions and high-confidence commands
        if intent == QueryIntent.QUESTION:
            return True

        if intent == QueryIntent.COMMAND and confidence >= 0.75:
            return True

        return False


# Singleton instance
_intent_detector = None


def get_intent_detector() -> IntentDetector:
    """Get or create the global intent detector instance"""
    global _intent_detector
    if _intent_detector is None:
        _intent_detector = IntentDetector()
    return _intent_detector
