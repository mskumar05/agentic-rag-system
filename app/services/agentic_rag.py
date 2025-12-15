"""
Agentic RAG implementation with ReAct-style reasoning
Orchestrates the entire RAG pipeline with agent-like capabilities
"""
from typing import List, Dict, Optional, Tuple
import logging
from app.models.schemas import (
    QueryRequest, QueryResponse, QueryIntent, AgentStep, Citation
)
from app.services.intent_detector import get_intent_detector
from app.services.query_transformer import get_query_transformer
from app.services.search import get_hybrid_search
from app.services.reranker import get_reranker
from app.services.llm import get_llm_service
from app.services.citation_validator import get_citation_validator
from app.services.hallucination_filter import get_hallucination_filter
from app.services.query_refusal import get_query_refusal_policy, RefusalReason
from app.core.config import settings

logger = logging.getLogger(__name__)


class AgenticRAG:
    """
    Agentic RAG system implementing ReAct-style reasoning

    Agent Workflow:
    1. Thought: Analyze query and plan approach
    2. Action: Execute retrieval or reasoning step
    3. Observation: Evaluate results
    4. Repeat until answer is found or max steps reached
    5. Final Answer: Generate response with citations
    """

    def __init__(self, max_steps: int = 5):
        """
        Initialize Agentic RAG system

        Args:
            max_steps: Maximum reasoning steps
        """
        self.max_steps = max_steps

        # Initialize components
        self.intent_detector = get_intent_detector()
        self.query_transformer = get_query_transformer()
        self.search = get_hybrid_search()
        self.reranker = get_reranker()
        self.llm = get_llm_service()
        self.citation_validator = get_citation_validator()
        self.hallucination_filter = get_hallucination_filter()
        self.refusal_policy = get_query_refusal_policy()

    def process_query(self, request: QueryRequest) -> QueryResponse:
        """
        Process user query with agentic reasoning

        Args:
            request: Query request

        Returns:
            Query response with answer and metadata
        """
        query = request.query
        logger.info(f"Processing query: {query[:100]}...")

        # Step 0: Check refusal policies (PII, legal, medical)
        should_refuse, refusal_reason, refusal_message = self.refusal_policy.evaluate_query(query)

        if should_refuse:
            # Refuse to process query (PII detected)
            logger.warning(f"Query refused: {refusal_reason}")
            return QueryResponse(
                query=query,
                answer=refusal_message,
                intent=QueryIntent.QUESTION,
                citations=[],
                confidence=0.0,
                reasoning_steps=[],
                has_sufficient_evidence=False,
                warning=f"Query refused: {refusal_reason.value}"
            )

        # Step 1: Detect intent
        intent, intent_confidence = self.intent_detector.detect_intent(query)

        logger.info(f"Detected intent: {intent} (confidence: {intent_confidence:.2f})")

        # Handle non-question intents
        if intent == QueryIntent.GREETING:
            return self._handle_greeting(query, intent)

        if intent == QueryIntent.CHITCHAT:
            return self._handle_chitchat(query, intent)

        # For questions and commands, proceed with RAG
        return self._agentic_reasoning(request, intent, intent_confidence)

    def _agentic_reasoning(
        self,
        request: QueryRequest,
        intent: QueryIntent,
        intent_confidence: float
    ) -> QueryResponse:
        """
        Perform agentic reasoning with ReAct loop

        Args:
            request: Query request
            intent: Detected intent
            intent_confidence: Confidence score for intent detection

        Returns:
            Query response
        """
        query = request.query
        reasoning_steps = []
        step_num = 0

        # Step 1: Initial thought and query transformation
        step_num += 1
        thought = "I need to search the knowledge base for relevant information."
        action = "Transforming query for better retrieval"

        transformed_query = self.query_transformer.transform(query)

        observation = f"Enhanced query: {transformed_query}"

        reasoning_steps.append(AgentStep(
            step_number=step_num,
            action=action,
            observation=observation,
            thought=thought
        ))

        # Step 2: Hybrid search
        step_num += 1
        thought = "Performing hybrid search combining semantic and keyword matching."
        action = "Executing hybrid search"

        search_results = self.search.search(
            query=transformed_query,
            top_k=request.top_k * 2  # Get more for reranking
        )

        observation = f"Retrieved {len(search_results)} results"

        reasoning_steps.append(AgentStep(
            step_number=step_num,
            action=action,
            observation=observation,
            thought=thought
        ))

        # Step 3: Re-ranking and validation
        step_num += 1
        thought = "Re-ranking results and checking for sufficient evidence."
        action = "Re-ranking and validating results"

        reranked = self.reranker.rerank(query, search_results)
        reranked = reranked[:request.top_k]

        # Validate citations
        is_valid, validation_msg = self.citation_validator.validate_results(reranked)

        if not is_valid:
            observation = f"Insufficient evidence: {validation_msg}"
            reasoning_steps.append(AgentStep(
                step_number=step_num,
                action=action,
                observation=observation,
                thought=thought
            ))

            return QueryResponse(
                query=query,
                answer=validation_msg,
                intent=intent,
                citations=[],
                confidence=0.0,
                reasoning_steps=reasoning_steps,
                has_sufficient_evidence=False,
                warning="Insufficient evidence in knowledge base"
            )

        observation = f"Found {len(reranked)} high-quality results"
        reasoning_steps.append(AgentStep(
            step_number=step_num,
            action=action,
            observation=observation,
            thought=thought
        ))

        # Step 4: Select answer template based on intent
        step_num += 1
        thought = "Selecting appropriate answer template."
        action = "Preparing generation prompt"

        template = self._select_template(query, intent)

        observation = f"Using template: {template['name']}"
        reasoning_steps.append(AgentStep(
            step_number=step_num,
            action=action,
            observation=observation,
            thought=thought
        ))

        # Step 5: Generate answer
        step_num += 1
        thought = "Generating answer using LLM with retrieved context."
        action = "Generating answer"

        context_chunks = [r.chunk.text for r in reranked]
        answer = self._generate_answer(
            query=query,
            context_chunks=context_chunks,
            template=template
        )

        observation = f"Generated answer ({len(answer)} characters)"
        reasoning_steps.append(AgentStep(
            step_number=step_num,
            action=action,
            observation=observation,
            thought=thought
        ))

        # Step 6: Hallucination check (if enabled)
        step_num += 1
        thought = "Verifying answer is supported by context."
        action = "Checking for hallucinations"

        is_supported, unsupported_claims, hal_confidence = (
            self.hallucination_filter.check_hallucination(answer, context_chunks)
        )

        if not is_supported:
            observation = f"Detected {len(unsupported_claims)} unsupported claims"
            answer = self.hallucination_filter.filter_unsupported_content(
                answer, context_chunks
            )
        else:
            observation = "Answer is well-supported by context"

        reasoning_steps.append(AgentStep(
            step_number=step_num,
            action=action,
            observation=observation,
            thought=thought
        ))

        # Generate citations
        citations = []
        if request.include_citations:
            citations = self.citation_validator.generate_citations(reranked)

        # Calculate final confidence
        confidence = min(
            intent_confidence * 0.3 +
            (sum(r.score for r in reranked) / len(reranked)) * 0.4 +
            hal_confidence * 0.3,
            1.0
        )

        # Apply disclaimers if needed (legal/medical queries)
        _, disclaimer_reason, disclaimer_message = self.refusal_policy.evaluate_query(query)
        if disclaimer_message and disclaimer_reason in [RefusalReason.LEGAL_DISCLAIMER, RefusalReason.MEDICAL_DISCLAIMER]:
            answer = self.refusal_policy.apply_disclaimer(answer, disclaimer_message)
            logger.info(f"Applied {disclaimer_reason.value} to answer")

        return QueryResponse(
            query=query,
            answer=answer,
            intent=intent,
            citations=citations,
            confidence=confidence,
            reasoning_steps=reasoning_steps,
            has_sufficient_evidence=True,
            warning=None if is_supported else "Some claims could not be fully verified"
        )

    def _select_template(
        self,
        query: str,
        intent: QueryIntent
    ) -> Dict[str, str]:
        """
        Select appropriate prompt template based on query and intent

        Args:
            query: User query
            intent: Detected intent

        Returns:
            Template dict with name and system message
        """
        query_lower = query.lower()

        # List or enumeration request
        if any(word in query_lower for word in ['list', 'enumerate', 'what are']):
            return {
                'name': 'list_template',
                'system': (
                    "You are a helpful assistant that provides clear, "
                    "structured answers. When listing items, use bullet points "
                    "or numbered lists. Base your answer strictly on the provided context."
                )
            }

        # Definition request
        if any(word in query_lower for word in ['define', 'what is', 'what does']):
            return {
                'name': 'definition_template',
                'system': (
                    "You are a helpful assistant that provides clear, concise definitions. "
                    "Start with a direct definition, then provide additional context if available. "
                    "Base your answer strictly on the provided context."
                )
            }

        # Comparison request
        if any(word in query_lower for word in ['compare', 'difference', 'versus', 'vs']):
            return {
                'name': 'comparison_template',
                'system': (
                    "You are a helpful assistant that provides structured comparisons. "
                    "Clearly outline similarities and differences. "
                    "Base your answer strictly on the provided context."
                )
            }

        # Default template
        return {
            'name': 'default_template',
            'system': (
                "You are a helpful assistant that provides accurate, "
                "well-reasoned answers based on the given context. "
                "Be concise but thorough. If the context doesn't fully answer "
                "the question, acknowledge this. Never make up information."
            )
        }

    def _generate_answer(
        self,
        query: str,
        context_chunks: List[str],
        template: Dict[str, str]
    ) -> str:
        """
        Generate answer using LLM

        Args:
            query: User query
            context_chunks: Retrieved context
            template: Prompt template

        Returns:
            Generated answer
        """
        # Build context
        context = "\n\n".join([
            f"[Context {i+1}]\n{chunk}"
            for i, chunk in enumerate(context_chunks)
        ])

        # Build prompt
        prompt = f"""Based on the following context, answer the user's question accurately and concisely.

{context}

Question: {query}

Instructions:
- Answer based ONLY on the provided context
- Be specific and cite relevant information
- If the context doesn't contain enough information, say so
- Do not make up or infer information not in the context

Answer:"""

        answer = self.llm.generate(
            prompt=prompt,
            system_message=template['system'],
            temperature=0.3
        )

        return answer.strip()

    def _handle_greeting(self, query: str, intent: QueryIntent) -> QueryResponse:
        """Handle greeting queries"""
        greetings = [
            "Hello! I'm your AI assistant. I can help you find information from the uploaded documents. What would you like to know?",
            "Hi there! I'm ready to help you explore the knowledge base. What can I assist you with?",
            "Greetings! I'm here to answer your questions based on the uploaded documents. How may I help you?"
        ]

        import random
        answer = random.choice(greetings)

        return QueryResponse(
            query=query,
            answer=answer,
            intent=intent,
            citations=[],
            confidence=1.0,
            reasoning_steps=[],
            has_sufficient_evidence=True
        )

    def _handle_chitchat(self, query: str, intent: QueryIntent) -> QueryResponse:
        """Handle chitchat queries"""
        answer = (
            "I appreciate the friendly interaction! However, I'm specifically designed "
            "to help you find information from the uploaded documents. "
            "Do you have any questions about the documents?"
        )

        return QueryResponse(
            query=query,
            answer=answer,
            intent=intent,
            citations=[],
            confidence=0.8,
            reasoning_steps=[],
            has_sufficient_evidence=True
        )


# Singleton instance
_agentic_rag = None


def get_agentic_rag() -> AgenticRAG:
    """Get or create the global agentic RAG instance"""
    global _agentic_rag
    if _agentic_rag is None:
        _agentic_rag = AgenticRAG()
    return _agentic_rag
