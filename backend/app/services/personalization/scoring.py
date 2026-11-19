import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass

from backend.app.models.personalization import (
    UserMarketProfile,
    CanonicalEntity,
    UserTopicPreference,
    UserLearnedPreference,
)
from backend.app.models.trend import Trend
from backend.app.services.personalization.config import (
    PersonalizationConfig,
    DEFAULT_PERSONALIZATION_CONFIG,
)
from backend.app.services.personalization.taxonomy import TaxonomyService
from backend.app.services.personalization.entity_service import EntityFollowService
from backend.app.services.personalization.candidates import ArticleCandidate


@dataclass
class ScoredArticle:
    candidate: ArticleCandidate
    final_score: float
    raw_signals: Dict[str, float]
    reasons: List[str]
    matched_topics: List[str]
    matched_entities: List[str]


@dataclass
class ScoredTrend:
    trend: Trend
    user_relevance_score: float
    market_strength_score: float
    final_score: float
    reasons: List[str]
    matched_topics: List[str]
    matched_entities: List[str]


class ArticleRelevanceService:
    """
    Computes deterministic 8-signal relevance scores for article candidates.
    """

    @classmethod
    def compute_freshness_score(
        cls, published_at: datetime, decay_hours: float = 48.0
    ) -> float:
        """
        Calculates exponential decay score based on article publication time:
        freshness = exp(-age_hours / tau)
        """
        now = datetime.now(timezone.utc)
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        age_hours = max(0.0, (now - published_at).total_seconds() / 3600.0)
        return float(math.exp(-age_hours / max(1.0, decay_hours)))

    @classmethod
    def compute_geographic_score(
        cls, profile: Optional[UserMarketProfile], article_region: str, article_text: str
    ) -> float:
        """
        Calculates geographic relevance score [0.0, 1.0].
        """
        if not profile:
            return 0.50

        text_lower = article_text.lower()
        # City match
        if profile.city and profile.city.lower() in text_lower:
            return 1.00
        # State match
        if profile.state and profile.state.lower() in text_lower:
            return 0.80
        # National match
        country_norm = (profile.country or "india").lower()
        if article_region and article_region.lower() in (country_norm, "india"):
            return 0.50
        if article_region and article_region.lower() in ("global", "all"):
            return 0.40

        return 0.20

    @classmethod
    def compute_topic_match(
        cls, user_topics: Dict[str, float], article_topics: List[str]
    ) -> Tuple[float, List[str]]:
        """
        Calculates topic match score and list of overlapping topics.
        """
        if not user_topics:
            return 0.25, []

        norm_article_topics = [TaxonomyService.normalize_topic(t) for t in article_topics if t]
        matched = []
        accumulated_score = 0.0

        for t in norm_article_topics:
            if t in user_topics:
                matched.append(t)
                accumulated_score += user_topics[t]

        if not matched:
            return 0.0, []

        # Jaccard-style normalized score
        overlap_ratio = len(matched) / max(1, len(user_topics))
        score = min(1.0, (accumulated_score / max(1, len(matched))) * 0.5 + overlap_ratio * 0.5)
        return float(score), matched

    @classmethod
    def compute_entity_match(
        cls, followed_entities: List[CanonicalEntity], article_entities: List[Dict[str, Any]]
    ) -> Tuple[float, List[str]]:
        """
        Calculates entity match score and list of overlapping entity names.
        """
        if not followed_entities:
            return 0.20, []

        matched = EntityFollowService.match_entities_in_article(
            followed_entities, article_entities
        )
        if not matched:
            return 0.0, []

        score = min(1.0, len(matched) * 0.50)
        return float(score), matched

    @classmethod
    def compute_feedback_score(
        cls,
        learned_prefs: Dict[str, float],
        primary_domain: str,
        topics: List[str],
        entities: List[str],
    ) -> float:
        """
        Aggregates learned interaction preference adjustments.
        """
        if not learned_prefs:
            return 0.50  # Neutral baseline

        scores: List[float] = []
        # Check domain
        if primary_domain in learned_prefs:
            scores.append(learned_prefs[primary_domain])

        # Check topics
        for t in topics:
            if t in learned_prefs:
                scores.append(learned_prefs[t])

        # Check entities
        for e in entities:
            if e in learned_prefs:
                scores.append(learned_prefs[e])

        if not scores:
            return 0.50

        return sum(scores) / len(scores)

    @classmethod
    def score_candidate(
        cls,
        candidate: ArticleCandidate,
        profile: Optional[UserMarketProfile],
        user_topics: Dict[str, float],
        followed_entities: List[CanonicalEntity],
        learned_prefs: Dict[str, float],
        user_settings: Dict[str, Any],
        active_trends: List[Trend],
        config: PersonalizationConfig = DEFAULT_PERSONALIZATION_CONFIG,
    ) -> ScoredArticle:
        """
        Computes the final weighted relevance score for an article candidate.
        """
        weights = config.get_effective_weights(user_settings)
        user_domain = profile.business_domain if profile else "grocery"

        # S1: Domain relevance
        s1_domain = TaxonomyService.compute_domain_similarity(
            user_domain, candidate.primary_domain, candidate.secondary_domains
        )

        # S2: Topic match
        s2_topic, matched_topics = cls.compute_topic_match(user_topics, candidate.topics)

        # S3: Entity match
        s3_entity, matched_entities = cls.compute_entity_match(
            followed_entities, candidate.entities
        )

        # S4: Geographic relevance
        article_text = f"{candidate.article.title} {candidate.article.description or ''}"
        s4_geo = cls.compute_geographic_score(profile, candidate.region, article_text)

        # S5: Intrinsic quality / relevance
        s5_quality = candidate.relevance_score

        # S6: Trend association
        s6_trend = 0.0
        linked_trend_name: Optional[str] = None
        for tr in active_trends:
            # Check if candidate shares topics or entities with active trend
            tr_topics = set(t.lower() for t in (tr.representative_topics or []))
            tr_entities = set(e.lower() for e in (tr.representative_entities or []))
            has_topic_link = any(t.lower() in tr_topics for t in candidate.topics)
            has_entity_link = any(
                (e.get("name") if isinstance(e, dict) else str(e)).lower() in tr_entities
                for e in candidate.entities
            )
            if has_topic_link or has_entity_link:
                trend_val = tr.strength_score
                if trend_val > s6_trend:
                    s6_trend = trend_val
                    linked_trend_name = tr.name

        # S7: Freshness decay
        s7_freshness = cls.compute_freshness_score(
            candidate.published_at, config.freshness_decay_hours
        )

        # S8: User feedback
        s8_feedback = cls.compute_feedback_score(
            learned_prefs,
            candidate.primary_domain,
            matched_topics,
            matched_entities,
        )

        # Final weighted sum
        final_score = (
            weights["domain"] * s1_domain
            + weights["topic"] * s2_topic
            + weights["entity"] * s3_entity
            + weights["geography"] * s4_geo
            + weights["article_relevance"] * s5_quality
            + weights["trend"] * s6_trend
            + weights["freshness"] * s7_freshness
            + weights["feedback"] * s8_feedback
        )
        # Apply domain mismatch penalty if article has zero affinity with user domain
        if s1_domain == 0.0 and candidate.primary_domain != "general_business":
            final_score *= 0.35

        final_score = max(0.0, min(1.0, final_score))

        # Generate explainable reasons
        reasons: List[str] = []
        if s1_domain >= 0.8:
            domain_name = (
                profile.business_domain.replace("_", " ").title() if profile else "market"
            )
            reasons.append(f"Relevant to your {domain_name} business")
        if matched_topics:
            topics_str = ", ".join(t.title() for t in matched_topics[:2])
            reasons.append(f"Matches your interest in {topics_str}")
        if matched_entities:
            ent_str = ", ".join(matched_entities[:2])
            reasons.append(f"Related to followed company: {ent_str}")
        if s4_geo >= 0.8 and profile and profile.city:
            reasons.append(f"Local market update for {profile.city.title()}")
        elif s6_trend >= 0.6 and linked_trend_name:
            reasons.append(f"Part of market trend: {linked_trend_name}")
        elif s7_freshness >= 0.85:
            reasons.append("Recent breaking market update")

        if not reasons:
            reasons.append("Top market intelligence story")

        raw_signals = {
            "domain": round(s1_domain, 4),
            "topic": round(s2_topic, 4),
            "entity": round(s3_entity, 4),
            "geography": round(s4_geo, 4),
            "article_relevance": round(s5_quality, 4),
            "trend": round(s6_trend, 4),
            "freshness": round(s7_freshness, 4),
            "feedback": round(s8_feedback, 4),
        }

        return ScoredArticle(
            candidate=candidate,
            final_score=round(final_score, 4),
            raw_signals=raw_signals,
            reasons=reasons,
            matched_topics=matched_topics,
            matched_entities=matched_entities,
        )


class TrendRelevanceService:
    """
    Ranks market trends by combining Phase 3 market strength with Phase 4 user relevance.
    """

    @classmethod
    def score_trend(
        cls,
        trend: Trend,
        profile: Optional[UserMarketProfile],
        user_topics: Dict[str, float],
        followed_entities: List[CanonicalEntity],
        config: PersonalizationConfig = DEFAULT_PERSONALIZATION_CONFIG,
    ) -> ScoredTrend:
        """
        Calculates user relevance and combines it with Phase 3 trend strength.
        """
        user_domain = profile.business_domain if profile else "grocery"

        # 1. Domain match
        t_domain = (trend.domain or "all").lower()
        if t_domain == "all":
            domain_score = 0.50
        elif t_domain == user_domain.lower():
            domain_score = 1.00
        else:
            domain_score = TaxonomyService.compute_domain_similarity(user_domain, t_domain)

        # 2. Topic match
        tr_topics = [
            TaxonomyService.normalize_topic(t) for t in (trend.representative_topics or [])
        ]
        matched_topics = [t for t in tr_topics if t in user_topics]
        topic_score = (
            min(1.0, len(matched_topics) * 0.40) if matched_topics else (0.25 if not user_topics else 0.0)
        )

        # 3. Entity match
        matched_entities: List[str] = []
        if followed_entities and trend.representative_entities:
            fol_names = {e.name.lower() for e in followed_entities}
            for tr_ent in trend.representative_entities:
                tr_name = str(tr_ent).strip().lower()
                if tr_name in fol_names:
                    matched_entities.append(tr_name.title())
        entity_score = min(1.0, len(matched_entities) * 0.50) if matched_entities else 0.10

        # 4. Geo match
        geo_score = 0.50
        if profile and profile.country and trend.region:
            if trend.region.lower() in (profile.country.lower(), "india"):
                geo_score = 0.80

        # User relevance composite
        user_relevance = (
            config.trend_domain_weight * domain_score
            + config.trend_topic_weight * topic_score
            + config.trend_entity_weight * entity_score
            + config.trend_geo_weight * geo_score
        )
        user_relevance = max(0.0, min(1.0, user_relevance))

        # Market strength from Phase 3
        market_strength = max(0.0, min(1.0, trend.strength_score))

        # Blended final score
        alpha = config.trend_user_relevance_alpha
        final_score = alpha * user_relevance + (1.0 - alpha) * market_strength
        final_score = max(0.0, min(1.0, final_score))

        # Reasons
        reasons: List[str] = []
        if domain_score >= 0.8:
            reasons.append(f"Trending in your {user_domain.replace('_', ' ').title()} sector")
        if matched_topics:
            t_str = ", ".join(t.title() for t in matched_topics[:2])
            reasons.append(f"Connected to topics you follow ({t_str})")
        if matched_entities:
            e_str = ", ".join(matched_entities[:2])
            reasons.append(f"Involves companies you follow ({e_str})")
        if market_strength >= 0.75:
            reasons.append(f"High-momentum market shift ({trend.status.title()})")

        if not reasons:
            reasons.append("Notable market trend")

        return ScoredTrend(
            trend=trend,
            user_relevance_score=round(user_relevance, 4),
            market_strength_score=round(market_strength, 4),
            final_score=round(final_score, 4),
            reasons=reasons,
            matched_topics=matched_topics,
            matched_entities=matched_entities,
        )
