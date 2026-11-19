import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import numpy as np

from backend.app.services.trends.candidates import CandidateArticle
from backend.app.services.trends.clustering import ArticleCluster
from backend.app.services.trends.similarity import SimilarityService


class TemporalMetrics:
    def __init__(
        self,
        recent_volume: int,
        baseline_volume: int,
        recent_velocity: float,
        baseline_velocity: float,
        growth_rate: float,
        burst_score: float,
        persistence_days: int,
        first_seen_at: datetime,
        last_seen_at: datetime,
    ):
        self.recent_volume = recent_volume
        self.baseline_volume = baseline_volume
        self.recent_velocity = recent_velocity
        self.baseline_velocity = baseline_velocity
        self.growth_rate = growth_rate
        self.burst_score = burst_score
        self.persistence_days = persistence_days
        self.first_seen_at = first_seen_at
        self.last_seen_at = last_seen_at


class TemporalAnalysisService:
    """
    Measures temporal velocity, growth rate, persistence, and burstiness
    for detected article clusters.
    """

    @staticmethod
    def analyze_cluster_temporal(
        cluster: ArticleCluster,
        baseline_articles: List[CandidateArticle],
        recent_window_days: int = 14,
        baseline_window_days: int = 45,
        match_similarity_threshold: float = 0.60,
    ) -> TemporalMetrics:
        """
        Analyzes temporal signals by comparing recent cluster volume against historical baseline.
        """
        recent_volume = cluster.article_count
        
        # Calculate dates span
        pub_dates = []
        for a in cluster.articles:
            dt = a.published_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            pub_dates.append(dt)
            
        first_seen_at = min(pub_dates) if pub_dates else datetime.now(timezone.utc)
        last_seen_at = max(pub_dates) if pub_dates else datetime.now(timezone.utc)
        persistence_days = max(1, (last_seen_at - first_seen_at).days + 1)

        # Count baseline matching articles
        baseline_matches = 0
        if cluster.centroid and baseline_articles:
            for b_art in baseline_articles:
                if b_art.embedding:
                    sim = SimilarityService.compute_cosine_similarity(cluster.centroid, b_art.embedding)
                    if sim >= match_similarity_threshold:
                        baseline_matches += 1

        baseline_volume = baseline_matches

        # Compute velocities (articles per day)
        recent_velocity = recent_volume / max(1, recent_window_days)
        baseline_velocity = baseline_volume / max(1, baseline_window_days)

        # Growth rate: relative increase over baseline
        growth_rate = (recent_velocity - baseline_velocity) / (baseline_velocity + 0.1)

        # Burst score: statistical z-score style burst metric
        # std_est ~ sqrt(baseline_velocity + 0.5)
        burst_score = (recent_velocity - baseline_velocity) / math.sqrt(baseline_velocity + 0.5)

        return TemporalMetrics(
            recent_volume=recent_volume,
            baseline_volume=baseline_volume,
            recent_velocity=round(recent_velocity, 3),
            baseline_velocity=round(baseline_velocity, 3),
            growth_rate=round(growth_rate, 3),
            burst_score=round(burst_score, 3),
            persistence_days=persistence_days,
            first_seen_at=first_seen_at,
            last_seen_at=last_seen_at,
        )
