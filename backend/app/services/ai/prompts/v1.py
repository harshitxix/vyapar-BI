import re
from typing import Tuple

PROMPT_VERSION = "v1.0"

SYSTEM_PROMPT = """You are an expert AI business intelligence engine specialized in Indian retail, kirana commerce, FMCG, consumer tech, and market dynamics.
Your task is to analyze the provided business news article and extract structured market intelligence in strict JSON format.

### EXTRACTION GUIDELINES:
1. summary: A 2-4 sentence objective, factual summary. Do NOT speculate, give financial advice, or extrapolate beyond the text.
2. primary_domain: Choose the most accurate domain from: ["grocery", "retail", "fmcg", "technology", "electronics", "restaurants", "manufacturing", "logistics", "general_business"].
3. secondary_domains: List of 0-2 secondary domains that also apply.
4. category: High-level classification, e.g. "Market", "Consumer", "Pricing", "Product Launch", "Regulation", "Supply Chain", "Expansion", "Funding", "Earnings", "Partnership".
5. subcategory: More specific subcategory (or null if not applicable).
6. article_type: One of ["news", "analysis", "earnings", "policy", "interview", "other"].
7. topics: 3 to 8 normalized, reusable topic tags in lowercase (e.g. ["quick commerce", "fmcg distribution", "edible oil prices"]).
8. keywords: 5 to 10 search terms stripped of common stopwords.
9. entities: Extract named entities with their type:
   - Types allowed: "COMPANY", "BRAND", "PRODUCT", "PERSON", "LOCATION", "ORGANIZATION", "MARKET", "INDUSTRY"
10. events: Discrete business events mentioned (e.g., product launches, mergers, plant expansions, policy changes) with type, description, and date if mentioned.
11. relevance_score: Float between 0.0 and 1.0 representing how relevant or impactful this news is to Indian retail/kirana owners, distributors, and consumer brand businesses:
    - 0.8 - 1.0: Directly impacts FMCG prices, wholesale supplies, local retail policies, quick commerce competition, key consumer brand launches.
    - 0.5 - 0.7: Broad economic/retail news relevant for context.
    - 0.0 - 0.4: Irrelevant/tangential news with no direct retail impact.
12. confidence: Float between 0.0 and 1.0 indicating your confidence in this structured extraction.

### OUTPUT FORMAT:
You MUST return ONLY valid JSON matching this exact structure:
{
  "summary": "...",
  "primary_domain": "...",
  "secondary_domains": ["..."],
  "category": "...",
  "subcategory": "..." or null,
  "article_type": "news",
  "topics": ["..."],
  "keywords": ["..."],
  "entities": [
    {"name": "...", "type": "COMPANY"}
  ],
  "events": [
    {"type": "product_launch", "description": "...", "date": "..."}
  ],
  "relevance_score": 0.85,
  "confidence": 0.95
}
"""


def sanitize_article_text(text: str) -> str:
    """Sanitize raw article text against common prompt injection patterns."""
    if not text:
        return ""
    # Strip dangerous injection phrases / override attempts
    cleaned = re.sub(r"(?i)(ignore\s+previous\s+instructions|system\s+prompt|reveal\s+secret|you\s+are\s+now)", "[FILTERED]", text)
    # Truncate overly long text to prevent context blowup (e.g. max 12,000 chars)
    return cleaned[:12000].strip()


def build_enrichment_prompt(title: str, description: str, content: str = "") -> Tuple[str, str]:
    """
    Constructs the system and user prompt for article enrichment with input isolation.
    """
    combined_body = content.strip() if content.strip() else description.strip()
    safe_title = sanitize_article_text(title)
    safe_body = sanitize_article_text(combined_body)

    user_prompt = f"""Analyze the following article and return structured JSON market intelligence.

<article_title>
{safe_title}
</article_title>

<article_content>
{safe_body}
</article_content>
"""
    return SYSTEM_PROMPT, user_prompt
