"""
Query refusal policies for PII, legal, and medical disclaimers
Uses LLM-based detection for nuanced and context-aware classification
"""
import re
import logging
import json
from typing import Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class RefusalReason(str, Enum):
    """Reasons for query refusal"""
    PII_DETECTED = "pii_detected"
    LEGAL_DISCLAIMER = "legal_disclaimer"
    MEDICAL_DISCLAIMER = "medical_disclaimer"
    NONE = "none"


class QueryRefusalPolicy:
    """
    Implement query refusal policies for safety and compliance

    Uses LLM for intelligent detection instead of keyword matching

    Features:
    1. PII Detection: Regex + LLM for comprehensive detection
    2. Legal Disclaimers: LLM-based intent detection
    3. Medical Disclaimers: LLM-based intent detection
    """

    def __init__(self, llm_service=None):
        """
        Initialize refusal policy

        Args:
            llm_service: Optional LLM service instance (lazy loaded if not provided)
        """
        self._llm_service = llm_service

        # PII patterns for fast first-pass detection
        self.pii_patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b'),
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'credit_card': re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
            'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
        }

        # Disclaimer templates
        self.legal_disclaimer = (
            "\n\n**Legal Disclaimer**: This response is for informational purposes only "
            "and does not constitute legal advice. Consult a qualified attorney for "
            "legal matters specific to your situation."
        )

        self.medical_disclaimer = (
            "\n\n**Medical Disclaimer**: This response is for informational purposes only "
            "and does not constitute medical advice. Consult a qualified healthcare "
            "provider for medical concerns or before making health-related decisions."
        )

    @property
    def llm_service(self):
        """Lazy load LLM service to avoid circular imports"""
        if self._llm_service is None:
            from app.services.llm import get_llm_service
            self._llm_service = get_llm_service()
        return self._llm_service

    def check_pii_regex(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Check if query contains PII using regex patterns (fast check)

        Args:
            query: User query to check

        Returns:
            Tuple of (contains_pii, pii_type)
        """
        for pii_type, pattern in self.pii_patterns.items():
            if pattern.search(query):
                logger.warning(f"PII detected in query text: {pii_type}")
                return True, pii_type

        return False, None

    def check_pii_request_llm(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Use LLM to detect if user is requesting PII information

        Args:
            query: User query to check

        Returns:
            Tuple of (is_pii_request, pii_type)
        """
        prompt = f"""Analyze the following user query and determine if it is requesting personally identifiable information (PII).

User query: "{query}"

PII includes:
- Social Security Numbers (SSN)
- Phone numbers
- Email addresses
- Physical addresses
- Credit card numbers
- Driver's license numbers
- Medical record numbers
- Bank account numbers
- Passport numbers
- Any other sensitive personal identifiers

Respond with ONLY a JSON object with this format:
{{
    "is_pii_request": true or false,
    "confidence": 0.0 to 1.0,
    "pii_type": "ssn|phone|email|address|credit_card|other|none",
    "reason": "brief explanation"
}}

Examples of PII requests (should refuse):
- "what is ssn?" → {{"is_pii_request": true, "confidence": 0.95, "pii_type": "ssn", "reason": "Requesting SSN"}}
- "phone" → {{"is_pii_request": true, "confidence": 0.90, "pii_type": "phone", "reason": "Requesting phone number"}}
- "what is the email address?" → {{"is_pii_request": true, "confidence": 0.95, "pii_type": "email", "reason": "Requesting email"}}
- "give me the address" → {{"is_pii_request": true, "confidence": 0.95, "pii_type": "address", "reason": "Requesting address"}}

Examples of NON-PII requests (should allow):
- "what is the candidate's education?" → {{"is_pii_request": false, "confidence": 0.95, "pii_type": "none", "reason": "Education is not PII"}}
- "what skills does the candidate have?" → {{"is_pii_request": false, "confidence": 0.95, "pii_type": "none", "reason": "Skills are not PII"}}
- "what is python?" → {{"is_pii_request": false, "confidence": 0.95, "pii_type": "none", "reason": "General knowledge question"}}

Respond ONLY with the JSON object, nothing else."""

        try:
            response = self.llm_service.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=150
            )

            # Parse JSON response
            result = self._parse_llm_json(response)

            if result and result.get('is_pii_request', False):
                confidence = result.get('confidence', 0.0)
                pii_type = result.get('pii_type', 'unknown')
                reason = result.get('reason', 'LLM detected PII request')

                if confidence > 0.7:  # Only flag if confident
                    logger.warning(f"PII request detected by LLM (confidence: {confidence:.2f}): {reason}")
                    return True, pii_type

        except Exception as e:
            logger.warning(f"LLM PII detection failed: {e}")

        return False, None

    def check_legal_query_llm(self, query: str) -> bool:
        """
        Use LLM to determine if query is legal-related

        Args:
            query: User query to check

        Returns:
            True if legal-related query
        """
        prompt = f"""Analyze the following user query and determine if it is asking for legal advice, legal information, or is related to legal matters.

User query: "{query}"

Respond with ONLY a JSON object with this format:
{{
    "is_legal": true or false,
    "confidence": 0.0 to 1.0,
    "reason": "brief explanation"
}}

Examples of legal queries:
- "Can I sue my employer?"
- "What are my legal rights?"
- "How do I file a lawsuit?"
- "Is this contract valid?"

Examples of NON-legal queries:
- "What experience does the candidate have?"
- "Tell me about the job requirements"
- "What skills are listed?"

Respond ONLY with the JSON object, nothing else."""

        try:
            response = self.llm_service.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=150
            )

            # Parse JSON response
            result = self._parse_llm_json(response)

            if result and result.get('is_legal', False):
                confidence = result.get('confidence', 0.0)
                reason = result.get('reason', 'LLM detected legal intent')

                if confidence > 0.6:  # Only flag if confident
                    logger.info(f"Legal query detected by LLM (confidence: {confidence:.2f}): {reason}")
                    return True

        except Exception as e:
            logger.warning(f"LLM legal detection failed: {e}")

        return False

    def check_medical_query_llm(self, query: str) -> bool:
        """
        Use LLM to determine if query is medical-related

        Args:
            query: User query to check

        Returns:
            True if medical-related query
        """
        prompt = f"""Analyze the following user query and determine if it is asking for medical advice, medical information, or is related to health/medical matters.

User query: "{query}"

Respond with ONLY a JSON object with this format:
{{
    "is_medical": true or false,
    "confidence": 0.0 to 1.0,
    "reason": "brief explanation"
}}

Examples of medical queries:
- "What medication should I take?"
- "How do I treat this symptom?"
- "What are the side effects of this drug?"
- "Should I see a doctor for this?"

Examples of NON-medical queries:
- "What is the candidate's education?"
- "Tell me about work experience"
- "What programming languages do they know?"

Respond ONLY with the JSON object, nothing else."""

        try:
            response = self.llm_service.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=150
            )

            # Parse JSON response
            result = self._parse_llm_json(response)

            if result and result.get('is_medical', False):
                confidence = result.get('confidence', 0.0)
                reason = result.get('reason', 'LLM detected medical intent')

                if confidence > 0.6:  # Only flag if confident
                    logger.info(f"Medical query detected by LLM (confidence: {confidence:.2f}): {reason}")
                    return True

        except Exception as e:
            logger.warning(f"LLM medical detection failed: {e}")

        return False

    def _parse_llm_json(self, response: str) -> Optional[dict]:
        """
        Parse JSON from LLM response, handling markdown code blocks

        Args:
            response: LLM response text

        Returns:
            Parsed JSON dict or None
        """
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"Response was: {response}")
            return None

    def evaluate_query(
        self,
        query: str
    ) -> Tuple[bool, RefusalReason, Optional[str]]:
        """
        Evaluate query against all refusal policies using LLM

        Args:
            query: User query to evaluate

        Returns:
            Tuple of (should_refuse, reason, message)
        """
        # Check 1: Fast regex check for PII in query text itself
        contains_pii, pii_type = self.check_pii_regex(query)
        if contains_pii:
            message = (
                f"WARNING: Your query contains personal information ({pii_type}). "
                "For your privacy and security, please remove any personal information "
                "such as emails, phone numbers, SSN, or addresses before submitting your query."
            )
            return True, RefusalReason.PII_DETECTED, message

        # Check 2: LLM check for queries requesting PII information
        is_pii_request, pii_type = self.check_pii_request_llm(query)
        if is_pii_request:
            message = (
                f"WARNING: Your query appears to be requesting personal identifiable information ({pii_type}). "
                "For privacy and security reasons, I cannot provide sensitive personal information "
                "such as Social Security Numbers, phone numbers, email addresses, or physical addresses. "
                "Please ask about non-sensitive information instead."
            )
            return True, RefusalReason.PII_DETECTED, message

        # Check for legal queries using LLM (add disclaimer, don't refuse)
        if self.check_legal_query_llm(query):
            return False, RefusalReason.LEGAL_DISCLAIMER, self.legal_disclaimer

        # Check for medical queries using LLM (add disclaimer, don't refuse)
        if self.check_medical_query_llm(query):
            return False, RefusalReason.MEDICAL_DISCLAIMER, self.medical_disclaimer

        return False, RefusalReason.NONE, None

    def apply_disclaimer(self, answer: str, disclaimer: str) -> str:
        """
        Apply disclaimer to answer

        Args:
            answer: Generated answer
            disclaimer: Disclaimer text to append

        Returns:
            Answer with disclaimer
        """
        if disclaimer:
            return answer + disclaimer
        return answer


# Singleton instance
_query_refusal_policy = None


def get_query_refusal_policy() -> QueryRefusalPolicy:
    """Get or create the global query refusal policy instance"""
    global _query_refusal_policy
    if _query_refusal_policy is None:
        _query_refusal_policy = QueryRefusalPolicy()
    return _query_refusal_policy
