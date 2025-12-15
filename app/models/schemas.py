"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class QueryIntent(str, Enum):
    """Query intent classification"""
    GREETING = "greeting"
    CHITCHAT = "chitchat"
    QUESTION = "question"
    COMMAND = "command"
    UNCLEAR = "unclear"


class DocumentChunk(BaseModel):
    """Represents a chunk of text from a document"""
    chunk_id: str
    document_id: str
    document_name: str
    text: str
    page_number: Optional[int] = None
    chunk_index: int
    metadata: Dict[str, Any] = {}


class SearchResult(BaseModel):
    """Search result with relevance score"""
    chunk: DocumentChunk
    score: float
    search_type: str  # "semantic", "keyword", or "hybrid"


class Citation(BaseModel):
    """Citation information"""
    document_name: str
    page_number: Optional[int] = None
    chunk_text: str
    relevance_score: float


class QueryRequest(BaseModel):
    """User query request"""
    query: str = Field(..., min_length=1, description="User question")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Number of results to retrieve")
    include_citations: bool = Field(True, description="Include citations in response")


class AgentStep(BaseModel):
    """Represents a step in the agentic workflow"""
    step_number: int
    action: str
    observation: str
    thought: str


class QueryResponse(BaseModel):
    """Response to user query"""
    query: str
    answer: str
    intent: QueryIntent
    citations: List[Citation] = []
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning_steps: List[AgentStep] = []  # For agentic reasoning
    has_sufficient_evidence: bool = True
    warning: Optional[str] = None


class IngestionResponse(BaseModel):
    """Response after document ingestion"""
    success: bool
    message: str
    documents_processed: int
    total_chunks: int
    document_ids: List[str] = []


class RetrievalMetrics(BaseModel):
    """Metrics for retrieval quality"""
    total_results: int
    semantic_results: int
    keyword_results: int
    avg_score: float
    min_score: float
    max_score: float
