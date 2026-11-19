import asyncio
from typing import List, Optional
from backend.app.services.trends.embeddings.base import BaseEmbeddingProvider


class FastEmbedProvider(BaseEmbeddingProvider):
    """
    Local ONNX-based embedding provider using FastEmbed.
    Default model: BAAI/bge-small-en-v1.5 (dimension: 384).
    Fast, runs locally on CPU with zero external API calls/costs.
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", dimension: int = 384):
        self._model_name = model_name
        self._dimension = dimension
        self._model = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def version(self) -> str:
        return "v1"

    def _get_model(self):
        if self._model is None:
            from fastembed import TextEmbedding
            self._model = TextEmbedding(model_name=self._model_name)
        return self._model

    def _embed_sync(self, texts: List[str]) -> List[List[float]]:
        model = self._get_model()
        embeddings_generator = model.embed(texts)
        return [list(vec.tolist()) for vec in embeddings_generator]

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._embed_sync, texts)
