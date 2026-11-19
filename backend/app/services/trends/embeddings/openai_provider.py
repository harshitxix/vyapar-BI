import httpx
from typing import List
from backend.app.services.trends.embeddings.base import BaseEmbeddingProvider
from backend.app.config.settings import settings


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """
    OpenAI-compatible embedding provider.
    Default model: text-embedding-3-small (dimension: 384 or 1536).
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = "text-embedding-3-small",
        dimension: int = 384,
        base_url: str = "https://api.openai.com/v1",
    ):
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model_name = model_name
        self._dimension = dimension
        self._base_url = base_url

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def version(self) -> str:
        return "openai-v3"

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY is not configured for OpenAIEmbeddingProvider.")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model_name,
            "input": texts,
            "dimensions": self._dimension,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self._base_url}/embeddings", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]
