from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class PersonalizationConfig:
    """
    Centralized configuration for Phase 4 Personalization & Feed Ranking Engine.
    All scoring weights and parameters live here so ranking behaviour can be
    inspected, logged, and tuned consistently.
    """
    config_version: str = "v4.0.0"

    # Article Relevance Scoring Weights (must sum to 1.0)
    domain_weight: float = 0.20
    topic_weight: float = 0.20
    entity_weight: float = 0.15
    geography_weight: float = 0.10
    article_relevance_weight: float = 0.10
    trend_weight: float = 0.10
    freshness_weight: float = 0.10
    feedback_weight: float = 0.05

    # Freshness exponential decay constant (tau in hours): exp(-age_hours / tau)
    freshness_decay_hours: float = 48.0

    # Candidate Generation Limits
    candidate_window_days: int = 14
    candidate_max_articles: int = 150
    candidate_max_trends: int = 50

    # Trend Relevance Blending (Phase 3 Market Strength vs Phase 4 User Relevance)
    # final_trend_score = alpha * user_relevance + (1 - alpha) * market_strength
    trend_user_relevance_alpha: float = 0.70

    # Trend User Relevance Sub-weights (sum to 1.0)
    trend_domain_weight: float = 0.40
    trend_topic_weight: float = 0.30
    trend_entity_weight: float = 0.20
    trend_geo_weight: float = 0.10

    # Diversity / Anti-Fatigue Parameters
    diversity_window_size: int = 3
    diversity_source_penalty: float = 0.25
    diversity_topic_overlap_threshold: float = 0.75
    diversity_topic_penalty: float = 0.20
    diversity_max_consecutive_entity: int = 2
    diversity_high_relevance_exemption: float = 0.90

    # Feedback & Preference Bounds
    min_preference_score: float = 0.0
    max_preference_score: float = 1.0
    neutral_preference_score: float = 0.5
    learned_preference_decay_days: float = 14.0

    # Event Signal Deltas (Explicit vs Implicit)
    event_deltas: Dict[str, float] = field(default_factory=lambda: {
        "article_save": 0.15,
        "topic_follow": 0.30,
        "entity_follow": 0.25,
        "trend_follow": 0.20,
        "article_share": 0.10,
        "article_open": 0.03,
        "trend_open": 0.03,
        "article_view": 0.00,  # Logged for impression tracking only; does not bias score
        "article_dismiss": -0.10,
        "article_not_interested": -0.25,
        "topic_unfollow": -0.20,
        "entity_unfollow": -0.15,
    })

    def get_effective_weights(self, user_settings: Dict[str, float]) -> Dict[str, float]:
        """
        Applies user-configured feed preference biases (e.g. freshness_bias,
        trend_bias, geographic_bias, followed_entities_bias) and re-normalizes
        weights so they always sum to 1.0.
        """
        raw = {
            "domain": self.domain_weight,
            "topic": self.topic_weight,
            "entity": self.entity_weight * float(user_settings.get("followed_entities_bias", 1.0)),
            "geography": self.geography_weight * float(user_settings.get("geographic_bias", 1.0)),
            "article_relevance": self.article_relevance_weight,
            "trend": self.trend_weight * float(user_settings.get("trend_bias", 1.0)),
            "freshness": self.freshness_weight * float(user_settings.get("freshness_bias", 1.0)),
            "feedback": (
                self.feedback_weight
                if user_settings.get("behavioural_personalization_enabled", True)
                else 0.0
            ),
        }
        total = sum(raw.values())
        if total <= 0:
            return {
                "domain": self.domain_weight,
                "topic": self.topic_weight,
                "entity": self.entity_weight,
                "geography": self.geography_weight,
                "article_relevance": self.article_relevance_weight,
                "trend": self.trend_weight,
                "freshness": self.freshness_weight,
                "feedback": self.feedback_weight,
            }
        return {k: v / total for k, v in raw.items()}


DEFAULT_PERSONALIZATION_CONFIG = PersonalizationConfig()
