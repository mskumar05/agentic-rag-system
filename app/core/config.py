"""
Configuration management for the Agentic RAG System
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Keys
    GROQ_API_KEY: str
    MISTRAL_API_KEY: Optional[str] = None
    TOGETHER_API_KEY: Optional[str] = None

    # Application Settings
    APP_NAME: str = "Agentic RAG System"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # RAG Settings
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.5
    MAX_CONTEXT_LENGTH: int = 4096

    # Embedding Settings
    EMBEDDING_PROVIDER: str = "sentence-transformers"  # sentence-transformers for local models
    EMBEDDING_MODEL: str = "intfloat/e5-mistral-7b-instruct"  # Mistral-based embeddings from HF

    # LLM Settings
    LLM_PROVIDER: str = "ollama"  # ollama, groq, or together
    LLM_MODEL: str = "mistral"  # Mistral model from Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_TEMPERATURE: float = 0.3
    MAX_TOKENS: int = 2048

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOADS_DIR: Path = DATA_DIR / "uploads"
    VECTOR_DB_DIR: Path = DATA_DIR / "vector_db"

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
