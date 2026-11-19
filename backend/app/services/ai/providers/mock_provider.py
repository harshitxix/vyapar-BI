from backend.app.schemas.enrichment import (
    ArticleType,
    EnrichmentOutput,
    EnrichmentResult,
    EnrichmentStatus,
    EntityItem,
    EntityType,
    KeyEventItem,
)
from backend.app.services.ai.prompts import PROMPT_VERSION
from backend.app.services.ai.providers.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """
    Mock LLM provider for fast, deterministic, offline unit testing.
    """

    def __init__(self, model_name: str = "mock-llm-v1"):
        super().__init__(model_name=model_name)

    async def enrich_article(
        self,
        title: str,
        description: str = "",
        content: str = "",
    ) -> EnrichmentResult:
        # Generate predictable mock extraction based on title
        enrichment = EnrichmentOutput(
            summary=f"Analysis of {title}. Market dynamics indicate growth across Indian retail distribution and kirana networks.",
            primary_domain="retail" if "retail" in title.lower() else "fmcg",
            secondary_domains=["grocery", "general_business"],
            category="Market",
            subcategory="Expansion",
            article_type=ArticleType.NEWS,
            topics=["retail growth", "kirana stores", "fmcg distribution"],
            keywords=["retail", "distribution", "fmcg", "india", "supply chain"],
            entities=[
                EntityItem(name="Reliance Retail", type=EntityType.COMPANY),
                EntityItem(name="India", type=EntityType.LOCATION),
            ],
            events=[
                KeyEventItem(type="company_expansion", description="Expansion announced in Indian market.", date="2026")
            ],
            relevance_score=0.88,
            confidence=0.95,
        )

        return EnrichmentResult(
            enrichment=enrichment,
            model=self.model_name,
            prompt_version=PROMPT_VERSION,
            input_tokens=250,
            output_tokens=180,
            latency_ms=45,
            estimated_cost=0.0,
            status=EnrichmentStatus.COMPLETED,
        )

    async def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 600,
    ) -> str:
        import json
        return json.dumps({
            "trend_name": "Rapid Expansion of Quick Commerce Retail",
            "trend_description": "Multiple FMCG and retail sources report hyper-local dark store network expansion across major urban centers.",
            "why_emerging": "Reporting volume spiked by 180% with cross-source coverage across kirana digitisation and delivery speed.",
            "key_developments": [
                "Blinkit and Zepto add 300+ new dark stores",
                "FMCG brands launch exclusive quick-commerce packaging",
                "Kirana partnerships integrated into last-mile logistics",
            ],
            "category": "Retail",
        })


# Alias for backwards compatibility
MockAIProvider = MockLLMProvider
