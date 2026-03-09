"""
Embedding generation using sentence-transformers
"""

import os
import numpy as np
from typing import List

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from .config import EMBEDDING_MODEL, EMBEDDING_DEVICE


class EmbeddingProvider:
    """Provider for text embeddings"""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        """Singleton pattern to avoid loading model multiple times"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None and SentenceTransformer is not None:
            print(f"Loading embedding model: {EMBEDDING_MODEL}...")
            device = self._get_device()
            self._model = SentenceTransformer(EMBEDDING_MODEL, device=device)
            print(f"Model loaded on device: {device}")
    
    def _get_device(self) -> str:
        """Determine best device"""
        if EMBEDDING_DEVICE != "auto":
            return EMBEDDING_DEVICE
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except:
            pass
        return "cpu"
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for texts"""
        if self._model is None:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
        
        # Normalize and encode
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embeddings
    
    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query with prompt template for better retrieval"""
        # Add query prompt for asymmetric search (query vs document)
        prompt = f"为这个句子生成表示以用于检索相关文章：{query}"
        return self.embed([prompt])[0]
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension"""
        if self._model is None:
            return 1024  # Default for bge-large-zh-v1.5
        return self._model.get_sentence_embedding_dimension()


class SimpleEmbeddingProvider:
    """Fallback simple embedding using hash-based approach (for testing without model)"""
    
    DIMENSION = 768
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """Simple random projection embedding (not for production)"""
        import hashlib
        
        embeddings = []
        for text in texts:
            # Create deterministic random vector from text hash
            hash_bytes = hashlib.sha256(text[:100].encode()).digest()
            seed = int.from_bytes(hash_bytes[:8], 'big')
            np.random.seed(seed)
            vec = np.random.randn(self.DIMENSION)
            vec = vec / np.linalg.norm(vec)  # Normalize
            embeddings.append(vec)
        
        return np.array(embeddings)
    
    def embed_query(self, query: str) -> np.ndarray:
        return self.embed([query])[0]
    
    @property
    def dimension(self) -> int:
        return self.DIMENSION
