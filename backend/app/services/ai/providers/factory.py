import logging
from backend.app.config.settings import settings
from backend.app.services.ai.providers.base import BaseLLMProvider
from backend.app.services.ai.providers.groq_provider import GroqProvider
from backend.app.services.ai.providers.mock_provider import MockLLMProvider
from backend.app.services.ai.providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


def get_llm_provider(provider_type: str = None) -> BaseLLMProvider:
    """
    Factory to instantiate configured LLM provider.
    """
    selected = (provider_type or settings.LLM_PROVIDER or "groq").lower()

    if selected == "groq":
        logger.info(f"Initializing Groq LLM provider with model {settings.GROQ_MODEL}")
        return GroqProvider(
            api_key=settings.GROQ_API_KEY or "",
            model_name=settings.GROQ_MODEL,
        )
    elif selected == "openai":
        logger.info(f"Initializing OpenAI provider with model {settings.OPENAI_MODEL}")
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY or "",
            model_name=settings.OPENAI_MODEL,
        )
    elif selected in ("mock", "test"):
        return MockLLMProvider()
    else:
        logger.warning(f"Unknown LLM provider '{selected}', falling back to Groq.")
        return GroqProvider(
            api_key=settings.GROQ_API_KEY or "",
            model_name=settings.GROQ_MODEL,
        )
