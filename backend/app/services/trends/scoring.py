import math
from typing import Dict, Any
from backend.app.services.trends.clustering import ArticleCluster
from backend.app.services.trends.temporal import TemporalMetrics


class TrendScores:
    def __init__(
        self,
        strength_score: float,
        confidence_score: float,
        momentum_score: float,
        coherence_score: float,
        diversity_score: float,
        evidence_grade: str,
    ):
        self.strength_score = strength_score
        self.confidence_score = confidence_score
        self.momentum_score = momentum_score
        self.coherence_score = coherence_score
        self.diversity_score = diversity_score
        self.evidence_grade = evidence_grade


class TrendScoringService:
    """
    Computes transparent, deterministic scores for detected market trend clusters.
    """

    @staticmethod
    def compute_source_diversity(cluster: ArticleCluster) -> float:
        """
        Computes source diversity using Simpson's Diversity Index (1 - sum(p_i^2)).
        Penalizes clusters dominated by a single publisher.
        """
        n = cluster.article_count
        if n <= 1:
            return 0.0

        source_counts: Dict[str, int] = {}
        for art in cluster.articles:
            sid = art.source_id or "unknown"
            source_counts[sid] = source_counts.get(sid, 0) + 1

        simpson_sum = sum((count / n) ** 2 for count in source_counts.values())
        raw_diversity = 1.0 - simpson_sum
        
        # Scale with unique source count benchmark (e.g. 4+ unique sources gives full diversity boost)
        unique_factor = min(1.0, len(source_counts) / 4.0)
        return float(min(1.0, max(0.0, raw_diversity * (1.0 + unique_factor) / 1.5)))

    @classmethod
    def score_trend(
        cls,
        cluster: ArticleCluster,
        temporal: TemporalMetrics,
    ) -> TrendScores:
        """
        Calculates all score components and assigns an evidence grade.
        """
        # 1. Coherence score (0.0 to 1.0)
        coherence = max(0.0, min(1.0, cluster.coherence))

        # 2. Source diversity (0.0 to 1.0)
        diversity = cls.compute_source_diversity(cluster)

        # 3. Momentum score (-1.0 to 1.0)
        # Using hyperbolic tangent to bound growth rate and burst smoothly
        raw_momentum = 0.5 * temporal.growth_rate + 0.3 * temporal.burst_score
        momentum = float(math.tanh(raw_momentum))

        # Normalized momentum (0.0 to 1.0) for strength calculation
        momentum_norm = (momentum + 1.0) / 2.0

        # 4. Volume scale factor (0.0 to 1.0)
        # log scale: 3 articles -> ~0.35, 10 articles -> ~0.75, 20+ articles -> ~1.0
        volume_factor = min(1.0, math.log(1 + cluster.article_count) / math.log(21))

        # 5. Overall Trend Strength Score (0.0 to 1.0)
        strength = (
            0.30 * coherence +
            0.30 * momentum_norm +
            0.25 * diversity +
            0.15 * volume_factor
        )
        strength = round(max(0.0, min(1.0, strength)), 3)

        # 6. Trend Confidence Score (0.0 to 1.0)
        # Reflects certainty that the cluster represents a genuine signal
        article_support = min(1.0, cluster.article_count / 8.0)
        confidence = (
            0.40 * coherence +
            0.35 * diversity +
            0.25 * article_support
        )
        confidence = round(max(0.0, min(1.0, confidence)), 3)

        # 7. Evidence Grade (high, medium, low)
        if strength >= 0.70 and confidence >= 0.65 and cluster.unique_source_count >= 3:
            grade = "high"
        elif strength >= 0.40 and cluster.unique_source_count >= 2:
            grade = "medium"
        else:
            grade = "low"

        return TrendScores(
            strength_score=strength,
            confidence_score=confidence,
            momentum_score=round(momentum, 3),
            coherence_score=round(coherence, 3),
            diversity_score=round(diversity, 3),
            evidence_grade=grade,
        )
