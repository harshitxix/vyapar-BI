from backend.app.services.trends.clustering import ArticleCluster
from backend.app.services.trends.temporal import TemporalMetrics
from backend.app.services.trends.scoring import TrendScores


class TrendLifecycleService:
    """
    Determines the lifecycle state of a market trend deterministically
    based on temporal velocity, momentum, and historical persistence.
    """

    @staticmethod
    def determine_lifecycle_status(
        cluster: ArticleCluster,
        temporal: TemporalMetrics,
        scores: TrendScores,
    ) -> str:
        """
        Lifecycle rules:
        - emerging: newly detected with low historical presence + positive growth
        - growing: sustained positive acceleration & momentum
        - established: high persistence over time with steady coverage
        - cooling: activity slowing down compared to recent peak
        - declining: sharp negative growth
        - inactive: dropped below viable article activity
        """
        if cluster.article_count < 2:
            return "inactive"

        # Emerging: low historical baseline but high recent burst/growth
        if temporal.baseline_volume <= 1 and (temporal.growth_rate >= 0.40 or temporal.burst_score >= 1.0):
            return "emerging"

        # Growing: strong positive momentum and increasing velocity
        if scores.momentum_score >= 0.20 and temporal.growth_rate >= 0.15:
            return "growing"

        # Established: persistent presence across history and active window
        if temporal.baseline_volume >= 3 and abs(temporal.growth_rate) < 0.25 and temporal.persistence_days >= 7:
            return "established"

        # Cooling: negative growth but still active
        if temporal.growth_rate < -0.15 and temporal.growth_rate >= -0.45:
            return "cooling"

        # Declining: sharp negative growth
        if temporal.growth_rate < -0.45:
            return "declining"

        # Default fallback
        if temporal.baseline_volume == 0:
            return "emerging"
        return "growing" if scores.momentum_score >= 0 else "cooling"
