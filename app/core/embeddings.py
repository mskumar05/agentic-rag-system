"""
Embedding generation supporting both Ollama and Hugging Face models
"""
from typing import List
import numpy as np
import logging
import requests
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings using Ollama or Sentence Transformers"""

    def __init__(self, provider: str = None, model_name: str = None):
        """
        Initialize the embedding model

        Args:
            provider: 'ollama' or 'sentence-transformers'
            model_name: Model name
        """
        self.provider = provider or settings.EMBEDDING_PROVIDER
        self.model_name = model_name or settings.EMBEDDING_MODEL

        logger.info(f"Initializing embeddings: provider={self.provider}, model={self.model_name}")

        if self.provider == "ollama":
            self._init_ollama()
        elif self.provider == "sentence-transformers":
            self._init_sentence_transformers()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _init_ollama(self):
        """Initialize Ollama embeddings"""
        self.base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')

        # Test connection
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            logger.info(f"OK Connected to Ollama at {self.base_url}")
        except Exception as e:
            logger.warning(f"Cannot connect to Ollama at {self.base_url}: {e}")
            logger.warning("Make sure Ollama is running: ollama serve")

        # Ollama embeddings dimension depends on model
        # Test with a sample embedding to get the actual dimension
        try:
            test_embedding = self._embed_ollama_single("test")
            self.dimension = len(test_embedding)
            logger.info(f"OK Ollama embeddings initialized with model: {self.model_name}")
            logger.info(f"  Embedding dimension: {self.dimension}")
        except Exception as e:
            logger.warning(f"Could not determine embedding dimension: {e}")
            # Fallback dimensions
            if "nomic" in self.model_name.lower():
                self.dimension = 768
            else:
                self.dimension = 4096
            logger.info(f"  Using default dimension: {self.dimension}")

    def _init_sentence_transformers(self):
        """Initialize Sentence Transformers (Hugging Face)"""
        from sentence_transformers import SentenceTransformer

        logger.info(f"Loading embedding model: {self.model_name}")
        logger.info("Note: First time will download model from Hugging Face.")

        self.model = SentenceTransformer(self.model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()

        logger.info(f"OK Embeddings loaded successfully")
        logger.info(f"  Embedding dimension: {self.dimension}")

    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        if self.provider == "ollama":
            return self._embed_ollama_single(text)
        else:
            return self._embed_st_single(text)

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Generate embeddings for multiple texts"""
        if self.provider == "ollama":
            return self._embed_ollama_batch(texts)
        else:
            return self._embed_st_batch(texts, batch_size)

    def _embed_ollama_single(self, text: str) -> np.ndarray:
        """Generate embedding using Ollama"""
        url = f"{self.base_url}/api/embeddings"

        payload = {
            "model": self.model_name,
            "prompt": text
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()

            result = response.json()
            embedding = np.array(result["embedding"], dtype=np.float32)
            return embedding

        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama. Is it running?")
            logger.error("Start with: ollama serve")
            raise
        except Exception as e:
            logger.error(f"Ollama embedding error: {e}")
            raise

    def _embed_ollama_batch(self, texts: List[str]) -> np.ndarray:
        """Generate batch embeddings using Ollama"""
        logger.info(f"Generating {len(texts)} embeddings via Ollama...")

        embeddings = []

        for i, text in enumerate(texts):
            if i % 10 == 0:
                logger.info(f"  Progress: {i}/{len(texts)}")

            embedding = self._embed_ollama_single(text)
            embeddings.append(embedding)

        result = np.array(embeddings, dtype=np.float32)
        logger.info(f"OK Generated {len(embeddings)} embeddings")
        return result

    def _embed_st_single(self, text: str) -> np.ndarray:
        """Generate embedding using Sentence Transformers"""
        # For E5 models, prefix with "query: " for better results
        if "e5" in self.model_name.lower():
            text = f"query: {text}"

        embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding

    def _embed_st_batch(self, texts: List[str], batch_size: int) -> np.ndarray:
        """Generate batch embeddings using Sentence Transformers"""
        # For E5 models, prefix documents with "passage: "
        if "e5" in self.model_name.lower():
            texts = [f"passage: {text}" for text in texts]

        logger.info(f"Generating {len(texts)} embeddings in batches of {batch_size}...")

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True
        )

        logger.info(f"OK Generated {len(embeddings)} embeddings")
        return embeddings

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)

    def batch_cosine_similarity(
        self, query_vec: np.ndarray, doc_vecs: np.ndarray
    ) -> np.ndarray:
        """Calculate cosine similarity between query and multiple documents"""
        # Normalize vectors
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
        doc_norms = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-10)

        # Compute cosine similarity
        similarities = np.dot(doc_norms, query_norm)
        return similarities


# Global singleton instance
_embedding_generator = None


def get_embedding_generator() -> EmbeddingGenerator:
    """Get or create the global embedding generator instance"""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator
