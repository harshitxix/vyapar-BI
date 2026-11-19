import hashlib
import numpy as np
from typing import List
from backend.app.services.trends.embeddings.base import BaseEmbeddingProvider


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic mock embedding provider based on text hash + bag of terms.
    Provides fast, reproducible 384-dimensional unit vectors without network or heavy models.
    """

    def __init__(self, dimension: int = 384):
        self._dim = dimension

    @property
    def model_name(self) -> str:
        return "mock-embedding-384"

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def version(self) -> str:
        return "mock-v1"

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            words = [w.strip(".,;:\"'()[]{}") for w in text.lower().split() if len(w) > 2]
            if not words:
                words = [text.lower()]

            # Sum deterministic token vectors
            combined_vec = np.zeros(self._dim, dtype=np.float32)
            for word in words:
                seed = int(hashlib.md5(word.encode("utf-8")).hexdigest()[:8], 16)
                rng = np.random.RandomState(seed)
                word_vec = rng.randn(self._dim).astype(np.float32)
                combined_vec += word_vec

            # Normalize to unit vector
            norm = np.linalg.norm(combined_vec)
            if norm > 0:
                combined_vec = combined_vec / norm
            results.append(combined_vec.tolist())
        return results
