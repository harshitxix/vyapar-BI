import pytest
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from backend.app.models.article import Article
from backend.app.models.enrichment import ArticleEnrichment
from backend.app.models.trend import Trend
from backend.app.models.personalization import (
    UserMarketProfile,
    CanonicalEntity,
    UserLearnedPreference,
)
from backend.app.services.personalization.config import (
    PersonalizationConfig,
    DEFAULT_PERSONALIZATION_CONFIG,
)
from backend.app.services.personalization.taxonomy import TaxonomyService
from backend.app.services.personalization.entity_service import (
    EntityFollowService,
    DEFAULT_SEED_ENTITIES,
)
from backend.app.services.personalization.candidates import ArticleCandidate
from backend.app.services.personalization.scoring import (
    ArticleRelevanceService,
    TrendRelevanceService,
    ScoredArticle,
)
from backend.app.services.personalization.diversity import DiversityService
from backend.app.services.personalization.feedback import FeedbackService


def test_taxonomy_domains_and_subdomains():
    domains = TaxonomyService.get_supported_domains()
    assert len(domains) >= 12
    domain_ids = [d["id"] for d in domains]
    assert "grocery" in domain_ids
    assert "fashion" in domain_ids
    assert "electronics" in domain_ids
    assert "retail" in domain_ids

    # Subdomains
    grocery_subs = TaxonomyService.get_subdomains("grocery")
    assert "neighborhood_grocery" in grocery_subs
    assert "supermarket" in grocery_subs

    # Suggested topics
    grocery_topics = TaxonomyService.get_suggested_topics("grocery")
    assert len(grocery_topics) > 0
    assert any("fmcg" in t.lower() for t in grocery_topics)


def test_taxonomy_domain_similarity():
    # Exact match -> 1.0
    assert TaxonomyService.compute_domain_similarity("grocery", "grocery") == 1.0
    # Related domains -> 0.35
    assert TaxonomyService.compute_domain_similarity("grocery", "retail") == 0.35
    assert TaxonomyService.compute_domain_similarity("fashion", "ecommerce") == 0.35
    # Unrelated -> 0.0
    assert TaxonomyService.compute_domain_similarity("grocery", "technology") == 0.0
    # None handling
    assert TaxonomyService.compute_domain_similarity(None, "grocery") == 0.20


def test_entity_service_seed_and_matching():
    seeds = DEFAULT_SEED_ENTITIES
    assert len(seeds) >= 10
    names = [s["name"] for s in seeds]
    assert "Blinkit" in names
    assert "Zepto" in names
    assert "Reliance Retail" in names

    # Entity detection matching article entity lists
    followed = [
        CanonicalEntity(
            id="ent_blinkit",
            name="Blinkit",
            entity_type="COMPANY",
            aliases=["grofers"],
            domain="grocery",
        )
    ]
    matched = EntityFollowService.match_entities_in_article(
        followed, [{"name": "Grofers", "type": "company"}]
    )
    assert "Blinkit" in matched


def test_article_relevance_scoring_formula():
    config = DEFAULT_PERSONALIZATION_CONFIG
    now = datetime.now(timezone.utc)

    profile = UserMarketProfile(
        id="prof_1",
        user_id="user_test_1",
        business_domain="grocery",
        business_subdomain="neighborhood_grocery",
        country="India",
        state="Haryana",
        city="Gurugram",
    )
    user_topics = {"fmcg": 1.0, "quick_commerce": 0.8}
    followed_entities = [
        CanonicalEntity(
            id="ent_blinkit",
            name="Blinkit",
            entity_type="COMPANY",
            aliases=["blinkit", "grofers"],
            domain="grocery",
        )
    ]
    learned_prefs = {}
    user_settings = {"weights": {"business_domain": 0.35, "topics": 0.25}}

    # Candidate 1: High relevance grocery article
    art1 = Article(
        id="art_1",
        source_id="src_tech",
        source_name="Inc42",
        source_domain="inc42.com",
        title="Blinkit partners with local kirana stores in Gurugram for FMCG distribution",
        description="Quick commerce expansion brings local grocery retailers into dark store supply chain.",
        original_url="https://inc42.com/art1",
        canonical_url="https://inc42.com/art1",
        canonical_url_hash="hash1",
        normalized_title_hash="thash1",
        extraction_method="rss",
        published_at=now - timedelta(hours=2),
        category="retail",
        region="india",
        business_domain="grocery",
    )
    enr1 = ArticleEnrichment(
        id="enr_1",
        article_id="art_1",
        status="completed",
        model="gpt-4o-mini",
        prompt_version="v2",
        primary_domain="grocery",
        secondary_domains=["retail"],
        category="retail",
        topics=["fmcg", "quick_commerce", "supply_chain"],
        entities=[{"name": "Blinkit", "type": "company"}, {"name": "Gurugram", "type": "location"}],
        relevance_score=0.9,
    )
    cand1 = ArticleCandidate(
        article=art1,
        enrichment=enr1,
        primary_domain="grocery",
        secondary_domains=["retail"],
        topics=["fmcg", "quick_commerce", "supply_chain"],
        entities=[{"name": "Blinkit", "type": "company"}, {"name": "Gurugram", "type": "location"}],
        published_at=art1.published_at,
        region="india",
        relevance_score=0.9,
    )

    scored1 = ArticleRelevanceService.score_candidate(
        candidate=cand1,
        profile=profile,
        user_topics=user_topics,
        followed_entities=followed_entities,
        learned_prefs=learned_prefs,
        user_settings=user_settings,
        active_trends=[],
        config=config,
    )

    assert scored1.final_score > 0.65
    assert any("grocery" in r.lower() for r in scored1.reasons)
    assert any("Blinkit" in r for r in scored1.reasons)
    assert any("Gurugram" in r for r in scored1.reasons)
    assert "fmcg" in scored1.matched_topics
    assert "Blinkit" in scored1.matched_entities

    # Candidate 2: Completely unrelated article
    art2 = Article(
        id="art_2",
        source_id="src_tech",
        source_name="TechCrunch",
        source_domain="techcrunch.com",
        title="Taiwan semiconductor foundry expands fab capacity",
        description="Global chip shortage prompts new capital investment in advanced packaging.",
        original_url="https://techcrunch.com/art2",
        canonical_url="https://techcrunch.com/art2",
        canonical_url_hash="hash2",
        normalized_title_hash="thash2",
        extraction_method="rss",
        published_at=now - timedelta(hours=2),
        category="technology",
        region="global",
        business_domain="technology",
    )
    cand2 = ArticleCandidate(
        article=art2,
        enrichment=None,
        primary_domain="technology",
        secondary_domains=[],
        topics=["semiconductor", "foundry"],
        entities=[{"name": "TSMC", "type": "company"}, {"name": "Taiwan", "type": "location"}],
        published_at=art2.published_at,
        region="global",
        relevance_score=0.7,
    )

    scored2 = ArticleRelevanceService.score_candidate(
        candidate=cand2,
        profile=profile,
        user_topics=user_topics,
        followed_entities=followed_entities,
        learned_prefs=learned_prefs,
        user_settings=user_settings,
        active_trends=[],
        config=config,
    )

    assert scored1.final_score > scored2.final_score + 0.35


def test_freshness_decay():
    now = datetime.now(timezone.utc)
    config = DEFAULT_PERSONALIZATION_CONFIG

    # Age = 0 hours -> Decay = 1.0
    decay_0 = ArticleRelevanceService.compute_freshness_score(now, config.freshness_decay_hours)
    assert pytest.approx(decay_0, 0.01) == 1.0

    # Age = 48 hours (tau) -> Decay = exp(-1) = 0.3678
    decay_48 = ArticleRelevanceService.compute_freshness_score(
        now - timedelta(hours=48), config.freshness_decay_hours
    )
    assert pytest.approx(decay_48, 0.02) == 0.368

    # Age = 96 hours -> Decay = exp(-2) = 0.135
    decay_96 = ArticleRelevanceService.compute_freshness_score(
        now - timedelta(hours=96), config.freshness_decay_hours
    )
    assert pytest.approx(decay_96, 0.02) == 0.135


def test_trend_relevance_separation_and_blending():
    config = DEFAULT_PERSONALIZATION_CONFIG

    profile = UserMarketProfile(
        id="prof_2",
        user_id="user_test_fashion",
        business_domain="fashion",
        country="India",
        state="Maharashtra",
        city="Mumbai",
    )
    user_topics = {"sustainable_apparel": 0.9}
    followed_entities = []

    # Trend A: Strong market strength (0.95), but domain is Electronics (not Fashion)
    trend_elec = Trend(
        id="trend_1",
        name="Smartphone festive price cuts across India",
        description="Massive discounts observed on 5G handsets across e-commerce platforms.",
        domain="electronics",
        region="india",
        category="pricing",
        status="active",
        strength_score=0.95,
        representative_topics=["smartphones", "festive_sale"],
        representative_entities=["Amazon", "Flipkart"],
    )

    # Trend B: Moderate market strength (0.60), but exact domain match with user (Fashion) and topic match
    trend_fash = Trend(
        id="trend_2",
        name="Sustainable cotton apparel demand surges",
        description="Indian textile retailers witness high adoption of organic clothing.",
        domain="fashion",
        region="india",
        category="consumer_demand",
        status="emerging",
        strength_score=0.60,
        representative_topics=["sustainable_apparel", "textile"],
        representative_entities=["Fabindia"],
    )

    st_elec = TrendRelevanceService.score_trend(trend_elec, profile, user_topics, followed_entities, config)
    st_fash = TrendRelevanceService.score_trend(trend_fash, profile, user_topics, followed_entities, config)

    # Invariant: Market strength is preserved strictly separate from user relevance
    assert st_elec.market_strength_score == 0.95
    assert st_fash.market_strength_score == 0.60

    # User relevance should strongly favor Fashion trend
    assert st_fash.user_relevance_score > st_elec.user_relevance_score

    # Blended score formula check: 0.70 * user_relevance + 0.30 * market_strength
    expected_fash = round(0.70 * st_fash.user_relevance_score + 0.30 * 0.60, 4)
    assert pytest.approx(st_fash.final_score, 0.01) == expected_fash


def test_diversity_anti_fatigue_reranking():
    now = datetime.now(timezone.utc)
    config = DEFAULT_PERSONALIZATION_CONFIG

    articles = []
    for i in range(4):
        art = Article(
            id=f"art_et_{i}",
            source_id="et_retail",
            source_name="ET Retail",
            source_domain="retail.economictimes.indiatimes.com",
            title=f"ET Retail Headline {i}",
            original_url=f"https://et.com/{i}",
            canonical_url=f"https://et.com/{i}",
            canonical_url_hash=f"ethash_{i}",
            normalized_title_hash=f"ettitle_{i}",
            extraction_method="rss",
            published_at=now,
        )
        cand = ArticleCandidate(
            article=art,
            enrichment=None,
            primary_domain="retail",
            secondary_domains=[],
            topics=["retail_market"],
            entities=[{"name": "Reliance Retail", "type": "company"}],
            published_at=now,
            region="india",
            relevance_score=0.70,
        )
        articles.append(ScoredArticle(
            candidate=cand,
            final_score=0.70,
            raw_signals={},
            reasons=[],
            matched_topics=["retail_market"],
            matched_entities=["Reliance Retail"],
        ))

    art_mint = Article(
        id="art_mint_1",
        source_id="mint",
        source_name="Mint",
        source_domain="livemint.com",
        title="Mint Headline Independent",
        original_url="https://mint.com/1",
        canonical_url="https://mint.com/1",
        canonical_url_hash="minthash_1",
        normalized_title_hash="minttitle_1",
        extraction_method="rss",
        published_at=now,
    )
    cand_mint = ArticleCandidate(
        article=art_mint,
        enrichment=None,
        primary_domain="retail",
        secondary_domains=[],
        topics=["consumer_spending"],
        entities=[{"name": "Tata Trent", "type": "company"}],
        published_at=now,
        region="india",
        relevance_score=0.68,
    )
    articles.append(ScoredArticle(
        candidate=cand_mint,
        final_score=0.68,
        raw_signals={},
        reasons=[],
        matched_topics=["consumer_spending"],
        matched_entities=["Tata Trent"],
    ))

    reranked = DiversityService.apply_diversity_reranking(articles, config)

    # First item is ET Retail #0 (0.70)
    assert reranked[0].candidate.article.source_id == "et_retail"
    # Second item should be Mint (0.68) because repeated ET Retail was penalized
    assert reranked[1].candidate.article.source_id == "mint"


def test_feedback_decay_calculation():
    config = DEFAULT_PERSONALIZATION_CONFIG
    now = datetime.now(timezone.utc)

    # Preference updated just now -> neutral baseline is 0.5, preference is 0.8
    pref_now = UserLearnedPreference(
        id="p1",
        user_id="u1",
        preference_type="topic",
        target_id="quick_commerce",
        preference_score=0.8,
        evidence_count=3,
        last_interaction_at=now,
    )
    score_now = FeedbackService.compute_decayed_score(pref_now, now, config)
    assert pytest.approx(score_now, 0.001) == 0.8

    # Preference updated 14 days ago (half-life): (0.8 - 0.5) * exp(-14/14) = 0.3 * 0.3678 = 0.1103 -> 0.5 + 0.1103 = 0.6103
    pref_14d = UserLearnedPreference(
        id="p2",
        user_id="u1",
        preference_type="topic",
        target_id="quick_commerce",
        preference_score=0.8,
        evidence_count=3,
        last_interaction_at=now - timedelta(days=14),
    )
    score_14d = FeedbackService.compute_decayed_score(pref_14d, now, config)
    assert pytest.approx(score_14d, 0.02) == 0.610
