import pytest
import numpy as np
from datetime import datetime, timezone, timedelta

from backend.app.models.article import Article
from backend.app.models.enrichment import ArticleEnrichment
from backend.app.services.trends.embeddings.mock_provider import MockEmbeddingProvider
from backend.app.services.trends.similarity import SimilarityService
from backend.app.services.trends.candidates import CandidateArticle
from backend.app.services.trends.clustering import ClusteringService, ArticleCluster
from backend.app.services.trends.temporal import TemporalAnalysisService, TemporalMetrics
from backend.app.services.trends.scoring import TrendScoringService
from backend.app.services.trends.lifecycle import TrendLifecycleService
from backend.app.services.trends.synthesis import TrendSynthesisService


@pytest.mark.asyncio
async def test_mock_embedding_provider():
    provider = MockEmbeddingProvider(dimension=384)
    texts = ["Quick commerce in India", "Quick commerce in India", "Organic tea export"]
    embeddings = await provider.embed_texts(texts)
    
    assert len(embeddings) == 3
    assert len(embeddings[0]) == 384
    # Deterministic output for same text
    assert embeddings[0] == embeddings[1]
    # Different output for different text
    assert embeddings[0] != embeddings[2]


def test_similarity_service():
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    vec3 = [0.0, 1.0, 0.0]
    
    # Identical vectors -> cosine similarity 1.0
    sim1 = SimilarityService.compute_cosine_similarity(vec1, vec2)
    assert pytest.approx(sim1, 0.001) == 1.0
    
    # Orthogonal vectors -> cosine similarity 0.0
    sim2 = SimilarityService.compute_cosine_similarity(vec1, vec3)
    assert pytest.approx(sim2, 0.001) == 0.0
    
    # Centroid
    centroid = SimilarityService.compute_centroid([vec1, vec2])
    assert pytest.approx(centroid[0], 0.001) == 1.0
    
    # Coherence
    coherence = SimilarityService.compute_coherence([vec1, vec2])
    assert pytest.approx(coherence, 0.001) == 1.0


def test_clustering_and_noise_rejection():
    # Create mock candidate articles
    now = datetime.now(timezone.utc)
    articles = []
    
    # 4 articles in cluster A (similar vectors)
    for i in range(4):
        art = Article(
            id=f"art_a_{i}",
            source_id=f"src_{i % 2}",  # 2 unique sources
            source_name=f"Source {i % 2}",
            source_domain="news.com",
            title=f"Healthy organic snack product {i}",
            original_url=f"http://test.com/a_{i}",
            canonical_url=f"http://test.com/a_{i}",
            canonical_url_hash=f"hash_a_{i}",
            normalized_title_hash=f"nhash_a_{i}",
            published_at=now - timedelta(days=i),
            extraction_method="rss",
        )
        enr = ArticleEnrichment(
            id=f"enr_a_{i}",
            article_id=art.id,
            topics=["healthy snacks", "fmcg"],
            primary_domain="grocery",
            model="test",
            prompt_version="v1",
        )
        # Vector slightly perturbed around [1.0, 0.0, 0.0]
        vec = [0.95 + 0.01 * i, 0.05, 0.0]
        cand = CandidateArticle(art, enr, vec)
        articles.append(cand)
        
    # 1 noise article (isolated vector)
    noise_art = Article(
        id="art_noise",
        source_id="src_9",
        source_name="Source 9",
        source_domain="news.com",
        title="Automobile tyre prices rise",
        original_url="http://test.com/noise",
        canonical_url="http://test.com/noise",
        canonical_url_hash="hash_noise",
        normalized_title_hash="nhash_noise",
        published_at=now,
        extraction_method="rss",
    )
    noise_enr = ArticleEnrichment(
        id="enr_noise",
        article_id=noise_art.id,
        topics=["automotive"],
        primary_domain="auto",
        model="test",
        prompt_version="v1",
    )
    articles.append(CandidateArticle(noise_art, noise_enr, [0.0, 0.0, 1.0]))
    
    clustering_service = ClusteringService(distance_threshold=0.35, min_cluster_size=3, min_sources=2)
    clusters = clustering_service.cluster_articles(articles)
    
    # Only the 4-article cluster should be formed; noise article is rejected
    assert len(clusters) == 1
    assert clusters[0].article_count == 4
    assert clusters[0].unique_source_count == 2
    assert "healthy snacks" in clusters[0].extract_top_topics()


def test_temporal_and_scoring_service():
    now = datetime.now(timezone.utc)
    articles = []
    for i in range(5):
        art = Article(
            id=f"art_{i}",
            source_id=f"src_{i}",
            source_name=f"Source {i}",
            source_domain="news.com",
            title=f"Quick commerce 10-minute delivery expansion {i}",
            original_url=f"http://test.com/{i}",
            canonical_url=f"http://test.com/{i}",
            canonical_url_hash=f"hash_{i}",
            normalized_title_hash=f"nhash_{i}",
            published_at=now - timedelta(days=i),
            extraction_method="rss",
        )
        enr = ArticleEnrichment(
            id=f"enr_{i}",
            article_id=art.id,
            topics=["quick commerce", "retail"],
            primary_domain="retail",
            model="test",
            prompt_version="v1",
        )
        cand = CandidateArticle(art, enr, [1.0, 0.0, 0.0])
        articles.append(cand)
        
    cluster = ArticleCluster(cluster_id=0, articles=articles)
    
    # 0 baseline articles -> newly emerging topic
    temporal = TemporalAnalysisService.analyze_cluster_temporal(
        cluster=cluster,
        baseline_articles=[],
        recent_window_days=14,
        baseline_window_days=45,
    )
    
    assert temporal.recent_volume == 5
    assert temporal.baseline_volume == 0
    assert temporal.growth_rate > 0
    
    scores = TrendScoringService.score_trend(cluster, temporal)
    assert 0.0 <= scores.strength_score <= 1.0
    assert 0.0 <= scores.confidence_score <= 1.0
    assert scores.diversity_score > 0.5  # 5 distinct sources
    assert scores.evidence_grade in ["high", "medium", "low"]


def test_lifecycle_transitions():
    now = datetime.now(timezone.utc)
    articles = [
        CandidateArticle(
            Article(
                id=f"a_{i}",
                source_id=f"s_{i}",
                source_name=f"Source {i}",
                source_domain="news.com",
                title=f"Article {i}",
                original_url="http://test.com",
                canonical_url="http://test.com",
                canonical_url_hash=f"h_{i}",
                normalized_title_hash=f"nh_{i}",
                published_at=now,
                extraction_method="rss",
            ),
            None,
            [1.0, 0.0, 0.0],
        )
        for i in range(4)
    ]
    cluster = ArticleCluster(cluster_id=1, articles=articles)
    
    # Emerging case: 0 baseline, high growth
    temp_emerging = TemporalMetrics(
        recent_volume=4,
        baseline_volume=0,
        recent_velocity=0.5,
        baseline_velocity=0.0,
        growth_rate=4.0,
        burst_score=2.0,
        persistence_days=3,
        first_seen_at=now - timedelta(days=3),
        last_seen_at=now,
    )
    scores = TrendScoringService.score_trend(cluster, temp_emerging)
    status_emerging = TrendLifecycleService.determine_lifecycle_status(cluster, temp_emerging, scores)
    assert status_emerging == "emerging"
    
    # Established case: 5 baseline, stable growth
    temp_est = TemporalMetrics(
        recent_volume=4,
        baseline_volume=5,
        recent_velocity=0.28,
        baseline_velocity=0.25,
        growth_rate=0.08,
        burst_score=0.05,
        persistence_days=14,
        first_seen_at=now - timedelta(days=14),
        last_seen_at=now,
    )
    status_est = TrendLifecycleService.determine_lifecycle_status(cluster, temp_est, scores)
    assert status_est == "established"


@pytest.mark.asyncio
async def test_synthesis_heuristic_fallback():
    now = datetime.now(timezone.utc)
    articles = [
        CandidateArticle(
            Article(
                id=f"a_{i}",
                source_id=f"s_{i}",
                source_name=f"Source {i}",
                source_domain="news.com",
                title=f"Plant-based protein snack launch {i}",
                original_url="http://test.com",
                canonical_url="http://test.com",
                canonical_url_hash=f"h_{i}",
                normalized_title_hash=f"nh_{i}",
                published_at=now,
                extraction_method="rss",
            ),
            ArticleEnrichment(
                id=f"e_{i}",
                article_id=f"a_{i}",
                topics=["plant protein", "snacking"],
                primary_domain="fmcg",
                model="test",
                prompt_version="v1",
            ),
            [1.0, 0.0, 0.0],
        )
        for i in range(3)
    ]
    cluster = ArticleCluster(cluster_id=1, articles=articles)
    temp = TemporalMetrics(
        recent_volume=3,
        baseline_volume=0,
        recent_velocity=0.3,
        baseline_velocity=0.0,
        growth_rate=2.0,
        burst_score=1.5,
        persistence_days=2,
        first_seen_at=now,
        last_seen_at=now,
    )
    scores = TrendScoringService.score_trend(cluster, temp)
    
    synthesis_service = TrendSynthesisService(ai_provider=None)
    result = await synthesis_service.synthesize_trend(cluster, temp, scores, domain="fmcg", region="india")
    
    assert result.trend_name
    assert "Plant Protein" in result.trend_name or "Snacking" in result.trend_name or "Fmcg" in result.trend_name
    assert len(result.key_developments) == 3
    assert result.why_emerging
