import numpy as np
from typing import List, Dict
from sklearn.cluster import AgglomerativeClustering

from backend.app.services.trends.candidates import CandidateArticle
from backend.app.services.trends.similarity import SimilarityService


class ArticleCluster:
    """
    A detected cluster of semantically related candidate articles.
    """

    def __init__(self, cluster_id: int, articles: List[CandidateArticle]):
        self.cluster_id = cluster_id
        self.articles = articles
        self.vectors = [a.embedding for a in articles if a.embedding is not None]
        self.centroid = SimilarityService.compute_centroid(self.vectors)
        self.coherence = SimilarityService.compute_coherence(self.vectors) if self.vectors else 0.0

    @property
    def article_count(self) -> int:
        return len(self.articles)

    @property
    def unique_sources(self) -> set:
        return {a.source_id for a in self.articles if a.source_id}

    @property
    def unique_source_names(self) -> set:
        return {a.source_name for a in self.articles if a.source_name}

    @property
    def unique_source_count(self) -> int:
        return len(self.unique_sources)

    def extract_top_topics(self, limit: int = 6) -> List[str]:
        topic_counts: Dict[str, int] = {}
        for a in self.articles:
            for t in a.topics:
                if t:
                    topic_counts[t] = topic_counts.get(t, 0) + 1
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_topics[:limit]]

    def extract_top_entities(self, limit: int = 8) -> List[str]:
        entity_counts: Dict[str, int] = {}
        for a in self.articles:
            for e in a.entities:
                if e:
                    entity_counts[e] = entity_counts.get(e, 0) + 1
        sorted_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)
        return [e[0] for e in sorted_entities[:limit]]


class ClusteringService:
    """
    Performs deterministic clustering on candidate article vector embeddings.
    Filters out noise / isolated articles.
    """

    def __init__(
        self,
        distance_threshold: float = 0.38,  # Equivalent to cosine similarity >= 0.62
        min_cluster_size: int = 3,
        min_sources: int = 2,
    ):
        self.distance_threshold = distance_threshold
        self.min_cluster_size = min_cluster_size
        self.min_sources = min_sources

    def cluster_articles(self, candidates: List[CandidateArticle]) -> List[ArticleCluster]:
        """
        Clusters articles with valid vector embeddings.
        Returns list of valid ArticleCluster objects meeting minimum size thresholds.
        """
        valid_candidates = [c for c in candidates if c.embedding is not None and len(c.embedding) > 0]
        if len(valid_candidates) < self.min_cluster_size:
            return []

        vectors = np.array([c.embedding for c in valid_candidates], dtype=np.float32)
        # Normalize vectors for cosine metric
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        norm_vectors = vectors / norms

        # Agglomerative clustering with cosine metric and average linkage
        clustering = AgglomerativeClustering(
            n_clusters=None,
            metric="cosine",
            linkage="average",
            distance_threshold=self.distance_threshold,
        )
        labels = clustering.fit_predict(norm_vectors)

        # Group by label
        clusters_by_label: Dict[int, List[CandidateArticle]] = {}
        for label, candidate in zip(labels, valid_candidates):
            if label not in clusters_by_label:
                clusters_by_label[label] = []
            clusters_by_label[label].append(candidate)

        result_clusters: List[ArticleCluster] = []
        for label, cluster_articles in clusters_by_label.items():
            cluster = ArticleCluster(cluster_id=int(label), articles=cluster_articles)
            
            # Enforce minimum size and source diversity filters
            if cluster.article_count >= self.min_cluster_size and cluster.unique_source_count >= self.min_sources:
                result_clusters.append(cluster)

        return result_clusters
