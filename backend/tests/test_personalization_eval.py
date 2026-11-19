import pytest
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Set

from backend.app.models.article import Article
from backend.app.models.enrichment import ArticleEnrichment
from backend.app.models.personalization import (
    UserMarketProfile,
    CanonicalEntity,
)
from backend.app.services.personalization.config import DEFAULT_PERSONALIZATION_CONFIG
from backend.app.services.personalization.candidates import ArticleCandidate
from backend.app.services.personalization.scoring import (
    ArticleRelevanceService,
    ScoredArticle,
)
from backend.app.services.personalization.diversity import DiversityService


def create_candidate_pool(now: datetime) -> List[ArticleCandidate]:
    """Generates 20 distinct candidate articles spanning 4 business domains."""
    articles_data = [
        # Grocery articles (5)
        ("g1", "grocery", "Inc42", "inc42.com", "Blinkit and Zepto expand kirana store dark store network in Gurugram",
         ["fmcg", "quick commerce", "supply chain"], [{"name": "Blinkit", "type": "company"}, {"name": "Zepto", "type": "company"}], "Gurugram"),
        ("g2", "grocery", "ET Retail", "retail.economictimes.indiatimes.com", "FMCG wholesale prices stabilize across northern India mandis",
         ["fmcg", "food prices"], [{"name": "Amul", "type": "brand"}], "Delhi"),
        ("g3", "grocery", "Mint", "livemint.com", "Edible oil import duties revised by Ministry of Commerce",
         ["food prices", "edible oil"], [], "India"),
        ("g4", "grocery", "Business Standard", "business-standard.com", "Dairy cooperative Amul announces expansion in organic milk segment",
         ["dairy", "organic food"], [{"name": "Amul", "type": "brand"}], "Gujarat"),
        ("g5", "grocery", "Financial Express", "financialexpress.com", "Packaged spices market sees double-digit growth in convenience stores",
         ["fmcg", "kirana retail"], [], "India"),

        # Fashion articles (5)
        ("f1", "fashion", "ET Retail", "retail.economictimes.indiatimes.com", "Fabindia launches sustainable organic cotton collection in Mumbai",
         ["sustainable apparel", "textile"], [{"name": "Fabindia", "type": "company"}], "Mumbai"),
        ("f2", "fashion", "Apparel Resources", "apparelresources.com", "Cotton yarn prices soften as festive apparel manufacturing peaks",
         ["cotton prices", "festive sales"], [], "Maharashtra"),
        ("f3", "fashion", "Mint", "livemint.com", "E-commerce fashion platforms report 35 percent surge in ethnic wear demand",
         ["ecommerce apparel", "festive sales"], [], "India"),
        ("f4", "fashion", "Business Standard", "business-standard.com", "Textile export promotion council announces handloom subsidies",
         ["textile exports", "handloom"], [], "India"),
        ("f5", "fashion", "Financial Express", "financialexpress.com", "Footwear retail chains expand physical store footprint in Tier 2 cities",
         ["footwear retail", "retail expansion"], [], "India"),

        # Electronics articles (5)
        ("e1", "electronics", "Gadgets360", "gadgets360.com", "Samsung launches festive discounts on 5G smartphones in Bengaluru retail outlets",
         ["smartphones", "festive sales"], [{"name": "Samsung", "type": "company"}], "Bengaluru"),
        ("e2", "electronics", "ET Tech", "economictimes.indiatimes.com", "Apple opens third company-owned flagship store in India",
         ["smartphones", "retail expansion"], [{"name": "Apple", "type": "company"}], "Bengaluru"),
        ("e3", "electronics", "Mint", "livemint.com", "Consumer electronics demand shifts to energy-efficient inverter ACs and appliances",
         ["appliances", "consumer electronics"], [], "India"),
        ("e4", "electronics", "Business Standard", "business-standard.com", "Semiconductor PLI scheme disburses first capital subsidy to manufacturing units",
         ["semiconductor", "manufacturing"], [], "India"),
        ("e5", "electronics", "Financial Express", "financialexpress.com", "Smart television prices drop ahead of cricket tournament season",
         ["appliances", "consumer electronics"], [], "India"),

        # Restaurant & Food Services articles (5)
        ("r1", "restaurants", "ET Retail", "retail.economictimes.indiatimes.com", "Zomato adjusts platform commission for dine-in partner restaurants in Delhi NCR",
         ["delivery aggregators", "dine-in footfall"], [{"name": "Zomato", "type": "company"}], "Delhi"),
        ("r2", "restaurants", "Mint", "livemint.com", "Commercial LPG cylinder prices cut by oil marketing companies",
         ["commercial lpg rates", "raw ingredient costs"], [], "India"),
        ("r3", "restaurants", "Business Standard", "business-standard.com", "Cloud kitchens drive 40 percent of food delivery growth in metropolitan clusters",
         ["cloud kitchens", "food delivery"], [], "Delhi"),
        ("r4", "restaurants", "Financial Express", "financialexpress.com", "FSSAI tightens food safety audit norms for quick-service restaurants",
         ["food safety", "qsr"], [], "India"),
        ("r5", "restaurants", "Inc42", "inc42.com", "Specialty coffee cafes expand beyond metros into tier-2 cities",
         ["cafes", "retail expansion"], [], "India"),
    ]

    candidates = []
    for art_id, domain, src_name, src_domain, title, topics, entities, region in articles_data:
        art = Article(
            id=art_id,
            source_id=f"src_{src_name.lower().replace(' ', '_')}",
            source_name=src_name,
            source_domain=src_domain,
            title=title,
            description=f"Market briefing on {title}",
            original_url=f"https://{src_domain}/{art_id}",
            canonical_url=f"https://{src_domain}/{art_id}",
            canonical_url_hash=f"hash_{art_id}",
            normalized_title_hash=f"thash_{art_id}",
            extraction_method="rss",
            published_at=now - timedelta(hours=3),
            category=domain,
            region=region.lower(),
            business_domain=domain,
        )
        enr = ArticleEnrichment(
            id=f"enr_{art_id}",
            article_id=art_id,
            status="completed",
            model="gpt-4o-mini",
            prompt_version="v2",
            primary_domain=domain,
            secondary_domains=[],
            category=domain,
            topics=topics,
            entities=entities,
            relevance_score=0.85,
        )
        cand = ArticleCandidate(
            article=art,
            enrichment=enr,
            primary_domain=domain,
            secondary_domains=[],
            topics=topics,
            entities=entities,
            published_at=art.published_at,
            region=region.lower(),
            relevance_score=0.85,
        )
        candidates.append(cand)

    return candidates


def test_four_profile_personalization_separation():
    """
    Evaluates that 4 distinct business personas receive distinctly personalized feeds
    from the exact same candidate pool of 20 articles.
    """
    now = datetime.now(timezone.utc)
    config = DEFAULT_PERSONALIZATION_CONFIG
    candidates = create_candidate_pool(now)

    # 1. Profile Grocery (Gurugram Kirana)
    profile_grocery = UserMarketProfile(
        id="prof_g", user_id="user_g", business_domain="grocery", business_subdomain="neighborhood_grocery",
        country="India", state="Haryana", city="Gurugram",
    )
    topics_grocery = {"fmcg": 1.0, "quick commerce": 0.9}
    entities_grocery = [
        CanonicalEntity(id="e_blinkit", name="Blinkit", entity_type="COMPANY", aliases=["blinkit"], domain="grocery"),
        CanonicalEntity(id="e_zepto", name="Zepto", entity_type="COMPANY", aliases=["zepto"], domain="grocery"),
    ]

    # 2. Profile Fashion (Mumbai Apparel)
    profile_fashion = UserMarketProfile(
        id="prof_f", user_id="user_f", business_domain="fashion", business_subdomain="clothing_retail",
        country="India", state="Maharashtra", city="Mumbai",
    )
    topics_fashion = {"sustainable apparel": 1.0, "textile": 0.9}
    entities_fashion = [
        CanonicalEntity(id="e_fabindia", name="Fabindia", entity_type="COMPANY", aliases=["fabindia"], domain="fashion")
    ]

    # 3. Profile Electronics (Bengaluru Gadgets)
    profile_electronics = UserMarketProfile(
        id="prof_e", user_id="user_e", business_domain="electronics", business_subdomain="mobile_retail",
        country="India", state="Karnataka", city="Bengaluru",
    )
    topics_electronics = {"smartphones": 1.0, "appliances": 0.8}
    entities_electronics = [
        CanonicalEntity(id="e_samsung", name="Samsung", entity_type="COMPANY", aliases=["samsung"], domain="electronics"),
        CanonicalEntity(id="e_apple", name="Apple", entity_type="COMPANY", aliases=["apple"], domain="electronics"),
    ]

    # 4. Profile Restaurant (Delhi Diner)
    profile_restaurant = UserMarketProfile(
        id="prof_r", user_id="user_r", business_domain="restaurants", business_subdomain="fine_dining",
        country="India", state="Delhi", city="Delhi",
    )
    topics_restaurant = {"delivery aggregators": 1.0, "dine-in footfall": 0.9}
    entities_restaurant = [
        CanonicalEntity(id="e_zomato", name="Zomato", entity_type="COMPANY", aliases=["zomato"], domain="restaurants")
    ]

    def rank_for_user(profile, topics, entities):
        scored = [
            ArticleRelevanceService.score_candidate(
                candidate=cand,
                profile=profile,
                user_topics=topics,
                followed_entities=entities,
                learned_prefs={},
                user_settings={},
                active_trends=[],
                config=config,
            )
            for cand in candidates
        ]
        return DiversityService.apply_diversity_reranking(scored, config)

    ranked_g = rank_for_user(profile_grocery, topics_grocery, entities_grocery)
    ranked_f = rank_for_user(profile_fashion, topics_fashion, entities_fashion)
    ranked_e = rank_for_user(profile_electronics, topics_electronics, entities_electronics)
    ranked_r = rank_for_user(profile_restaurant, topics_restaurant, entities_restaurant)

    # Invariant 1: Top article for each user matches their business domain exactly
    assert ranked_g[0].candidate.primary_domain == "grocery"
    assert ranked_g[0].candidate.article.id == "g1"  # Matches Blinkit, Zepto, FMCG, Quick Commerce & Gurugram
    assert any("Blinkit" in r for r in ranked_g[0].reasons)

    assert ranked_f[0].candidate.primary_domain == "fashion"
    assert ranked_f[0].candidate.article.id == "f1"  # Matches Fabindia, Sustainable Apparel & Mumbai
    assert any("Fabindia" in r for r in ranked_f[0].reasons)

    assert ranked_e[0].candidate.primary_domain == "electronics"
    assert ranked_e[0].candidate.article.id in ["e1", "e2"]  # Matches Samsung/Apple & Bengaluru

    assert ranked_r[0].candidate.primary_domain == "restaurants"
    assert ranked_r[0].candidate.article.id == "r1"  # Matches Zomato & Delhi

    # Invariant 2: Top-5 feeds have near-zero overlap across diverse profiles
    top5_g = {item.candidate.article.id for item in ranked_g[:5]}
    top5_f = {item.candidate.article.id for item in ranked_f[:5]}
    top5_e = {item.candidate.article.id for item in ranked_e[:5]}
    top5_r = {item.candidate.article.id for item in ranked_r[:5]}

    def jaccard_similarity(s1: Set[str], s2: Set[str]) -> float:
        intersection = len(s1.intersection(s2))
        union = len(s1.union(s2))
        return intersection / union if union > 0 else 0.0

    # Cross-persona Top 5 overlap must be 0% between grocery, fashion, electronics, and restaurant
    assert jaccard_similarity(top5_g, top5_f) == 0.0
    assert jaccard_similarity(top5_g, top5_e) == 0.0
    assert jaccard_similarity(top5_g, top5_r) == 0.0
    assert jaccard_similarity(top5_f, top5_e) == 0.0
    assert jaccard_similarity(top5_f, top5_r) == 0.0
    assert jaccard_similarity(top5_e, top5_r) == 0.0
