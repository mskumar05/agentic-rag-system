"""
Custom vector store implementation without external dependencies
Uses numpy arrays and pickle for persistence
"""
import numpy as np
import pickle
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import logging
from app.core.config import settings
from app.models.schemas import DocumentChunk

logger = logging.getLogger(__name__)


class CustomVectorStore:
    """
    Custom vector store using numpy arrays for in-memory storage
    and pickle for persistence. No external database required.
    """

    def __init__(self, store_path: Path = None):
        """
        Initialize the vector store

        Args:
            store_path: Path to store the vector database
        """
        self.store_path = store_path or settings.VECTOR_DB_DIR / "vector_store.pkl"
        self.metadata_path = self.store_path.parent / "metadata.json"

        # In-memory storage
        self.vectors: np.ndarray = np.array([])  # Shape: (n_vectors, embedding_dim)
        self.chunks: List[DocumentChunk] = []
        self.document_index: Dict[str, List[int]] = {}  # doc_id -> chunk indices

        # Load existing data if available
        self.load()

    def add_documents(
        self,
        chunks: List[DocumentChunk],
        embeddings: np.ndarray
    ) -> None:
        """
        Add documents with their embeddings to the store

        Args:
            chunks: List of document chunks
            embeddings: Corresponding embeddings (n_chunks, embedding_dim)
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")

        start_idx = len(self.chunks)

        # Add chunks
        self.chunks.extend(chunks)

        # Add vectors
        if self.vectors.size == 0:
            self.vectors = embeddings
        else:
            self.vectors = np.vstack([self.vectors, embeddings])

        # Update document index
        for i, chunk in enumerate(chunks):
            doc_id = chunk.document_id
            chunk_idx = start_idx + i

            if doc_id not in self.document_index:
                self.document_index[doc_id] = []
            self.document_index[doc_id].append(chunk_idx)

        logger.info(f"Added {len(chunks)} chunks to vector store. Total: {len(self.chunks)}")

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        filter_doc_ids: Optional[List[str]] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Search for similar documents using cosine similarity

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filter_doc_ids: Optional list of document IDs to filter

        Returns:
            List of (chunk, score) tuples sorted by relevance
        """
        if self.vectors.size == 0:
            logger.warning("Vector store is empty")
            return []

        # Calculate cosine similarities
        similarities = self._cosine_similarity_batch(query_embedding, self.vectors)

        # Apply filtering if specified
        if filter_doc_ids:
            valid_indices = []
            for doc_id in filter_doc_ids:
                valid_indices.extend(self.document_index.get(doc_id, []))

            if not valid_indices:
                return []

            # Create mask
            mask = np.zeros(len(similarities), dtype=bool)
            mask[valid_indices] = True
            similarities = np.where(mask, similarities, -np.inf)

        # Get top-k indices
        top_k = min(top_k, len(self.chunks))
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        # Build results
        results = []
        for idx in top_indices:
            idx = int(idx)
            score = float(similarities[idx])
            if score > 0:  # Only return positive similarities
                results.append((self.chunks[idx], score))

        return results

    def _cosine_similarity_batch(
        self,
        query_vec: np.ndarray,
        doc_vecs: np.ndarray
    ) -> np.ndarray:
        """Calculate cosine similarity between query and all documents"""
        # Normalize vectors
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
        doc_norms = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-10)

        # Compute cosine similarity
        similarities = np.dot(doc_norms, query_norm)
        return similarities

    def get_document_chunks(self, document_id: str) -> List[DocumentChunk]:
        """Get all chunks for a specific document"""
        indices = self.document_index.get(document_id, [])
        return [self.chunks[i] for i in indices]

    def delete_document(self, document_id: str) -> bool:
        """
        Delete all chunks for a document

        Args:
            document_id: Document ID to delete

        Returns:
            True if document was found and deleted
        """
        if document_id not in self.document_index:
            return False

        indices_to_delete = set(self.document_index[document_id])

        # Remove from chunks and vectors
        remaining_indices = [i for i in range(len(self.chunks)) if i not in indices_to_delete]

        self.chunks = [self.chunks[i] for i in remaining_indices]
        self.vectors = self.vectors[remaining_indices]

        # Rebuild document index
        self.document_index = {}
        for i, chunk in enumerate(self.chunks):
            doc_id = chunk.document_id
            if doc_id not in self.document_index:
                self.document_index[doc_id] = []
            self.document_index[doc_id].append(i)

        logger.info(f"Deleted document {document_id}")
        return True

    def save(self) -> None:
        """Persist vector store to disk"""
        try:
            # Save main data
            data = {
                'vectors': self.vectors,
                'chunks': [chunk.model_dump() for chunk in self.chunks],
                'document_index': self.document_index
            }

            with open(self.store_path, 'wb') as f:
                pickle.dump(data, f)

            # Save metadata
            metadata = {
                'total_chunks': len(self.chunks),
                'total_documents': len(self.document_index),
                'embedding_dim': self.vectors.shape[1] if self.vectors.size > 0 else 0,
                'last_updated': datetime.now().isoformat()
            }

            with open(self.metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Saved vector store to {self.store_path}")

        except Exception as e:
            logger.error(f"Error saving vector store: {e}")
            raise

    def load(self) -> None:
        """Load vector store from disk"""
        if not self.store_path.exists():
            logger.info("No existing vector store found. Starting fresh.")
            return

        try:
            with open(self.store_path, 'rb') as f:
                data = pickle.load(f)

            self.vectors = data['vectors']
            self.chunks = [DocumentChunk(**chunk_dict) for chunk_dict in data['chunks']]
            self.document_index = data['document_index']

            logger.info(f"Loaded {len(self.chunks)} chunks from vector store")

        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            logger.warning("Starting with empty vector store")
            self.vectors = np.array([])
            self.chunks = []
            self.document_index = {}

    def get_stats(self) -> Dict:
        """Get statistics about the vector store"""
        return {
            'total_chunks': len(self.chunks),
            'total_documents': len(self.document_index),
            'embedding_dim': self.vectors.shape[1] if self.vectors.size > 0 else 0,
            'documents': {
                doc_id: len(indices)
                for doc_id, indices in self.document_index.items()
            }
        }

    def clear(self) -> None:
        """Clear all data from the vector store"""
        self.vectors = np.array([])
        self.chunks = []
        self.document_index = {}
        logger.info("Cleared vector store")


# Global singleton instance
_vector_store = None


def get_vector_store() -> CustomVectorStore:
    """Get or create the global vector store instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = CustomVectorStore()
    return _vector_store
