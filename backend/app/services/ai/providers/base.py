from abc import ABC, abstractmethod
from typing import Optional
from backend.app.schemas.enrichment import EnrichmentResult


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers (Groq, OpenAI, Mock, etc.)."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    async def enrich_article(
        self,
        title: str,
        description: str = "",
        content: str = "",
    ) -> EnrichmentResult:
        """
        Enrich an article asynchronously and return structured intelligence.
        """
        pass

    async def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 600,
    ) -> str:
        """
        Generate raw text/JSON completion from LLM given system and user prompts.
        """
        raise NotImplementedError("generate_completion is not implemented for this provider.")


# Alias for backwards compatibility and clarity
BaseAIProvider = BaseLLMProvider

