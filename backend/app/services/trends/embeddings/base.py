from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.
    Supports local ONNX (FastEmbed), OpenAI, or mock providers.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name/Identifier of the embedding model."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimension of the generated vector (e.g. 384 or 1536)."""
        pass

    @property
    def version(self) -> str:
        """Version of the embedding representation."""
        return "v1"

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate vector embeddings for a list of text strings.
        """
        pass

    async def embed_text(self, text: str) -> List[float]:
        """
        Convenience method to generate embedding for a single text string.
        """
        embeddings = await self.embed_texts([text])
        if not embeddings:
            raise ValueError("Failed to generate embedding.")
        return embeddings[0]
