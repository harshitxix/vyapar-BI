import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from backend.app.services.ai.providers.base import BaseAIProvider
from backend.app.services.trends.clustering import ArticleCluster
from backend.app.services.trends.temporal import TemporalMetrics
from backend.app.services.trends.scoring import TrendScores

logger = logging.getLogger("vyapar.trends.synthesis")


class TrendSynthesisOutput(BaseModel):
    trend_name: str = Field(..., description="Concise market trend title (3 to 7 words)")
    trend_description: str = Field(..., description="2-3 sentences explaining the market phenomenon based strictly on supplied evidence")
    why_emerging: str = Field(..., description="1-2 sentences explaining why the pattern emerged")
    key_developments: List[str] = Field(default_factory=list, description="2-4 key factual developments")
    category: str = Field(default="Consumer Trend", description="Normalized category")


SYNTHESIS_SYSTEM_PROMPT = """You are an expert Market Intelligence Analyst synthesizing an already-detected cluster of related news articles into a structured Market Trend summary.

STRICT GUARDRAILS & INSTRUCTIONS:
1. ALGORITHMS DETECT, YOU EXPLAIN: The statistical cluster is already proven. Your task is ONLY to synthesize and name the trend clearly.
2. ZERO HALLUCINATION: Use ONLY facts, company names, product categories, and developments present in the provided article evidence. Do NOT invent data, quotes, numbers, or dates.
3. NO BUSINESS RECOMMENDATIONS: Do NOT advise retailers what to stock, buy, or price. Only explain what is occurring in the market.
4. CATEGORIES: Choose one canonical category from:
   - Consumer Trend
   - Product Trend
   - Technology
   - Pricing
   - Regulation
   - Retail
   - E-commerce
   - Supply Chain
   - Competition
   - Other

Return ONLY a valid JSON object matching this schema:
{
  "trend_name": "Clear, informative trend title",
  "trend_description": "2-3 factual sentences explaining what is happening across these stories.",
  "why_emerging": "1-2 sentences explaining the trend's momentum and reporting focus.",
  "key_developments": ["Concrete factual development 1", "Concrete factual development 2"],
  "category": "Consumer Trend"
}"""


class TrendSynthesisService:
    """
    Synthesizes cluster evidence into human-readable trend names, descriptions,
    and key developments using the LLM with strict grounding.
    """

    def __init__(self, ai_provider: Optional[BaseAIProvider] = None):
        self.ai_provider = ai_provider

    def _build_heuristic_fallback(
        self,
        cluster: ArticleCluster,
        temporal: TemporalMetrics,
        scores: TrendScores,
        domain: str,
    ) -> TrendSynthesisOutput:
        """
        Algorithmic fallback if LLM is unavailable or times out.
        Ensures trend engine never fails.
        """
        top_topics = cluster.extract_top_topics(3)
        top_entities = cluster.extract_top_entities(3)
        
        topic_str = " & ".join(t.title() for t in top_topics) if top_topics else f"{domain.title()} Shift"
        trend_name = f"Emerging Shift: {topic_str}"
        
        desc = (
            f"Multiple articles across {cluster.unique_source_count} independent sources report expanding developments "
            f"in {', '.join(top_topics) if top_topics else domain}."
        )
        why = (
            f"Detected based on {cluster.article_count} supporting stories with {scores.evidence_grade} evidence "
            f"and a growth velocity of {temporal.recent_velocity:.2f} articles/day."
        )
        
        developments = [a.article.title for a in cluster.articles[:3]]
        
        return TrendSynthesisOutput(
            trend_name=trend_name[:250],
            trend_description=desc,
            why_emerging=why,
            key_developments=developments,
            category="Consumer Trend",
        )

    async def synthesize_trend(
        self,
        cluster: ArticleCluster,
        temporal: TemporalMetrics,
        scores: TrendScores,
        domain: str = "retail",
        region: str = "india",
    ) -> TrendSynthesisOutput:
        """
        Synthesizes a trend cluster with LLM or fallback.
        """
        if not self.ai_provider:
            return self._build_heuristic_fallback(cluster, temporal, scores, domain)

        # Prepare evidence packet
        articles_evidence = []
        for i, a in enumerate(cluster.articles[:12], 1):
            summary = a.enrichment.summary if a.enrichment and a.enrichment.summary else a.article.description or ""
            articles_evidence.append(
                f"Story {i}:\n"
                f"- Title: {a.article.title}\n"
                f"- Source: {a.source_name}\n"
                f"- Summary: {summary}\n"
                f"- Topics: {', '.join(a.topics[:5])}\n"
                f"- Entities: {', '.join(a.entities[:5])}"
            )

        evidence_text = "\n\n".join(articles_evidence)
        user_prompt = (
            f"MARKET DOMAIN: {domain.upper()}\n"
            f"REGION: {region.upper()}\n"
            f"METRICS:\n"
            f"- Article count: {cluster.article_count}\n"
            f"- Independent sources: {cluster.unique_source_count} ({', '.join(list(cluster.unique_source_names)[:5])})\n"
            f"- Velocity: {temporal.recent_velocity:.2f} articles/day (Baseline: {temporal.baseline_velocity:.2f}/day)\n"
            f"- Momentum: {scores.momentum_score}\n"
            f"- Coherence: {scores.coherence_score}\n\n"
            f"CLUSTER ARTICLES EVIDENCE:\n"
            f"{evidence_text}\n\n"
            f"Synthesize the overarching market trend adhering to the schema and instructions."
        )

        try:
            response_text = await self.ai_provider.generate_completion(
                system_prompt=SYNTHESIS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=600,
            )
            
            # Extract JSON
            clean_text = response_text.strip()
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()

            parsed = json.loads(clean_text)
            return TrendSynthesisOutput(**parsed)
        except Exception as e:
            logger.warning(f"LLM Trend Synthesis failed ({e}), using heuristic synthesis.")
            return self._build_heuristic_fallback(cluster, temporal, scores, domain)
